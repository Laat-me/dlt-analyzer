# -*- coding: utf-8 -*-
"""排列三候选算法集合 + 900/100 滚动回测。

评估口径（与 pailie5-analyzer 一致，便于横向对比）：
  * 主指标  Top-2 位置覆盖率：每位给 2 个候选，实际数字落入即计 1 分，满分 3
  * 辅助    Top-1 位置命中率 / Top-3 覆盖率 / 整组三位全中次数
  * 随机基线 Top-1 = 10%，Top-2 = 20%，Top-3 = 30%（每位独立均匀）

回测方式：walk-forward。第 i 期（i >= 900）只用 draws[:i] 训练，绝不看未来数据。
"""
import argparse
import json
import math
import os
import random

from scipy import stats

warnings = __import__("warnings")
warnings.filterwarnings("ignore")

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.normpath(os.path.join(HERE, "..", "data"))
DRAWS_PATH = os.path.join(DATA_DIR, "draws.json")
MODEL_PATH = os.path.join(DATA_DIR, "model.json")

TRAIN_SIZE = 900
HOLDOUT_SIZE = 100


# ---------------------------------------------------------------- 基础统计

def pos_counts(draws, pos, window=None):
    """位置 pos 上 0-9 的频次（window=None 表示全期）。"""
    arr = [0] * 10
    seq = draws if window is None else draws[-window:]
    for rec in seq:
        arr[rec["digits"][pos]] += 1
    return arr


def transition_matrix(draws, pos):
    """位置 pos 的一阶转移计数 trans[a][b]，Laplace 平滑在打分时做。"""
    trans = [[0] * 10 for _ in range(10)]
    prev = None
    for rec in draws:
        cur = rec["digits"][pos]
        if prev is not None:
            trans[prev][cur] += 1
        prev = cur
    return trans


def last_gap(draws, pos):
    """每位各数字距上次出现的期数（本期为 1）；从未出现给 len(draws)+1。"""
    gap = {d: len(draws) + 1 for d in range(10)}
    for age, rec in enumerate(reversed(draws), start=1):
        d = rec["digits"][pos]
        if gap[d] > len(draws):
            gap[d] = age
    return [gap[d] for d in range(10)]


def sum_digit_conditional(draws, pos):
    """P(和值=sum, 位置pos=digit) 的联合计数 -> 条件分布原料。"""
    joint = [[0] * 10 for _ in range(28)]  # sum 0..27
    sum_tot = [0] * 28
    for rec in draws:
        s = sum(rec["digits"])
        d = rec["digits"][pos]
        joint[s][d] += 1
        sum_tot[s] += 1
    return joint, sum_tot


# ---------------------------------------------------------------- 候选算法
# 每个算法: fn(draws) -> [ranked_digits_pos0, ranked_digits_pos1, ranked_digits_pos2]
# ranked 为长度 10 的列表，按得分降序；同分取数字较小者，保证可复现。

def as_num(digits):
    return int("".join(str(d) for d in digits))


def recent_digit_set(draws, window):
    """近 window 期出现过的数字集合。"""
    s = set()
    for rec in draws[-window:]:
        s.update(rec["digits"])
    return s


def _rank(scores):
    return sorted(range(10), key=lambda d: (-scores[d], d))


def _normalize(arr):
    total = float(sum(arr)) or 1.0
    return [x / total for x in arr]


def a_freq30(draws):
    return [_rank(pos_counts(draws, p, 30)) for p in range(3)]


def b_freq10(draws):
    return [_rank(pos_counts(draws, p, 10)) for p in range(3)]


def c_freq5(draws):
    return [_rank(pos_counts(draws, p, 5)) for p in range(3)]


def d_freqall(draws):
    return [_rank(pos_counts(draws, p)) for p in range(3)]


def e_mix_30_10_all(draws):
    out = []
    for p in range(3):
        c30 = _normalize(pos_counts(draws, p, 30))
        c10 = _normalize(pos_counts(draws, p, 10))
        allc = _normalize(pos_counts(draws, p))
        out.append(_rank([c30[d] * 2 + c10[d] * 0.8 + allc[d] * 0.1 for d in range(10)]))
    return out


def f_dirichlet_global(draws):
    """向"全期全局数字受欢迎度"收缩的贝叶斯位置频率，alpha=3。"""
    out = []
    for p in range(3):
        cnt = pos_counts(draws, p)
        glob = [0] * 10
        for rec in draws:
            for d in rec["digits"]:
                glob[d] += 1
        glob = _normalize(glob)
        n = sum(cnt)
        alpha = 3.0
        out.append(_rank([(cnt[d] + alpha * glob[d]) / (n + alpha) for d in range(10)]))
    return out


def g_recency_eb(draws, tau=50.0):
    """指数递减加权（半衰期 ~34 期），远端样本权重趋零。"""
    out = []
    for p in range(3):
        score = [0.0] * 10
        for age, rec in enumerate(reversed(draws)):
            score[rec["digits"][p]] += math.exp(-age / tau)
        out.append(_rank(score))
    return out


def h_markov1_blend(draws, weight=0.5):
    """一阶 Markov 转移概率 与 全期位置频率 的混合。"""
    out = []
    last = list(draws[-1]["digits"]) if draws else [None] * 3
    for p in range(3):
        trans = transition_matrix(draws, p)
        base = _normalize(pos_counts(draws, p))
        prev = last[p]
        if prev is None:
            out.append(_rank(base))
            continue
        row = trans[prev]
        total = sum(row) + 10
        mark = [(row[d] + 1) / total for d in range(10)]
        out.append(_rank([weight * mark[d] + (1 - weight) * base[d] for d in range(10)]))
    return out


def i_gap_cold(draws):
    """追冷：距上次出现越久得分越高，平局用全期频率降序兜底。"""
    out = []
    for p in range(3):
        gap = last_gap(draws, p)
        base = _normalize(pos_counts(draws, p))
        out.append(_rank([gap[d] + base[d] * 0.5 for d in range(10)]))
    return out


def j_anti_repeat(draws, penalty=1.5):
    """反连号：近 30 期热频，但对上期同位重复数字降权。"""
    out = []
    prev = draws[-1]["digits"] if draws else [None] * 3
    for p in range(3):
        c30 = _normalize(pos_counts(draws, p, 30))
        score = [c30[d] for d in range(10)]
        if prev[p] is not None:
            score[prev[p]] -= penalty * c30[prev[p]] if c30[prev[p]] else penalty * 0.1
        out.append(_rank(score))
    return out


def k_sum_conditional(draws, recent=100, prior=1.0):
    """和值条件模型：用近期和值分布 P(s)，乘历史条件分布 P(位= d | 和值=s)。"""
    recent_draws = draws[-recent:] if len(draws) > recent else draws
    sum_dist = [0.0] * 28
    for rec in recent_draws:
        sum_dist[sum(rec["digits"])] += 1
    sum_dist = _normalize(sum_dist)

    out = []
    for p in range(3):
        joint, sum_tot = sum_digit_conditional(draws, p)
        score = [0.0] * 10
        for s in range(28):
            ps = sum_dist[s]
            if ps <= 0:
                continue
            denom = sum_tot[s] + 10 * prior
            for d in range(10):
                score[d] += ps * ((joint[s][d] + prior) / denom)
        out.append(_rank(score))
    return out


# ---------------------------------------------- 民间方法派生的候选算法
# 对应 scripts/claims.py 里验证过的那些公式，这里把它们改造成可排序的评分模型，
# 放进同一个 900/100 + 分块回测框架里和其他算法同台比较。

def m_012_route(draws, window=100):
    """012路：先估每位各路(mod 3)出现概率，再在路内按历史频率分配。"""
    out = []
    for p in range(3):
        route_cnt = [0, 0, 0]
        for rec in draws[-window:]:
            route_cnt[rec["digits"][p] % 3] += 1
        route_p = _normalize(route_cnt)
        base = _normalize(pos_counts(draws, p))
        out.append(_rank([route_p[d % 3] * (0.5 + base[d] * 10) for d in range(10)]))
    return out


def n_repeat10(draws, window=10, boost=1.0):
    """近 window 期出现过的数字加权（用户提出的「10期重号」假设）。"""
    seen = recent_digit_set(draws, window)
    out = []
    for p in range(3):
        base = _normalize(pos_counts(draws, p, 30))
        out.append(_rank([base[d] + (boost if d in seen else 0.0) for d in range(10)]))
    return out


def o_cold10(draws, window=10, boost=1.0):
    """近 window 期未出现的冷号加权（遗漏回归假设）。"""
    seen = recent_digit_set(draws, window)
    out = []
    for p in range(3):
        base = _normalize(pos_counts(draws, p))
        out.append(_rank([base[d] + (boost if d not in seen else 0.0) for d in range(10)]))
    return out


def p_neighbor(draws, boost=1.0):
    """邻码：上期数字 ±1 加权。"""
    prev = draws[-1]["digits"]
    adj = {(d + 1) % 10 for d in prev} | {(d - 1) % 10 for d in prev}
    out = []
    for p in range(3):
        base = _normalize(pos_counts(draws, p, 30))
        out.append(_rank([base[d] + (boost if d in adj else 0.0) for d in range(10)]))
    return out


def q_hot7(draws, window=7):
    """冷热温（热号定义为近 7 期中出 2 次以上）：近 7 期频次排序。"""
    return [_rank(pos_counts(draws, p, window)) for p in range(3)]


def r_span_target(draws, lo=3, hi=8, window=200):
    """跨度约束：估计 P(跨度落在 lo~hi | 该位取 d)，偏好能形成常见跨度的数字。"""
    window_draws = draws[-window:] if len(draws) > window else draws
    in_range = [dict.fromkeys(range(10), 0) for _ in range(3)]
    for rec in window_draws:
        dg = rec["digits"]
        if lo <= max(dg) - min(dg) <= hi:
            for p in range(3):
                in_range[p][dg[p]] += 1
    n = max(len(window_draws), 1)
    out = []
    for p in range(3):
        base = _normalize(pos_counts(draws, p, 30))
        out.append(_rank([base[d] + in_range[p][d] / n for d in range(10)]))
    return out


def s_kill123(draws):
    """123百位杀号法：排除「上期开奖号×123 的首位数字」出现在百位，其余按频率。"""
    kill = int(str(as_num(draws[-1]["digits"]) * 123)[0])
    out = []
    for p in range(3):
        base = _normalize(pos_counts(draws, p))
        out.append(_rank([-1.0 if (p == 0 and d == kill) else base[d] for d in range(10)]))
    return out


def t_size_parity(draws, window=50, boost=0.3):
    """大小/奇偶 2:1 平衡：近期某侧偏多则向另一侧加权（钟摆理论）。"""
    out = []
    for p in range(3):
        c = pos_counts(draws, p, window)
        big, small = sum(c[5:]), sum(c[:5])
        odd, even = sum(c[1::2]), sum(c[0::2])
        score = []
        for d in range(10):
            s = 1.0
            if big > small and d < 5:
                s += boost
            if small > big and d >= 5:
                s += boost
            if odd > even and d % 2 == 0:
                s += boost
            if even > odd and d % 2 == 1:
                s += boost
            score.append(s)
        out.append(_rank(score))
    return out


def u_golden_dart(draws):
    """黄金定胆：上期开奖号 ×0.618 取前三位，作为优先数字加权。"""
    n = int(as_num(draws[-1]["digits"]) * 0.618)
    darts = [int(c) for c in str(n)[:3]]
    out = []
    for p in range(3):
        base = _normalize(pos_counts(draws, p, 30))
        score = list(base)
        for i, d in enumerate(darts):
            score[d] += (3 - i) * 0.5
        out.append(_rank(score))
    return out


def v_omit_ratio(draws):
    """遗漏比值：当前遗漏 / 该数字历史平均遗漏，比值越高越「该出了」。"""
    n = len(draws)
    out = []
    for p in range(3):
        last_seen = dict.fromkeys(range(10))
        gaps = {d: [] for d in range(10)}
        for i, rec in enumerate(draws):
            d = rec["digits"][p]
            if last_seen[d] is not None:
                gaps[d].append(i - last_seen[d])
            last_seen[d] = i
        score = []
        for d in range(10):
            mean_gap = (sum(gaps[d]) / len(gaps[d])) if gaps[d] else float(n)
            cur = n - 1 - (last_seen[d] if last_seen[d] is not None else -1)
            score.append(cur / max(mean_gap, 1.0))
        out.append(_rank(score))
    return out


def w_duima(draws, boost=0.8):
    """对码法：上期数字的对码 (d+5)%10 加权。"""
    prev = draws[-1]["digits"]
    duima = {(d + 5) % 10 for d in prev}
    out = []
    for p in range(3):
        base = _normalize(pos_counts(draws, p, 30))
        out.append(_rank([base[d] + (boost if d in duima else 0.0) for d in range(10)]))
    return out


def x_sumtail(draws, window=100, prior=1.0):
    """和值尾条件模型：近期和值尾分布 × 历史 P(位=d | 和值尾)。"""
    tails = [0.0] * 10
    for rec in draws[-window:]:
        tails[sum(rec["digits"]) % 10] += 1
    tails = _normalize(tails)
    out = []
    for p in range(3):
        joint = [[0] * 10 for _ in range(10)]
        tot = [0] * 10
        for rec in draws:
            t = sum(rec["digits"]) % 10
            joint[t][rec["digits"][p]] += 1
            tot[t] += 1
        score = [0.0] * 10
        for t in range(10):
            if tails[t] <= 0:
                continue
            den = tot[t] + 10 * prior
            for d in range(10):
                score[d] += tails[t] * ((joint[t][d] + prior) / den)
        out.append(_rank(score))
    return out


# ---------------------------------------------- 第二批：ML / 结构 / 起卦 / 对照

DIFF_PAIRS = {"百十位差": (0, 1), "百个位差": (0, 2), "十个位差": (1, 2)}


def y_diff_pair(draws, window=100):
    """位差分析法：先估三个位差在近期的分布，再给能凑出高概率位差的数字加权。

    位差 |a-b| 的理论分布本身就不均匀（差值1占18%，差值9只占2%），
    所以这里比的是"位差的时间分布是否可预测"，而不是"位差是否均匀"。
    """
    recent = draws[-window:] if len(draws) > window else draws
    n = max(len(recent), 1)
    # 每个位差组合的近期分布
    diff_dist = {}
    for name, (a, b) in DIFF_PAIRS.items():
        cnt = [0] * 10
        for rec in recent:
            cnt[abs(rec["digits"][a] - rec["digits"][b])] += 1
        diff_dist[name] = _normalize(cnt)

    out = []
    for p in range(3):
        base = _normalize(pos_counts(draws, p, 30))
        prev_pair = {}
        for name, (a, b) in DIFF_PAIRS.items():
            prev_pair[name] = abs(draws[-1]["digits"][a] - draws[-1]["digits"][b])
        score = list(base)
        for d in range(10):
            bonus = 0.0
            for name, (a, b) in DIFF_PAIRS.items():
                if p == a:
                    bonus += diff_dist[name][abs(d - prev_pair[name]) % 10]
                elif p == b:
                    bonus += diff_dist[name][abs(prev_pair[name] - d) % 10]
            score[d] += bonus * 0.5
        out.append(_rank(score))
    return out


def aa_markov2(draws, weight=0.5, prior=1.0):
    """二阶马尔可夫：用前两期的同位数字对作为状态，估计下一个数字。"""
    out = []
    for p in range(3):
        trans = {}
        for i in range(2, len(draws)):
            key = (draws[i - 2]["digits"][p], draws[i - 1]["digits"][p])
            trans.setdefault(key, [0] * 10)
            trans[key][draws[i]["digits"][p]] += 1
        base = _normalize(pos_counts(draws, p))
        if len(draws) < 2:
            out.append(_rank(base))
            continue
        key = (draws[-2]["digits"][p], draws[-1]["digits"][p])
        row = trans.get(key)
        if row is None or sum(row) < 5:
            out.append(_rank(base))
            continue
        total = sum(row) + 10 * prior
        mark = [(row[d] + prior) / total for d in range(10)]
        out.append(_rank([weight * mark[d] + (1 - weight) * base[d] for d in range(10)]))
    return out


def ab_skip_number(draws, boost=1.0):
    """隔期号：上上期出现过、但上期没出现的数字加权（民间「隔期号」）。"""
    if len(draws) < 2:
        return [_rank(pos_counts(draws, p)) for p in range(3)]
    prev2 = set(draws[-2]["digits"])
    prev1 = set(draws[-1]["digits"])
    target = prev2 - prev1
    out = []
    for p in range(3):
        base = _normalize(pos_counts(draws, p, 30))
        out.append(_rank([base[d] + (boost if d in target else 0.0) for d in range(10)]))
    return out


# ---- 机器学习基线（sklearn 可用；tensorflow/torch 不在环境里，用 MLP 作 LSTM 的代理）----

FEATURE_WINDOWS = (5, 10, 30, 100)


def _position_features(draws, p):
    """给某个位置构造特征向量（全部只用历史数据）。"""
    n = len(draws)
    feats = []
    for w in FEATURE_WINDOWS:
        cnt = pos_counts(draws, p, min(w, n))
        tot = max(sum(cnt), 1)
        feats.extend([c / tot for c in cnt])
    gap = last_gap(draws, p)
    feats.extend([min(g, 200) / 200 for g in gap])
    base = _normalize(pos_counts(draws, p))
    feats.extend(base)
    # 上期、上上期同位数字的 one-hot
    for offset in (1, 2):
        oh = [0.0] * 10
        if n >= offset:
            oh[draws[-offset]["digits"][p]] = 1.0
        feats.extend(oh)
    # 上期各位作为整体信息（和值、跨度、上下文位置）
    if n >= 1:
        dg = draws[-1]["digits"]
        feats.extend([sum(dg) / 27.0, (max(dg) - min(dg)) / 9.0])
        feats.extend([d / 9.0 for d in dg])
    else:
        feats.extend([0.0] * 5)
    return feats


_ML_CACHE = {}


def _ml_predict(draws, p, model_factory, model_tag, train_window=600, retrain_every=100):
    """滚动训练：用「不晚于当前期」的数据训练，预测当期。

    训练一次可服务同一段内的多期预测（训练集始终是前缀，无未来泄漏）。
    结果按 (模型, 位置, 训练集指纹) 缓存，否则整轮回测要跑几个小时。

    指纹用训练段末两期的实际号码，能唯一对应一份训练集内容。
    """
    n = len(draws)
    if n < 120:
        return None
    train_end = ((n - 1) // retrain_every) * retrain_every
    train_start = max(0, train_end - train_window)
    if train_end - train_start < 100:
        return None
    key = (model_tag, p, train_start, train_end,
           tuple(draws[train_start]["digits"]), tuple(draws[train_end - 1]["digits"]))
    if key not in _ML_CACHE:
        X, y = [], []
        for i in range(train_start + 2, train_end):
            X.append(_position_features(draws[:i], p))
            y.append(draws[i]["digits"][p])
        if len(set(y)) < 2:
            _ML_CACHE[key] = None
        else:
            clf = model_factory()
            clf.fit(X, y)
            _ML_CACHE[key] = (clf, list(clf.classes_))
    cached = _ML_CACHE[key]
    if cached is None:
        return None
    clf, classes = cached
    proba = clf.predict_proba([_position_features(draws[:n], p)])[0]
    score = [0.0] * 10
    for cls, pr in zip(classes, proba):
        score[int(cls)] = pr
    return _rank(score)


def _ml_logreg(draws):
    from sklearn.linear_model import LogisticRegression
    out = []
    for p in range(3):
        r = _ml_predict(draws, p, lambda: LogisticRegression(max_iter=400, C=0.5), "logreg")
        out.append(r if r is not None else _rank(pos_counts(draws, p)))
    return out


def _ml_gbm(draws):
    from sklearn.ensemble import HistGradientBoostingClassifier
    out = []
    for p in range(3):
        r = _ml_predict(draws, p, lambda: HistGradientBoostingClassifier(
            max_iter=60, learning_rate=0.1, max_depth=3, random_state=0), "gbm")
        out.append(r if r is not None else _rank(pos_counts(draws, p)))
    return out


def _ml_mlp(draws):
    """小型前馈网络 —— LSTM/深度学习的可负担代理（环境无 tensorflow/torch）。"""
    from sklearn.neural_network import MLPClassifier
    out = []
    for p in range(3):
        r = _ml_predict(draws, p, lambda: MLPClassifier(
            hidden_layer_sizes=(32,), max_iter=120, random_state=0, early_stopping=False), "mlp")
        out.append(r if r is not None else _rank(pos_counts(draws, p)))
    return out


# ---- 六爻起卦（本项目对大乐透用过的方法，这里同样纳入回测）----

TRIGRAM_BY_BINARY = {7: 1, 3: 2, 5: 3, 1: 4, 6: 5, 2: 6, 4: 7, 0: 8}  # 先天八卦序


def _toss_lines(seed):
    """三枚铜钱掷六次，返回 6 个爻值 (6=老阴 7=少阳 8=少阴 9=老阳)。"""
    rng = random.Random(seed)
    return [sum(rng.choice((2, 3)) for _ in range(3)) for _ in range(6)]


def _hexagram_digit(seed):
    """由卦象推出一个 0-9 的数字。

    规则（本实现自定，传统流派差异很大）：
      下卦/上卦各自按「阳=1 阴=0、自下而上」取二进制值 -> 先天八卦数 1~8
      动爻数 = 老阴/老阳的个数
      数字 = (上卦数 + 下卦数 + 动爻数) % 10
    """
    lines = _toss_lines(seed)
    yin_yang = [1 if v in (7, 9) else 0 for v in lines]
    low = yin_yang[0] + yin_yang[1] * 2 + yin_yang[2] * 4
    up = yin_yang[3] + yin_yang[4] * 2 + yin_yang[5] * 4
    changing = sum(1 for v in lines if v in (6, 9))
    return (TRIGRAM_BY_BINARY[up] + TRIGRAM_BY_BINARY[low] + changing) % 10


def af_liuyao(draws):
    """按「下一期期号」起卦，每位独立起一卦，卦得数字优先。"""
    if not draws:
        return [_rank([0] * 10) for _ in range(3)]
    next_num = str(int(draws[-1]["num"]) + 1)
    out = []
    for p in range(3):
        dart = _hexagram_digit(f"{next_num}-{p}")
        base = _normalize(pos_counts(draws, p, 30))
        score = list(base)
        score[dart] += 10.0
        out.append(_rank(score))
    return out


def ag_random_control(draws):
    """均匀随机对照（按"下一期期号+位置"固定种子，可复现）。

    作用不是预测，而是验证回测框架本身：它必须落在 20% 附近。
    若它也"排进前几名"，说明整个选优过程就是噪声。
    """
    next_num = str(int(draws[-1]["num"]) + 1) if draws else "0"
    out = []
    for p in range(3):
        rng = random.Random(f"ctrl-{next_num}-{p}")
        order = list(range(10))
        rng.shuffle(order)
        out.append(order)
    return out


def z_prob_ensemble(draws):
    """默认主算法：4 个概率型模型的等权集成（F/G/H/K）。"""
    parts = [f_dirichlet_global(draws), g_recency_eb(draws), h_markov1_blend(draws), k_sum_conditional(draws)]
    out = []
    for p in range(3):
        acc = [0.0] * 10
        for part in parts:
            ordered = part[p]
            for rank_i, d in enumerate(ordered):
                acc[d] += (10 - rank_i) / 10.0  # 名次折成分数，避免量纲不一致
        out.append(_rank(acc))
    return out


ALGORITHMS = {
    "A_freq30": a_freq30,
    "B_freq10": b_freq10,
    "C_freq5": c_freq5,
    "D_freqAll": d_freqall,
    "E_mix_30_10_all": e_mix_30_10_all,
    "F_dirichlet_global": f_dirichlet_global,
    "G_recency_eb": g_recency_eb,
    "H_markov1_blend": h_markov1_blend,
    "I_gap_cold": i_gap_cold,
    "J_anti_repeat": j_anti_repeat,
    "K_sum_conditional": k_sum_conditional,
    "Z_prob_ensemble": z_prob_ensemble,
    # --- 民间方法派生 ---
    "M_012_route": m_012_route,
    "N_repeat10": n_repeat10,
    "O_cold10": o_cold10,
    "P_neighbor": p_neighbor,
    "Q_hot7": q_hot7,
    "R_span_target": r_span_target,
    "S_kill123": s_kill123,
    "T_size_parity": t_size_parity,
    "U_golden_dart": u_golden_dart,
    "V_omit_ratio": v_omit_ratio,
    "W_duima": w_duima,
    "X_sumtail": x_sumtail,
    # --- 第二批：ML / 结构 / 起卦 / 对照 ---
    "Y_diff_pair": y_diff_pair,
    "AA_markov2": aa_markov2,
    "AB_skip_number": ab_skip_number,
    "AC_ml_logreg": _ml_logreg,
    "AD_ml_gbm": _ml_gbm,
    "AE_ml_mlp": _ml_mlp,
    "AF_liuyao": af_liuyao,
    "AG_random_control": ag_random_control,
}


# ---------------------------------------------------------------- 回测

def evaluate_range(draws, start, end, min_history=30):
    """对 draws[start:end] 的每一期做"只用其之前数据训练"的滚动回测。"""
    results = {}
    for name, fn in ALGORITHMS.items():
        top1 = top2 = top3 = 0
        exact_top1 = exact_top2 = 0
        trials = 0
        for i in range(start, end):
            hist = draws[:i]
            if len(hist) < min_history:
                continue
            actual = draws[i]["digits"]
            ranked = fn(hist)
            trials += 1
            ok1 = ok2 = 0
            for p in range(3):
                if actual[p] == ranked[p][0]:
                    top1 += 1
                    ok1 += 1
                if actual[p] in ranked[p][:2]:
                    top2 += 1
                    ok2 += 1
                if actual[p] in ranked[p][:3]:
                    top3 += 1
            if ok1 == 3:
                exact_top1 += 1
            if ok2 == 3:
                exact_top2 += 1
        pos_trials = trials * 3
        results[name] = {
            "periods": trials,
            "top1PosRate": round(top1 / pos_trials, 4) if pos_trials else 0.0,
            "top2PosRate": round(top2 / pos_trials, 4) if pos_trials else 0.0,
            "top3PosRate": round(top3 / pos_trials, 4) if pos_trials else 0.0,
            "exactTop1": exact_top1,
            "exactTop2": exact_top2,
        }
    return results


def evaluate(draws, train_size=TRAIN_SIZE, holdout_size=HOLDOUT_SIZE):
    """滚动回测：对每个留出期，只用其之前的数据训练。"""
    n = len(draws)
    start = max(train_size, n - holdout_size)
    return evaluate_range(draws, start, n)


def select_algorithm(draws, results, block=100, blocks=8, alpha=0.05):
    """选优协议（避免靠单个 100 期留出集的噪声选算法）。

    1. 主排序：8 个独立 100 期分块的 Top-2 覆盖率均值（2400 个位置样本，比单块可靠）
    2. 并列时：900/100 单一留出集覆盖率
    3. 同时给出均排名/排名波动，以及相对 20% 基线的二项检验 p 值与 Bonferroni 校正结论
    """
    per_block = block_stability(draws, block, blocks)
    rows = []
    if per_block:
        labels = [label for label, _ in per_block]
        # 每个分块的合法样本数（min_history 会吃掉每块开头若干期）
        blocks_pos = sum(res[first]["periods"] * 3 for _, res in per_block for first in [next(iter(res))])
        for name in ALGORITHMS:
            rates, ranks = [], []
            for _, res in per_block:
                order = sorted(res.items(), key=lambda kv: kv[1]["top2PosRate"], reverse=True)
                ranks.append([k for k, _ in order].index(name) + 1)
                rates.append(res[name]["top2PosRate"])
            rows.append({
                "name": name,
                "rates": [round(r, 4) for r in rates],
                "ranks": ranks,
                "avgRate": round(sum(rates) / len(rates), 4),
                "avgRank": round(sum(ranks) / len(ranks), 2),
                "rankSpread": max(ranks) - min(ranks),
                "holdoutRate": results[name]["top2PosRate"],
            })
    else:
        labels, blocks_pos = [], 0

    n_algo = len(ALGORITHMS)
    bonf = alpha / n_algo
    z_gate = stats.norm.ppf(1 - bonf)
    baseline = 0.20
    gate = baseline + z_gate * math.sqrt(baseline * 0.8 / max(blocks_pos, 1))

    enriched = list(rows)

    for item in enriched:
        k = round(item["avgRate"] * blocks_pos)
        pval = stats.binomtest(k, blocks_pos, baseline, alternative="greater").pvalue
        item["pValueVsBaseline"] = round(pval, 6)
        item["significantAfterCorrection"] = bool(pval < bonf and item["avgRate"] > gate)

    enriched.sort(key=lambda r: (-r["avgRate"], -r["holdoutRate"], r["avgRank"]))
    meta = {
        "blocks": labels,
        "positionSamples": blocks_pos,
        "baseline": baseline,
        "bonferroniAlpha": round(bonf, 6),
        "gateRate": round(gate, 4),
        "anySignificant": any(r["significantAfterCorrection"] for r in enriched),
    }
    return enriched, meta


def pick_best(results):
    """单留出集排序（仅用于报告，不作为算法选择依据）。"""
    return sorted(
        results.items(),
        key=lambda kv: (kv[1]["top2PosRate"], kv[1]["top1PosRate"], kv[1]["top3PosRate"], -kv[1]["periods"]),
        reverse=True,
    )


# ---------------------------------------------------------------- 形态统计

def form_of(digits):
    uniq = len(set(digits))
    if uniq == 1:
        return "豹子"
    if uniq == 2:
        return "组三"
    return "组六"


def block_stability(draws, block=100, blocks=4):
    """分块稳定性：把最近 blocks*block 期切成独立块，各自回测。

    若某算法只是靠噪声胜出，它不会在多个块里持续领先 —— 排名会大幅抖动。
    """
    n = len(draws)
    out = []
    for b in range(blocks):
        end = n - b * block
        start = end - block
        if start < 200:
            break
        block_results = evaluate_range(draws, start, end)
        out.append((f"{draws[start]['num']}~{draws[end - 1]['num']}", block_results))
    return out


def rank_table(draws, block=100, blocks=4):
    per_block = block_stability(draws, block, blocks)
    if not per_block:
        return []
    names = list(ALGORITHMS)
    rows = []
    for name in names:
        rates, ranks = [], []
        for _, res in per_block:
            order = sorted(res.items(), key=lambda kv: kv[1]["top2PosRate"], reverse=True)
            rank = [k for k, _ in order].index(name) + 1
            ranks.append(rank)
            rates.append(res[name]["top2PosRate"])
        rows.append({
            "name": name,
            "rates": [round(r, 4) for r in rates],
            "ranks": ranks,
            "avgRank": round(sum(ranks) / len(ranks), 2),
            "rankSpread": max(ranks) - min(ranks),
            "avgRate": round(sum(rates) / len(rates), 4),
        })
    return rows, [label for label, _ in per_block]


def descriptive_stats(draws, recent=100):
    seq = draws[-recent:]
    sums = [sum(r["digits"]) for r in seq]
    spans = [max(r["digits"]) - min(r["digits"]) for r in seq]
    forms = {"豹子": 0, "组三": 0, "组六": 0}
    for r in seq:
        forms[form_of(r["digits"])] += 1
    odd_cnt = [sum(1 for d in r["digits"] if d % 2) for r in seq]
    big_cnt = [sum(1 for d in r["digits"] if d >= 5) for r in seq]
    repeats = sum(
        1 for a, b in zip(seq, seq[1:]) if set(a["digits"]) & set(b["digits"])
    )
    digit_freq = [0] * 10
    for r in seq:
        for d in r["digits"]:
            digit_freq[d] += 1
    return {
        "window": len(seq),
        "sumAvg": round(sum(sums) / len(sums), 2),
        "sumMin": min(sums),
        "sumMax": max(sums),
        "spanAvg": round(sum(spans) / len(spans), 2),
        "formDist": forms,
        "oddCountDist": {str(k): odd_cnt.count(k) for k in sorted(set(odd_cnt))},
        "bigCountDist": {str(k): big_cnt.count(k) for k in sorted(set(big_cnt))},
        "repeatWithPrevRate": round(repeats / max(len(seq) - 1, 1), 4),
        "digitFreq": {str(d): digit_freq[d] for d in range(10)},
    }


# ---------------------------------------------------------------- 输出

def build_prediction(draws, algo_name):
    fn = ALGORITHMS[algo_name]
    ranked = fn(draws)
    return {
        "mainTicket": [ranked[p][0] for p in range(3)],
        "top2": [sorted(ranked[p][:2]) for p in range(3)],
        "top3": [sorted(ranked[p][:3]) for p in range(3)],
        "rankedPerPosition": ranked,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", type=int, default=TRAIN_SIZE)
    parser.add_argument("--holdout", type=int, default=HOLDOUT_SIZE)
    parser.add_argument("--write-model", action="store_true", help="把回测结果写入 model.json")
    args = parser.parse_args()

    with open(DRAWS_PATH, encoding="utf-8") as fh:
        draws = json.load(fh)

    n = len(draws)
    start = max(args.train, n - args.holdout)
    print(f"样本 {n} 期 ({draws[0]['num']} ~ {draws[-1]['num']})")
    print(f"训练段 draws[:{start}]，留出段 draws[{start}:{n}]（{n - start} 期）\n")

    results = evaluate(draws, args.train, args.holdout)
    ranked_algs = pick_best(results)

    header = f"{'算法':<22}{'Top-1位':>9}{'Top-2位':>9}{'Top-3位':>9}{'三位全中':>9}{'Top2全中':>10}"
    print(header)
    print("-" * len(header))
    for name, m in ranked_algs:
        print(
            f"{name:<22}{m['top1PosRate']:>8.2%}{m['top2PosRate']:>9.2%}"
            f"{m['top3PosRate']:>9.2%}{m['exactTop1']:>9}{m['exactTop2']:>10}"
        )
    print("\n随机基线              " f"{0.10:>8.2%}{0.20:>9.2%}{0.30:>9.2%}{'~0.1':>9}{'~0.8':>10}")

    best = ranked_algs[0][0]
    print(f"\n>>> 留出集最优: {best}  Top-2覆盖率 {results[best]['top2PosRate']:.2%}")

    selected, meta = select_algorithm(draws, results, block=100, blocks=8)
    if selected:
        print(f"\n分块稳定性（{len(meta['blocks'])} 个各 100 期独立回测，共 {meta['positionSamples']} 个位置样本）：")
        print(f"{'算法':<22}" + "".join(f"{lb:>12}" for lb in meta["blocks"])
              + f"{'均值':>9}{'均排名':>7}{'波动':>5}{'p值':>9}")
        for row in selected:
            cells = "".join(f"{r * 100:>8.1f}%" for r in row["rates"])
            print(f"{row['name']:<22}{cells}{row['avgRate']:>8.2%}{row['avgRank']:>7}"
                  f"{row['rankSpread']:>5}{row['pValueVsBaseline']:>9.3f}")
        print(f"  随机基线 20.00%；Bonferroni 校正门槛（{len(ALGORITHMS)} 个算法，"
              f"alpha={meta['bonferroniAlpha']:.5f}）= {meta['gateRate']:.2%}")
        print(f"  有任何算法显著优于随机：{'是' if meta['anySignificant'] else '否 —— 全部落在抽样噪声内'}")
        print("  解读：若算法真有预测力，应在多数分块里稳定靠前；排名波动大 = 优势来自噪声。")

    best = selected[0]["name"] if selected else ranked_algs[0][0]
    print(f"\n>>> 选优协议胜出: {best}  分块均值 {selected[0]['avgRate']:.2%}"
          f"（单一留出集 {results[best]['top2PosRate']:.2%}）" if selected else f"\n>>> 选出: {best}")

    prediction = build_prediction(draws, best)
    print(f"下一期主推: {' '.join(str(d) for d in prediction['mainTicket'])}")
    print(f"Top-2 候选: " + "  ".join("/".join(map(str, x)) for x in prediction["top2"]))
    print(f"Top-3 候选: " + "  ".join("/".join(map(str, x)) for x in prediction["top3"]))

    recent = descriptive_stats(draws)
    print(f"\n近100期形态: {recent['formDist']}  和值均值 {recent['sumAvg']}  跨度均值 {recent['spanAvg']}"
          f"  与上期重号率 {recent['repeatWithPrevRate']:.2%}")

    if args.write_model:
        model = {
            "version": 1,
            "game": "排列三",
            "gameNo": "35",
            "optimizationTarget": "positional top2-coverage",
            "activeAlgorithm": best,
            "honesty": {
                "conclusion": "全部候选算法均未显著优于随机基线，历史数据中未发现可利用信号。",
                "anyAlgorithmSignificant": meta["anySignificant"],
                "sourceOfSelection": "8 个独立 100 期分块的 Top-2 覆盖率均值",
                "payoutRatio": 0.53,
                "note": "排列三为固定奖金 (直选1040/组选3 346/组选6 173 元，每注2元)，"
                        "返奖率约 53%。即使存在微小概率优势，也不改变长期负期望。",
            },
            "backtest": {
                "trainSize": start,
                "holdoutSize": n - start,
                "metric": "top2PosRate",
                "randomBaseline": {"top1": 0.10, "top2": 0.20, "top3": 0.30},
            },
            "selectionProtocol": meta,
            "algorithmBenchmarks": [
                {"name": name, **m, "selected": name == best} for name, m in ranked_algs
            ],
            "blockStability": selected,
            "performance": {"totalPredictions": 0, "hits": {"0": 0, "1": 0, "2": 0, "3": 0}},
            "recentStats": recent,
            "latest": draws[-1],
            "updatedAt": draws[-1]["date"],
        }
        with open(MODEL_PATH, "w", encoding="utf-8") as fh:
            json.dump(model, fh, ensure_ascii=False, indent=1)
        print(f"\n已写入 {MODEL_PATH}")


if __name__ == "__main__":
    main()
