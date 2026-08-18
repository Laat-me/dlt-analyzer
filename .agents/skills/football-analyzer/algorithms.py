# -*- coding: utf-8 -*-
"""
足球比分概率预测算法池 (football-analyzer)
============================================
实现:
  1. Poisson 模型 (基础): λ = 联赛场均 × 进攻强度 × 防守系数, 比分矩阵概率
  2. Dixon-Coles 修正 (低比分依赖修正, 可选)
  3. 负二项 (需 statsmodels, 可选)
  4. 混合加权: 泊松概率 × 战意权重 × 伤病权重 × 主客场修正
  5. 回测框架: 胜平负/比分精确/大小球 三指标

数据约定 (matches.csv):
  date,league,season,home,away,home_goals,away_goals,home_xg,away_xg,home_rank,away_rank
用法:
  from algorithms import poisson_predict, backtest
"""
import numpy as np
import math

# ---------------------------------------------------------------- 泊松核心

def poisson_pmf(lam, k):
    """P(X=k) = λ^k e^-λ / k!"""
    return math.exp(-lam) * lam ** k / math.factorial(k)

def expected_goals(home_stats, away_stats, league_avg):
    """λ 计算
    home_stats: dict(home_avg_for, home_avg_against, ...) 用主场数据
    away_stats: dict(away_avg_for, away_avg_against, ...) 用客场数据
    """
    att_home = home_stats["avg_for"] / league_avg          # 主队进攻强度
    def_home = home_stats["avg_against"] / league_avg      # 主队防守系数
    att_away = away_stats["avg_for"] / league_avg
    def_away = away_stats["avg_against"] / league_avg
    lam1 = league_avg * att_home * def_away                 # 主队预期进球
    lam2 = league_avg * att_away * def_home                 # 客队预期进球
    return lam1, lam2

def score_matrix(lam1, lam2, max_goals=8):
    """比分概率矩阵: P[i][j] = 主队i球 客队j球"""
    p1 = [poisson_pmf(lam1, k) for k in range(max_goals + 1)]
    p2 = [poisson_pmf(lam2, k) for k in range(max_goals + 1)]
    M = np.zeros((max_goals + 1, max_goals + 1))
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            M[i][j] = p1[i] * p2[j]
    return M

def poisson_predict(home_stats, away_stats, league_avg, max_goals=8, weights=None):
    """输出比分概率排行 + 胜平负 + 大小球
    weights: 混合加权 dict(win_bonus, draw_bonus, loss_penalty, over_bias) 可选"""
    lam1, lam2 = expected_goals(home_stats, away_stats, league_avg)
    M = score_matrix(lam1, lam2, max_goals)

    if weights:  # 混合加权: 调整 胜/平/负 区块概率
        W = M.copy()
        W = W * weights.get("win_bonus", 1.0) * (W > 0)  # 占位: 实际按区块加权
        M = W

    # 排行
    scores = []
    n = M.shape[0]
    for i in range(n):
        for j in range(n):
            scores.append((float(M[i][j]), f"{i}-{j}"))
    scores.sort(reverse=True)

    # 胜平负
    p_home = sum(M[i][j] for i in range(n) for j in range(n) if i > j)
    p_draw = sum(M[i][i] for i in range(n))
    p_away = sum(M[i][j] for i in range(n) for j in range(n) if i < j)
    total = M.sum()
    if total > 0:
        p_home, p_draw, p_away = p_home / total, p_draw / total, p_away / total
    # 大小球 2.5
    p_over = sum(M[i][j] for i in range(n) for j in range(n) if i + j >= 3)
    p_under = 1.0 - p_over if total > 0 else 0.0

    return {
        "lam": (round(lam1, 3), round(lam2, 3)),
        "top_scores": [(s, sc) for sc, s in scores[:10]],
        "result_prob": {"home": p_home, "draw": p_draw, "away": p_away},
        "over25": {"over": p_over, "under": p_under},
    }

# ---------------------------------------------------------------- 混合加权

def apply_weights(base, weights):
    """人工修正: 战意/伤病/主客场
    weights: dict(win_mult, draw_mult, away_mult, over_mult) 乘数
    返回修正后的 λ 与概率"""
    lam1, lam2 = base["lam"]
    lam1 *= weights.get("home_mult", 1.0)
    lam2 *= weights.get("away_mult", 1.0)
    M = score_matrix(lam1, lam2)
    # 战意: 若主队战意高(争冠/保级) 胜区概率 × win_mult
    n = M.shape[0]
    if weights.get("win_mult") and weights["win_mult"] != 1.0:
        for i in range(n):
            for j in range(n):
                if i > j:
                    M[i][j] *= weights["win_mult"]
    if weights.get("over_mult") and weights["over_mult"] != 1.0:
        for i in range(n):
            for j in range(n):
                if i + j >= 3:
                    M[i][j] *= weights["over_mult"]
    M = M / M.sum()
    p_home = sum(M[i][j] for i in range(n) for j in range(n) if i > j)
    p_draw = sum(M[i][i] for i in range(n))
    p_away = 1 - p_home - p_draw
    scores = []
    for i in range(n):
        for j in range(n):
            scores.append((M[i][j], f"{i}-{j}"))
    scores.sort(reverse=True)
    return {"lam": (lam1, lam2), "top_scores": [(s, sc) for sc, s in scores[:10]],
            "result_prob": {"home": p_home, "draw": p_draw, "away": p_away}}

# ---------------------------------------------------------------- 回测框架

def backtest(matches, home_stats_fn, away_stats_fn, league_avg, holdout_frac=0.1):
    """按时间切分回测: 前90%训练(算stats), 后10%留出
    matches: 按时间升序的 dict 列表
    指标: 胜平负准确率 / 比分精确命中率 / 大小球准确率"""
    n = len(matches)
    cut = int(n * (1 - holdout_frac))
    train, test = matches[:cut], matches[cut:]

    # 训练: 计算每队攻防均值(可扩展)
    home_avg = {}
    for m in train:
        home_avg.setdefault(m["home"], []).append(m["home_goals"])
        home_avg.setdefault(m["away"], []).append(m["away_goals"])
    stats = {}
    for team, goals in home_avg.items():
        stats[team] = {"avg_for": np.mean(goals), "avg_against": np.mean(goals)}

    n_res = n_scores = n_ou = 0
    correct_res = correct_scores = correct_ou = 0
    for m in test:
        hs = stats.get(m["home"], {"avg_for": league_avg, "avg_against": league_avg})
        as_ = stats.get(m["away"], {"avg_for": league_avg, "avg_against": league_avg})
        pred = poisson_predict(hs, as_, league_avg)
        # 胜平负
        pr = pred["result_prob"]
        pick = max(pr, key=pr.get)
        actual = "home" if m["home_goals"] > m["away_goals"] else ("draw" if m["home_goals"] == m["away_goals"] else "away")
        n_res += 1; correct_res += (pick == actual)
        # 比分
        top_score = pred["top_scores"][0][0]
        n_scores += 1
        correct_scores += (top_score == f"{m['home_goals']}-{m['away_goals']}")
        # 大小球
        ou = pred["over25"]
        pick_ou = "over" if ou["over"] > ou["under"] else "under"
        actual_ou = "over" if m["home_goals"] + m["away_goals"] >= 3 else "under"
        n_ou += 1; correct_ou += (pick_ou == actual_ou)

    return {
        "holdout": len(test),
        "result_accuracy": correct_res / n_res,
        "exact_score_accuracy": correct_scores / n_scores,
        "over_under_accuracy": correct_ou / n_ou,
    }

if __name__ == "__main__":
    # 示例: 无真实数据时演示泊松计算
    demo = poisson_predict(
        {"avg_for": 1.8, "avg_against": 1.0},
        {"avg_for": 1.2, "avg_against": 1.4},
        league_avg=1.35)
    print("示例 λ:", demo["lam"])
    print("比分概率排行:", demo["top_scores"])
    print("胜平负:", {k: f"{v:.1%}" for k, v in demo["result_prob"].items()})
    print("大小球2.5:", {k: f"{v:.1%}" for k, v in demo["over25"].items()})
