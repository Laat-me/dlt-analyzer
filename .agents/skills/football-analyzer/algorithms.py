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

def poisson_predict(home_stats, away_stats, league_avg, max_goals=8, weights=None, top_n=2):
    """输出比分概率排行 + 胜平负 + 大小球
    weights: 混合加权 dict(win_bonus, draw_bonus, loss_penalty, over_bias) 可选
    top_n: 对外推荐比分最多 N 个（默认2, 完整矩阵仍保留用于计算）"""
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
        "top_scores": [(s, sc) for sc, s in scores[:top_n]],
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

# ---------------------------------------------------------------- 市场赔率反推 λ

def find_lam_from_odds(odds, grid_min=0.1, grid_max=3.5, step=0.05):
    """从胜平负赔率反推泊松 λ1,λ2 (网格搜索使泊松胜平负匹配市场隐含概率)
    用途: 无需逐队攻防数据, 市场赔率已含伤停/战意/交锋等信息"""
    inv = [1.0 / o for o in odds]
    s = sum(inv)
    target = [i / s for i in inv]
    best, besterr = None, 1e9
    for l1 in np.arange(grid_min, grid_max + 1e-9, step):
        for l2 in np.arange(grid_min, grid_max + 1e-9, step):
            p1 = [poisson_pmf(l1, k) for k in range(9)]
            p2 = [poisson_pmf(l2, k) for k in range(9)]
            ph = sum(p1[i] * p2[j] for i in range(9) for j in range(9) if i > j)
            pd = sum(p1[i] * p2[i] for i in range(9))
            pa = 1 - ph - pd
            err = abs(ph - target[0]) + abs(pd - target[1]) + abs(pa - target[2])
            if err < besterr:
                besterr, best = err, (round(l1, 2), round(l2, 2))
    return best

def goals_distribution(lam1, lam2, max_goals=8):
    """竞彩总进球数分布: 0,1,2,3,4,5,6,7+ 八档"""
    M = score_matrix(lam1, lam2, max_goals)
    total = M.sum()
    dist = {}
    for g in range(max_goals):
        if g < max_goals - 1:
            dist[g] = float(sum(M[i][j] for i in range(max_goals + 1)
                                for j in range(max_goals + 1) if i + j == g) / total)
        else:
            dist[f"{max_goals - 1}+"] = float(sum(M[i][j] for i in range(max_goals + 1)
                                                  for j in range(max_goals + 1) if i + j >= max_goals - 1) / total)
    return dist

def half_full_distribution(lam1, lam2, max_goals=8, first_half_ratio=0.45):
    """半全场分布(9档: 胜胜/胜平/胜负/平胜/平平/平负/负胜/负平/负负)
    假设上下半场进球为独立增量泊松：
      上半场 λh = λ * first_half_ratio
      下半场 λ2h = λ * (1-first_half_ratio)
    先枚举半场比分与全场比分, 再映射到半全场类型。"""
    lam1_h1, lam2_h1 = lam1 * first_half_ratio, lam2 * first_half_ratio
    lam1_h2, lam2_h2 = lam1 * (1 - first_half_ratio), lam2 * (1 - first_half_ratio)
    p_h1_home = [poisson_pmf(lam1_h1, k) for k in range(max_goals + 1)]
    p_h1_away = [poisson_pmf(lam2_h1, k) for k in range(max_goals + 1)]
    p_h2_home = [poisson_pmf(lam1_h2, k) for k in range(max_goals + 1)]
    p_h2_away = [poisson_pmf(lam2_h2, k) for k in range(max_goals + 1)]

    def res(a, b):
        if a > b:
            return '胜'
        if a == b:
            return '平'
        return '负'

    out = {k: 0.0 for k in ['胜胜','胜平','胜负','平胜','平平','平负','负胜','负平','负负']}
    for h1 in range(max_goals + 1):
        for a1 in range(max_goals + 1):
            p1 = p_h1_home[h1] * p_h1_away[a1]
            r1 = res(h1, a1)
            for h2 in range(max_goals + 1):
                for a2 in range(max_goals + 1):
                    p2 = p_h2_home[h2] * p_h2_away[a2]
                    rf = res(h1 + h2, a1 + a2)
                    out[r1 + rf] += float(p1 * p2)
    s = sum(out.values())
    if s > 0:
        out = {k: v / s for k, v in out.items()}
    return out

def top_half_full(dist, top_n=3):
    return sorted(dist.items(), key=lambda x: -x[1])[:top_n]

def dixon_coles_correction(M, lam1, lam2, rho=-0.1):
    """Dixon-Coles (1997) 低比分相关性修正
    独立泊松对低比分(0-0/1-0/0-1/1-1)有系统性偏差; 修正因子:
      tau(0,0)=1-λ1λ2ρ  tau(1,0)=1+λ2ρ  tau(0,1)=1+λ1ρ  tau(1,1)=1-ρ
    rho 通常为负(足球数据约-0.05~-0.15): 0-0/1-1 上调, 1-0/0-1 下调"""
    M = M.copy()
    M[0, 0] *= 1 - lam1 * lam2 * rho
    M[1, 0] *= 1 + lam2 * rho
    M[0, 1] *= 1 + lam1 * rho
    M[1, 1] *= 1 - rho
    s = M.sum()
    return M / s if s > 0 else M

def estimate_rho(matches):
    """从历史比分 MLE 估计 rho (Dixon-Coles 论文方法)
    matches: list of (hg, ag); 返回使对数似然最大的 rho"""
    import math
    best_rho, best_ll = -0.15, -1e18
    for rho in np.arange(-0.20, 0.01, 0.01):
        ll = 0.0
        for hg, ag in matches:
            l1 = max(hg, 0.5); l2 = max(ag, 0.5)
            p = poisson_pmf(l1, hg) * poisson_pmf(l2, ag)
            if (hg, ag) == (0, 0): p *= 1 - l1 * l2 * rho
            elif (hg, ag) == (1, 0): p *= 1 + l2 * rho
            elif (hg, ag) == (0, 1): p *= 1 + l1 * rho
            elif (hg, ag) == (1, 1): p *= 1 - rho
            ll += math.log(max(p, 1e-12))
        if ll > best_ll:
            best_ll, best_rho = ll, rho
    return best_rho

def lambda_from_stats(home_stats, away_stats, league_avg=1.35):
    """历史攻防数据算 λ (SKILL 公式): λ = 联赛场均 × 进攻强度 × 防守系数
    home_stats: dict(avg_for, avg_against) 用主场数据"""
    att_home = home_stats["avg_for"] / league_avg
    def_home = home_stats["avg_against"] / league_avg
    att_away = away_stats["avg_for"] / league_avg
    def_away = away_stats["avg_against"] / league_avg
    return (league_avg * att_home * def_away, league_avg * att_away * def_home)

def lambda_mix(odds, home_stats, away_stats, league_avg=1.35, w_hist=0.6):
    """混合 λ: 历史攻防(w_hist) + 市场赔率反推(1-w_hist)
    提高历史数据权重: 默认历史60% 市场40%"""
    l_hist = lambda_from_stats(home_stats, away_stats, league_avg)
    l_mkt = find_lam_from_odds(odds)
    return (w_hist * l_hist[0] + (1 - w_hist) * l_mkt[0],
            w_hist * l_hist[1] + (1 - w_hist) * l_mkt[1])

def full_predict(odds, weights=None, home_stats=None, away_stats=None,
                 league_avg=1.35, w_hist=0.6, dixon_coles=True, rho=-0.1, top_n=2):
    """完整预测: λ(历史+市场混合) -> [Dixon-Coles修正] -> 比分排行/胜平负/大小球/总进球/半全场
    - home_stats/away_stats 提供时: λ = w_hist×历史 + (1-w_hist)×市场 (默认历史60%)
    - 否则纯市场反推
    - dixon_coles=True: 低比分相关性修正
    - weights: 三层人工加权 dict(home_mult, away_mult, win_mult, draw_extra, over_mult)
    - top_n: 对外推荐比分最多 N 个 (默认2)"""
    if home_stats and away_stats:
        l1, l2 = lambda_mix(odds, home_stats, away_stats, league_avg, w_hist)
    else:
        l1, l2 = find_lam_from_odds(odds)
    if weights:
        adj = apply_weights({"lam": (l1, l2)}, weights)
        l1, l2 = adj["lam"]
    M = score_matrix(l1, l2)
    if dixon_coles:
        M = dixon_coles_correction(M, l1, l2, rho)
    if weights and weights.get("draw_extra") and weights["draw_extra"] != 1.0:
        n = M.shape[0]
        for i in range(n):
            M[i][i] *= weights["draw_extra"]
        M = M / M.sum()
    n = M.shape[0]
    ph = float(sum(M[i][j] for i in range(n) for j in range(n) if i > j))
    pd = float(sum(M[i][i] for i in range(n)))
    pa = 1 - ph - pd
    scores = sorted([(float(M[i][j]), f"{i}:{j}") for i in range(n) for j in range(n)], reverse=True)[:top_n]
    p_over = float(sum(M[i][j] for i in range(n) for j in range(n) if i + j >= 3))
    hf = half_full_distribution(l1, l2)
    return {
        "lam": (round(l1, 2), round(l2, 2)),
        "top_scores": [(s, p) for p, s in scores],
        "result_prob": {"home": ph, "draw": pd, "away": pa},
        "over25": {"over": p_over, "under": 1 - p_over},
        "goals_dist": goals_distribution(l1, l2),
        "half_full": hf,
        "half_full_top": top_half_full(hf),
    }

# ---------------------------------------------------------------- 爆冷/卖分风险分析

def upset_risk_analysis(matches_with_rank, tier="low", thr=6):
    """实力差爆冷分析: 大热(排名差>=thr)的爆冷率/被逼平率, 分时段
    matches_with_rank: list of dict(home, away, hg, ag, rank_h, rank_a, md_order)
    实证基线(德甲/德乙2025): 顶级6-11%, 低级别14-25%, 低级别末段末5轮悬殊场25%"""
    big = [m for m in matches_with_rank if abs(m["rank_h"] - m["rank_a"]) >= thr]
    if not big:
        return {"big_count": 0}
    def big_loss(m):
        return (m["rank_h"] - m["rank_a"] < 0 and m["hg"] < m["ag"]) or \
               (m["rank_h"] - m["rank_a"] > 0 and m["hg"] > m["ag"])
    n = len(big)
    loss = sum(1 for m in big if big_loss(m))
    draws = sum(1 for m in big if m["hg"] == m["ag"])
    max_md = max(m["md_order"] for m in matches_with_rank)
    last5 = [m for m in big if m["md_order"] >= max_md - 4]
    last5_loss = sum(1 for m in last5 if big_loss(m)) if last5 else 0
    return {
        "tier": tier, "threshold": thr, "big_count": n,
        "upset_rate": loss / n,
        "draw_rate_against_favorite": draws / n,
        "late_season_upset_rate": (last5_loss / len(last5)) if last5 else None,
        "baseline": {"top_tier": "6-11%", "low_tier": "14-25%", "low_tier_late": "25%"},
    }

# ---------------------------------------------------------------- 历史异常分析（爆冷/大比分/卖分/控分画像）
# 数据约定 (fetch_history.py 产物): {date, round, home, away, hg, ag, hthg, htag, rank_h, rank_a}
# 注意: 本模块全部输出为「统计指纹」(risk fingerprint)，不构成任何操控/卖分证据。

def _favorite(m, thr):
    """大热方向: 排名差 >= thr 时返回 dict(fav_home, gap), 否则 None (无大热)"""
    gap = m['rank_a'] - m['rank_h']  # >0 主队名次更小(更靠前) => 主队是大热
    if abs(gap) < thr:
        return None
    return {'fav_home': gap > 0, 'gap': abs(gap)}


def _fav_win(m, fav_home):
    return (m['hg'] > m['ag']) if fav_home else (m['ag'] > m['hg'])


def _phase_name(round_no, max_r):
    if round_no >= max_r - 4:
        return '末5轮'
    if round_no <= round(max_r * 0.4):
        return '前半段'
    return '中段'


def upset_stats(matches, thr=6):
    """爆冷画像: 大热(排名差>=thr)输球率/被逼平率, 按赛季时段拆解"""
    big = [(m, f) for m in matches if (f := _favorite(m, thr))]
    if not big:
        return {'count': 0, 'note': f'排名差>= {thr} 的大热场次不足'}
    max_r = max(m['round'] for m in matches)
    n = len(big)
    by_phase = {}
    for m, f in big:
        ph = _phase_name(m['round'], max_r)
        s = by_phase.setdefault(ph, {'n': 0, 'upset': 0, 'draw': 0})
        s['n'] += 1
        if m['hg'] == m['ag']:
            s['draw'] += 1
        elif not _fav_win(m, f['fav_home']):
            s['upset'] += 1
    n_upset = sum(v['upset'] for v in by_phase.values())
    n_draw = sum(v['draw'] for v in by_phase.values())
    return {
        'count': n, 'thr': thr,
        'upset_rate': round(n_upset / n, 4),
        'draw_rate': round(n_draw / n, 4),
        'by_phase': {k: {'n': v['n'], 'upset_rate': round(v['upset'] / v['n'], 4),
                         'draw_rate': round(v['draw'] / v['n'], 4)} for k, v in by_phase.items()},
    }


def scoreline_vs_poisson(matches, league_avg):
    """大比分画像: 常见比分与总进球的实际频率 vs 独立泊松期望(两队均按 λ=联赛均分/2)
    偏离倍数 ratio 越大说明该比分在联赛里系统性偏多(如 1-1 聚类)"""
    lam = league_avg / 2.0
    p = [math.exp(-lam) * lam ** k / math.factorial(k) for k in range(9)]
    n = len(matches)
    actual = {}
    tg = {}
    for m in matches:
        key = f"{m['hg']}:{m['ag']}"
        actual[key] = actual.get(key, 0) + 1
        g = min(m['hg'] + m['ag'], 7)
        tg[g] = tg.get(g, 0) + 1
    top = sorted(actual.items(), key=lambda kv: -kv[1])[:8]
    score_rows = []
    for key, cnt in top:
        i, j = map(int, key.split(':'))
        exp = n * p[i] * p[j]
        score_rows.append({'score': key, 'actual': cnt, 'expected': round(exp, 1),
                           'ratio': round(cnt / exp, 2) if exp else None})
    total_lam = league_avg
    tg_rows = []
    for g in range(8):
        act = tg.get(g, 0)
        if g < 7:
            exp = n * math.exp(-total_lam) * total_lam ** g / math.factorial(g)
        else:
            exp = n * (1 - sum(math.exp(-total_lam) * total_lam ** k / math.factorial(k) for k in range(7)))
        tg_rows.append({'goals': f'{g}+' if g == 7 else g, 'actual': act,
                        'expected': round(exp, 1), 'ratio': round(act / exp, 2)})
    big_events = [m for m in matches if m['hg'] + m['ag'] >= 6]
    return {'scorelines': score_rows, 'total_goals': tg_rows,
            'big_score_count': len(big_events), 'big_score_rate': round(len(big_events) / n, 4)}


def sell_fingerprints(matches, thr=10):
    """卖分画像(统计指纹): ①赛季末(末5轮)排名悬殊大热不胜 ②赛季末中游对中游低进球(无欲无求)"""
    max_r = max(m['round'] for m in matches)
    late = [m for m in matches if m['round'] >= max_r - 4]
    cases = []
    for m in late:
        f = _favorite(m, thr)
        if f and not _fav_win(m, f['fav_home']):
            cases.append({'round': m['round'], 'home': m['home'], 'away': m['away'],
                          'hg': m['hg'], 'ag': m['ag'], 'gap': f['gap'],
                          'fav': '主' if f['fav_home'] else '客',
                          'result': '平' if m['hg'] == m['ag'] else '负'})
    cases.sort(key=lambda x: -x['gap'])
    n_teams = max(max(m['rank_h'], m['rank_a']) for m in matches)
    mid = [m for m in late if 0.3 <= m['rank_h'] / n_teams <= 0.7 and 0.3 <= m['rank_a'] / n_teams <= 0.7]
    low = [m for m in mid if m['hg'] + m['ag'] <= 1]
    all_low = sum(1 for m in matches if m['hg'] + m['ag'] <= 1) / len(matches)
    return {
        'late_big_favorite_nonwin': cases[:10],
        'case_count': len(cases),
        'dead_rubber': {'n': len(mid),
                        'low_goal_rate': round(len(low) / len(mid), 4) if mid else None,
                        'league_low_goal_rate': round(all_low, 4)},
    }


def score_control_fingerprints(matches):
    """控分画像(统计指纹): ①队伍级窄分差(0-0/1-0/0-1/1-1)率显著高于联赛基线 ②持1-0到终场 ③同轮多个大热被逼平"""
    narrow = {'0:0', '1:0', '0:1', '1:1'}
    team_cnt, team_narrow = {}, {}
    for m in matches:
        for t in (m['home'], m['away']):
            team_cnt[t] = team_cnt.get(t, 0) + 1
        if f"{m['hg']}:{m['ag']}" in narrow:
            for t in (m['home'], m['away']):
                team_narrow[t] = team_narrow.get(t, 0) + 1
    base = sum(team_narrow.values()) / sum(team_cnt.values()) if team_cnt else 0
    team_flags = []
    for t, c in team_cnt.items():
        if c >= 12:
            r = team_narrow.get(t, 0) / c
            if r > base * 1.35 and r - base > 0.12:
                team_flags.append({'team': t, 'narrow_rate': round(r, 3),
                                   'league': round(base, 3), 'n': c})
    team_flags.sort(key=lambda x: -x['narrow_rate'])
    # 持1-0到终场 (半场领先1球且守住)
    hold_teams = {}
    for m in matches:
        if m.get('hthg') is None:
            continue
        if (m['hthg'] == 1 and m['htag'] == 0 and m['hg'] == 1 and m['ag'] == 0):
            hold_teams[m['home']] = hold_teams.get(m['home'], 0) + 1
        if (m['hthg'] == 0 and m['htag'] == 1 and m['hg'] == 0 and m['ag'] == 1):
            hold_teams[m['away']] = hold_teams.get(m['away'], 0) + 1
    hold_top = sorted(hold_teams.items(), key=lambda kv: -kv[1])[:5]
    # 同轮大热被逼平聚类
    round_draws = {}
    for m in matches:
        f = _favorite(m, 10)
        if f and m['hg'] == m['ag']:
            round_draws[m['round']] = round_draws.get(m['round'], 0) + 1
    cluster = [{'round': r, 'favorite_draws': c} for r, c in sorted(round_draws.items()) if c >= 2]
    return {
        'league_narrow_rate': round(base, 3),
        'team_flags': team_flags[:8],
        'one_goal_holds': {'total': sum(hold_teams.values()), 'top_teams': hold_top},
        'same_round_fav_draw_cluster': cluster,
    }


def _flag_match(m, max_r):
    """单场异常旗标(组合规则, 均为统计指纹)"""
    flags = []
    if m['hg'] + m['ag'] >= 6:
        flags.append('大比分')
    f6 = _favorite(m, 6)
    if f6:
        win = _fav_win(m, f6['fav_home'])
        if f6['gap'] >= 10 and not win and m['hg'] != m['ag']:
            flags.append('悬殊爆冷')
        elif f6['gap'] >= 10 and m['hg'] == m['ag']:
            flags.append('大热被逼平')
        if m['round'] >= max_r - 4 and f6['gap'] >= 10 and not win:
            flags.append('赛季末悬殊不胜')
    if f"{m['hg']}:{m['ag']}" in {'0:0', '1:0', '0:1', '1:1'} and f6 and f6['gap'] >= 10:
        flags.append('悬殊场窄分差')
    return flags


def anomaly_analysis(matches, league_name='', tier='top', league_avg=None):
    """历史异常四类画像汇总: 爆冷(实力差法) / 大比分(泊松偏离) / 卖分(赛季末指纹) / 控分(窄分差/持领先/同轮聚类)
    返回结构化报告; 全部为统计指纹, 不构成操控证据。"""
    if not matches:
        return {'league': league_name, 'n': 0}
    if league_avg is None:
        league_avg = sum(m['hg'] + m['ag'] for m in matches) / len(matches)
    max_r = max(m['round'] for m in matches)
    flagged = []
    for m in matches:
        fs = _flag_match(m, max_r)
        if fs:
            flagged.append({'round': m['round'], 'home': m['home'], 'away': m['away'],
                            'hg': m['hg'], 'ag': m['ag'], 'flags': fs})
    flagged.sort(key=lambda x: -len(x['flags']))
    return {
        'league': league_name, 'tier': tier, 'n': len(matches),
        'league_avg': round(league_avg, 3),
        'upset': upset_stats(matches),
        'high_score': scoreline_vs_poisson(matches, league_avg),
        'sell': sell_fingerprints(matches),
        'control': score_control_fingerprints(matches),
        'top_flagged': flagged[:10],
        'honest_note': '本报告全部为统计指纹(risk fingerprint)，不构成任何操控/卖分证据；单场异常无法定性；小样本时段置信区间宽。',
    }

# ---------------------------------------------------------------- 基于历史异常画像的预测（比分偏置）

def build_score_bias(matches, league_avg, max_g=4, shrink_k=8.0, cap=(0.5, 2.0)):
    """历史赛果 → 比分偏置表: 各比分实际频率 / 独立泊松期望(两队均按 λ=联赛均分/2)
    边界: 行/列下标 == max_g 表示该侧进 >= max_g 球(归并桶)
    经验收缩: ratio 向 1.0 收缩, 权重 = 期望计数/(期望计数+shrink_k), 避免小样本噪声过度扭曲;
    再按 cap 截断。返回 {(i, j): ratio}"""
    lam = league_avg / 2.0
    p = [poisson_pmf(lam, k) for k in range(max_g)]
    p_ge = 1 - sum(p)
    n = len(matches)
    actual = {}
    for m in matches:
        i = min(m['hg'], max_g)
        j = min(m['ag'], max_g)
        actual[(i, j)] = actual.get((i, j), 0) + 1
    bias = {}
    for i in range(max_g + 1):
        for j in range(max_g + 1):
            pi = p_ge if i == max_g else p[i]
            pj = p_ge if j == max_g else p[j]
            exp = n * pi * pj
            if exp <= 0:
                bias[(i, j)] = 1.0
                continue
            raw = actual.get((i, j), 0) / exp
            w = exp / (exp + shrink_k)
            v = 1 + (raw - 1) * w
            v = min(max(v, cap[0]), cap[1])
            bias[(i, j)] = round(v, 3)
    return bias


def apply_score_bias(M, bias, max_g=4):
    """按偏置表加权比分矩阵并重归一化; i/j >= max_g 归入偏置桶"""
    Mb = M.copy()
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            Mb[i, j] *= bias.get((min(i, max_g), min(j, max_g)), 1.0)
    s = Mb.sum()
    return Mb / s if s > 0 else Mb


def lam_from_probs(probs, grid_min=0.1, grid_max=4.0, step=0.05):
    """胜平负概率(归一化) → 最匹配的泊松 λ1,λ2 (网格搜索)
    用途: 让半全场/总进球与修正后的胜平负同源"""
    p_home, p_draw = probs[0], probs[1]
    best, besterr = None, 1e9
    for l1 in np.arange(grid_min, grid_max + 1e-9, step):
        for l2 in np.arange(grid_min, grid_max + 1e-9, step):
            q1 = [poisson_pmf(l1, k) for k in range(9)]
            q2 = [poisson_pmf(l2, k) for k in range(9)]
            qh = sum(q1[i] * q2[j] for i in range(9) for j in range(9) if i > j)
            qd = sum(q1[i] * q2[i] for i in range(9))
            qa = 1 - qh - qd
            err = abs(qh - p_home) + abs(qd - p_draw) + abs(qa - (1 - p_home - p_draw))
            if err < besterr:
                besterr, best = err, (round(l1, 2), round(l2, 2))
    return best


def anomaly_predict(odds, tier='low', bias=None, home_stats=None, away_stats=None,
                    league_avg=1.35, w_hist=0.6, dixon_coles=True, rho=-0.1,
                    top_n=2, draw_extra=None):
    """基于历史异常画像的预测: 市场/混合λ → [Dixon-Coles] → 联赛比分偏置表修正 → 半全场
    - tier: 'top'(德甲层) / 'low'(德乙层), 仅作标注
    - bias: build_score_bias 产物; 提供时按偏置表修正比分矩阵(修正独立泊松对常见比分的系统性偏差)
    - 半全场与总进球由「修正后胜平负反推有效λ」得出, 与修正后胜平负同源
    - 返回: lam/effective_lam/tier/result_prob/top_scores(≤top_n)/over25/goals_dist/half_full/half_full_top"""
    if home_stats and away_stats:
        l1, l2 = lambda_mix(odds, home_stats, away_stats, league_avg, w_hist)
    else:
        l1, l2 = find_lam_from_odds(odds)
    M = score_matrix(l1, l2)
    if dixon_coles:
        M = dixon_coles_correction(M, l1, l2, rho)
    if draw_extra and draw_extra != 1.0:
        n = M.shape[0]
        for i in range(n):
            M[i][i] *= draw_extra
        M = M / M.sum()
    if bias:
        M = apply_score_bias(M, bias)
    n = M.shape[0]
    ph = float(sum(M[i][j] for i in range(n) for j in range(n) if i > j))
    pd = float(sum(M[i][i] for i in range(n)))
    pa = 1 - ph - pd
    eff = lam_from_probs([ph, pd])
    hf = half_full_distribution(*eff)
    gd = {}
    for g in range(8):
        if g < 7:
            gd[g] = float(sum(M[i][j] for i in range(n) for j in range(n) if i + j == g))
        else:
            gd['7+'] = float(sum(M[i][j] for i in range(n) for j in range(n) if i + j >= 7))
    scores = sorted([(float(M[i][j]), f"{i}:{j}") for i in range(n) for j in range(n)], reverse=True)[:top_n]
    p_over = float(sum(M[i][j] for i in range(n) for j in range(n) if i + j >= 3))
    return {
        'lam': (round(l1, 2), round(l2, 2)),
        'effective_lam': eff,
        'tier': tier,
        'result_prob': {'home': ph, 'draw': pd, 'away': pa},
        'top_scores': [(s, p) for p, s in scores],
        'over25': {'over': p_over, 'under': 1 - p_over},
        'goals_dist': gd,
        'half_full': hf,
        'half_full_top': top_half_full(hf),
    }

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
