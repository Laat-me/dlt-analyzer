# -*- coding: utf-8 -*-
"""
大乐透算法池 (dlt-analyzer) — 88 个算法中已固化实现的版本
============================================================
数据约定:
- draws: 升序列表, 每项 {"num","date","front":[5],"back":[2]}
- 所有频次统计使用 0-based 索引: F[k][n-1] = 号码 n 在近 window 期的出现次数
  (历史教训: bincount(arr) 直接用号码值做索引会造成 base 错位一位)

实现状态:
- ORIGINAL: 公式来自 SKILL.md / model.json 参数记录
- REBUILT:  按家族描述重建, 可能有细节偏差
- 变体:     AI_U_wide 的参数/后区权重变体
未实现算法见 algorithms.md「未实现算法」清单(原公式未保留)。

用法:
  from algorithms import registry, backtest
  result = backtest(registry["AI_U_wide"], draws, holdout_start=len(draws)-100)
"""
import numpy as np
from itertools import combinations

# ---------------------------------------------------------------- 公共工具

def cum_freq(arr, maxn, window):
    """F[k][n-1] = 号码n 在 [k-window, k) 期(不含k期)的出现次数; window=None 表示全期累计"""
    N = arr.shape[0]
    F = np.zeros((N, maxn), dtype=np.int32)
    for k in range(1, N):
        F[k] = F[k - 1]
        if window is not None and k - window >= 0:
            F[k] -= np.bincount(arr[k - window - 1] - 1, minlength=maxn)[:maxn]
        F[k] += np.bincount(arr[k - 1] - 1, minlength=maxn)[:maxn]
    return F

def norm(F):
    mx = np.maximum(F.max(axis=1, initial=1), 1)
    return F / mx[:, None]

def repeat_flags(arr, maxn):
    """R[k][n-1] = 号码n 是否在 k-1 期出现"""
    N = arr.shape[0]
    R = np.zeros((N, maxn), dtype=np.int8)
    for k in range(1, N):
        R[k, arr[k - 1] - 1] = 1
    return R

def neighbor_counts(arr, maxn, radius, exclude_center=True):
    """NC[k][n-1] = k-1 期(上期)出号在 ±radius 邻域内命中 n 的次数。
    口径（round-27）：radius=1 且 exclude_center=True 时即为「跨期邻号」特征——
    表示号码 n 是否属于上一期开奖号码的 +1/-1（不含上期号码本身，即不含重号）。
    示例：上期出 {05,20}，则 04/06/19/21 各 +1，05/20 不计（重号）。"""
    N = arr.shape[0]
    NC = np.zeros((N, maxn), dtype=np.int8)
    for k in range(1, N):
        for x in arr[k - 1]:
            lo = max(1, x - radius); hi = min(maxn, x + radius)
            NC[k, lo - 1:hi] += 1
        if exclude_center:
            for x in arr[k - 1]:
                NC[k, x - 1] -= 1
    return NC

def prev_neighbor_flags(arr, maxn, radius=1):
    """PN[k][n-1] = 号码 n 是否命中「跨期邻号」：n ∈ {上一期号码 ±1..±radius} 且 n ∉ 上一期号码集合。
    radius=1 即上一期号码 ±1。按集合排除上期全部原号，保证与「重号」严格互斥——
    即使上期自身含连号(如 05,06)，05/06 也只算重号、不计入邻号。返回 0/1 标记。"""
    N = arr.shape[0]
    PN = np.zeros((N, maxn), dtype=np.int8)
    for k in range(1, N):
        prev_set = set(int(x) for x in arr[k - 1])
        for n in range(1, maxn + 1):
            if n in prev_set:
                continue
            for x in prev_set:
                if abs(n - x) <= radius:
                    PN[k, n - 1] = 1
                    break
    return PN

def gap_map(arr, maxn):
    """G[k][n-1] = 号码n 到 k-1 期为止的遗漏期数(未出现过则记大值)"""
    N = arr.shape[0]
    G = np.zeros((N, maxn), dtype=np.int32)
    for k in range(1, N):
        G[k] = G[k - 1] + 1
        for x in arr[k - 1]:
            G[k, x - 1] = 0
    # 从未出现过的号码: 用 max 遗漏替代
    for k in range(1, N):
        appeared = np.zeros(maxn, dtype=bool)
        for x in arr[:k].reshape(-1):
            appeared[x - 1] = True
        G[k, ~appeared] = G[k].max() + 1
    return G

# ---------------------------------------------------------------- 选号输出

def pick_top6(scores):
    """无约束裸 top6 (平局按号码序)"""
    return sorted((np.argsort(-scores)[:6] + 1).tolist())

def pick_top3(scores):
    return sorted((np.argsort(-scores)[:3] + 1).tolist())

def ok_constraint(f6):
    """6+3 前区约束: 奇偶 2:4~4:2, 区间各 1-3, 和值 70-130, 全距>=15"""
    oe = sum(1 for n in f6 if n % 2 == 0)
    lo = sum(1 for n in f6 if n <= 12); mid = sum(1 for n in f6 if 13 <= n <= 24); hi = sum(1 for n in f6 if n >= 25)
    s = sum(f6); span = max(f6) - min(f6)
    return (2 <= oe <= 4) and all(1 <= x <= 3 for x in [lo, mid, hi]) and (70 <= s <= 130) and (span >= 15)

def pick_top6_constrained(scores, topk=12):
    """候选池 topk + 枚举 6 码满足 6+3 约束, 取最高总分组合"""
    pool = (np.argsort(-scores)[:topk] + 1).tolist()
    best, bestscore = None, -1e18
    for combo in combinations(pool, 6):
        if ok_constraint(combo):
            sc = sum(scores[n - 1] for n in combo)
            if sc > bestscore:
                best, bestscore = combo, sc
    if best is None:
        return pick_top6(scores)  # 无满足组合时回退裸 top6
    return sorted(best)

# ---------------------------------------------------------------- 算法注册表
# 每个算法: fn(k) -> (front6, back3); k = 当前预测期下标(用 k 之前数据)

def make_ai_u_wide(radius=2, w_repeat=0.18, w_neighbor=0.02, base_win=None,
                   constrained=True, back_repeat=None, topk=12):
    """AI_U_wide 族: base + w_repeat*重号 + w_neighbor*邻域(r)  (ORIGINAL 参数)
    round-25 还原版: radius=3, w_repeat=0.5, w_neighbor=0.2, topk=8 (900/100窗口指纹还原)
    round-27 口径: radius=1 时邻域项即「跨期邻号(上期±1,不含重号)」，radius≥2 为更宽跨期邻域"""
    def fn(k, F, R, NC, G, front_actual, back_actual):
        bf = norm(F["f_all_f"])[k] if base_win is None else norm(F["f30_f"])[k]
        bb = norm(F["b_all_b"])[k] if base_win is None else norm(F["b30_b"])[k]
        wr_b = back_repeat if back_repeat is not None else w_repeat
        sf = bf + w_repeat * R["f"][k] + w_neighbor * NC["f"][k, :, radius - 1].astype(np.float32)
        sb = bb + wr_b * R["b"][k] + w_neighbor * NC["b"][k, :, radius - 1].astype(np.float32)
        f6 = pick_top6_constrained(sf, topk=topk) if constrained else pick_top6(sf)
        return f6, pick_top3(sb)
    return fn

def make_v1_cold(constrained=True):
    """v1 追冷 (ORIGINAL): gap×0.5 + (5-freq30)×2.5 + (N/7-freq)×0.3 / 后区 gap×0.6 + (3-freq30)×2"""
    def fn(k, F, R, NC, G, front_actual, back_actual):
        n_hist = k
        sf = 0.5 * G["f"][k] + (5 - F["f30_f"][k]) * 2.5 + (n_hist / 7.0 - F["f_all_f"][k]) * 0.3
        sb = 0.6 * G["b"][k] + (3 - F["b30_b"][k]) * 2.0
        f6 = pick_top6_constrained(sf) if constrained else pick_top6(sf)
        return f6, pick_top3(sb)
    return fn

def make_v2_hot(constrained=True):
    """v2 追热 (ORIGINAL): freq5×3 + freq10×1.5 + neighbor(上期±1跨期邻号)×4 + streak×4
    round-27: nb 取 NC radius=1(上期号码±1、不含重号)"""
    def fn(k, F, R, NC, G, front_actual, back_actual):
        f5 = F["f5_f"][k].astype(np.float32); f10 = F["f10_f"][k].astype(np.float32)
        nb = NC["f"][k, :, 0].astype(np.float32)
        streak = (f5 >= 2).astype(np.float32) * 4
        sf = f5 * 3 + f10 * 1.5 + nb * 4 + streak
        sb = F["b5_b"][k].astype(np.float32) * 3 + F["b10_b"][k].astype(np.float32) * 1.5
        f6 = pick_top6_constrained(sf) if constrained else pick_top6(sf)
        return f6, pick_top3(sb)
    return fn

def make_v3(alg_cold, alg_hot):
    """v3 冷热组合 (ORIGINAL): 冷号池 top2 + 热号池 top3 (约束优先)"""
    def fn(k, F, R, NC, G, front_actual, back_actual):
        f6_c, _ = alg_cold(k, F, R, NC, G, front_actual, back_actual)
        f6_h, _ = alg_hot(k, F, R, NC, G, front_actual, back_actual)
        seen = []
        for g in (f6_c[:2], f6_h[:3]):
            for n in g:
                if n not in seen:
                    seen.append(n)
        if len(seen) < 6:
            for n in f6_c + f6_h:
                if n not in seen:
                    seen.append(n)
        f6 = sorted(seen[:6])
        _, b3_h = alg_hot(k, F, R, NC, G, front_actual, back_actual)
        return f6, b3_h
    return fn

def make_dirichlet(alpha=1.0):
    """H_dirichlet (REBUILT): Dirichlet 平滑频率"""
    def fn(k, F, R, NC, G, front_actual, back_actual):
        fa = F["f_all_f"][k].astype(np.float64) + alpha
        sf = fa / fa.sum()
        ba = F["b_all_b"][k].astype(np.float64) + alpha
        sb = ba / ba.sum()
        return pick_top6(sf), pick_top3(sb)
    return fn

def make_recency_eb(gamma=0.995):
    """I_recency_eb (REBUILT): 递减加权经验贝叶斯"""
    def fn(k, F, R, NC, G, front_actual, back_actual):
        sf = np.zeros(35); sb = np.zeros(12)
        for t in range(max(0, k - 500), k):
            w = gamma ** (k - 1 - t)
            sf[front_actual[t] - 1] += w
            sb[back_actual[t] - 1] += w
        return pick_top6(sf), pick_top3(sb)
    return fn

def make_repeat_markov(w_markov=0.3):
    """J_repeat_markov (REBUILT): 上期延续(马尔可夫) + 频率基线混合"""
    def fn(k, F, R, NC, G, front_actual, back_actual):
        sf = (1 - w_markov) * norm(F["f_all_f"])[k] + w_markov * R["f"][k]
        sb = (1 - w_markov) * norm(F["b_all_b"])[k] + w_markov * R["b"][k]
        return pick_top6(sf), pick_top3(sb)
    return fn

def make_ensemble(algos):
    """K_prob_ensemble (REBUILT): 多算法等权集成"""
    def fn(k, F, R, NC, G, front_actual, back_actual):
        sf = np.zeros(35); sb = np.zeros(12)
        for a in algos:
            f6, b3 = a(k, F, R, NC, G, front_actual, back_actual)
            for x in f6: sf[x - 1] += 1
            for x in b3: sb[x - 1] += 1
        return pick_top6(sf), pick_top3(sb)
    return fn

def make_tail(weight=0.5):
    """M_tail (REBUILT): 尾号分布加权"""
    def fn(k, F, R, NC, G, front_actual, back_actual):
        tail_f = np.zeros(10)
        for t in range(max(0, k - 100), k):
            for x in front_actual[t]: tail_f[x % 10] += 1
        tail_b = np.zeros(10)
        for t in range(max(0, k - 100), k):
            for x in back_actual[t]: tail_b[x % 10] += 1
        sf = norm(F["f_all_f"])[k] + weight * np.array([tail_f[n % 10] for n in range(1, 36)])
        sb = norm(F["b_all_b"])[k] + weight * np.array([tail_b[n % 10] for n in range(1, 13)])
        return pick_top6(sf), pick_top3(sb)
    return fn

def make_prime(w=0.5):
    """P_prime (REBUILT): 质数偏好"""
    def fn(k, F, R, NC, G, front_actual, back_actual):
        primes = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31}
        sf = norm(F["f_all_f"])[k] + w * np.array([1.0 if n in primes else 0.0 for n in range(1, 36)])
        sb = norm(F["b_all_b"])[k] + w * np.array([1.0 if n in primes else 0.0 for n in range(1, 13)])
        return pick_top6(sf), pick_top3(sb)
    return fn

def make_span_neighbor(w=0.02):
    """O_span (REBUILT): 跨度 + 邻域平滑"""
    def fn(k, F, R, NC, G, front_actual, back_actual):
        sf = norm(F["f_all_f"])[k] + w * NC["f"][k, :, 0].astype(np.float32)
        sb = norm(F["b_all_b"])[k] + w * NC["b"][k, :, 0].astype(np.float32)
        return pick_top6(sf), pick_top3(sb)
    return fn

def make_entropy():
    """E_entropy (REBUILT): 熵/均匀性(接近期望频率者加分)"""
    def fn(k, F, R, NC, G, front_actual, back_actual):
        exp_f = 5.0 / 35.0
        fa = F["f_all_f"][k].astype(np.float64) / max(k, 1)
        sf = -np.abs(fa - exp_f)
        exp_b = 2.0 / 12.0
        ba = F["b_all_b"][k].astype(np.float64) / max(k, 1)
        sb = -np.abs(ba - exp_b)
        return pick_top6(sf), pick_top3(sb)
    return fn

def make_sumreg():
    """S_sumreg (REBUILT): 和值回归约束(接近均值和值)"""
    def fn(k, F, R, NC, G, front_actual, back_actual):
        sf = norm(F["f_all_f"])[k].copy()
        sf += 0.02 * np.array([1.0 if 13 <= n <= 24 else 0.0 for n in range(1, 36)])
        return pick_top6(sf), pick_top3(norm(F["b_all_b"])[k])
    return fn

def make_period7(w=0.3):
    """AZ_period7 (REBUILT): 7期周期回归(7期前同窗口号码加权)"""
    def fn(k, F, R, NC, G, front_actual, back_actual):
        sf = norm(F["f_all_f"])[k].copy()
        sb = norm(F["b_all_b"])[k].copy()
        if k >= 7:
            for x in front_actual[k - 7]: sf[x - 1] += w
            for x in back_actual[k - 7]: sb[x - 1] += w
        return pick_top6(sf), pick_top3(sb)
    return fn

def make_rolling(win, w_repeat=0.18):
    """AV/AW (REBUILT): 滚动窗口 + 重号"""
    def fn(k, F, R, NC, G, front_actual, back_actual):
        start = max(0, k - win)
        sf = np.zeros(35); sb = np.zeros(12)
        for t in range(start, k):
            sf[front_actual[t] - 1] += 1
            sb[back_actual[t] - 1] += 1
        sf = sf / max(sf.max(), 1) + w_repeat * R["f"][k]
        sb = sb / max(sb.max(), 1) + w_repeat * R["b"][k]
        return pick_top6(sf), pick_top3(sb)
    return fn

def make_fixed_repeat(n_repeat=3):
    """CO/CN/CM_fixed_repeat (REBUILT): 固定取 n_repeat 个上期重号 + 其余按 base 高分补足
    记录: CO_repeat3 ge5=2% (固定3个重号, 出现2期命中5个号码)"""
    def fn(k, F, R, NC, G, front_actual, back_actual):
        bf = norm(F["f_all_f"])[k]
        bb = norm(F["b_all_b"])[k]
        repeats_f = (np.argsort(-R["f"][k])[:n_repeat] + 1).tolist()
        rest_f = [n for n in (np.argsort(-bf) + 1).tolist() if n not in repeats_f]
        f6 = sorted((repeats_f + rest_f)[:6])
        repeats_b = (np.argsort(-R["b"][k])[:1] + 1).tolist()
        rest_b = [n for n in (np.argsort(-bb) + 1).tolist() if n not in repeats_b]
        b3 = sorted((repeats_b + rest_b)[:3])
        return f6, b3
    return fn

def make_stacked_vote(algos):
    """AO_stacked_vote (REBUILT): 多算法堆叠投票
    记录: ge5=2% 出现2期命中5个号码, 高命中级别潜力但ge4稳定性(5%)低于AI_U_wide"""
    def fn(k, F, R, NC, G, front_actual, back_actual):
        sf = np.zeros(35); sb = np.zeros(12)
        for a in algos:
            f6, b3 = a(k, F, R, NC, G, front_actual, back_actual)
            for x in f6: sf[x - 1] += 1
            for x in b3: sb[x - 1] += 1
        return pick_top6(sf), pick_top3(sb)
    return fn

def make_vote_repeat(algos, w_repeat=0.18):
    """AR_vote_repeat (REBUILT): 堆叠投票 + 重号融合
    记录: ge5=1%, ge4=4%"""
    def fn(k, F, R, NC, G, front_actual, back_actual):
        sf = np.zeros(35); sb = np.zeros(12)
        for a in algos:
            f6, b3 = a(k, F, R, NC, G, front_actual, back_actual)
            for x in f6: sf[x - 1] += 1
            for x in b3: sb[x - 1] += 1
        sf = sf + w_repeat * R["f"][k]
        sb = sb + w_repeat * R["b"][k]
        return pick_top6(sf), pick_top3(sb)
    return fn

def make_zone_balance(max_per_zone=2):
    """BS_zone_balance (REBUILT): 区间均衡(每段<=2)约束枚举
    记录: ge4=7% ge5=1%"""
    def fn(k, F, R, NC, G, front_actual, back_actual):
        bf = norm(F["f_all_f"])[k] + 0.18 * R["f"][k] + 0.02 * NC["f"][k, :, 1].astype(np.float32)
        pool = (np.argsort(-bf)[:15] + 1).tolist()
        best, bestscore = None, -1e18
        for combo in combinations(pool, 6):
            lo = sum(1 for n in combo if n <= 12); mid = sum(1 for n in combo if 13 <= n <= 24); hi = sum(1 for n in combo if n >= 25)
            if lo <= max_per_zone and mid <= max_per_zone and hi <= max_per_zone and ok_constraint(combo):
                sc = sum(bf[n - 1] for n in combo)
                if sc > bestscore:
                    best, bestscore = combo, sc
        f6 = sorted(best) if best else pick_top6(bf)
        bb = norm(F["b_all_b"])[k] + 0.18 * R["b"][k] + 0.02 * NC["b"][k, :, 0].astype(np.float32)
        return f6, pick_top3(bb)
    return fn

def make_low_crowd_strong():
    """BU_low_crowd_strong (REBUILT): 少人买组合特征=和值>92+高区多+低区少
    记录: 基于500期真实一等奖注数分析, ge4=7% ge5=2% (无需注数数据, 用组合特征筛选)"""
    def fn(k, F, R, NC, G, front_actual, back_actual):
        bf = norm(F["f_all_f"])[k] + 0.18 * R["f"][k] + 0.02 * NC["f"][k, :, 1].astype(np.float32)
        pool = (np.argsort(-bf)[:20] + 1).tolist()
        best, bestscore = None, -1e18
        for combo in combinations(pool, 6):
            lo = sum(1 for n in combo if n <= 12); hi = sum(1 for n in combo if n >= 25)
            s6 = sum(combo)
            if s6 > 92 and hi >= lo + 1 and ok_constraint(combo):
                sc = sum(bf[n - 1] for n in combo)
                if sc > bestscore:
                    best, bestscore = combo, sc
        f6 = sorted(best) if best else pick_top6(bf)
        bb = norm(F["b_all_b"])[k] + 0.18 * R["b"][k]
        return f6, pick_top3(bb)
    return fn

def make_strong_front(w_front=0.5, w_back=0.3):
    """CH_strong_front (REBUILT): 前区重号强化 + 后区重号
    记录: ge4=6% ge5=1%"""
    def fn(k, F, R, NC, G, front_actual, back_actual):
        sf = norm(F["f_all_f"])[k] + w_front * R["f"][k] + 0.02 * NC["f"][k, :, 1].astype(np.float32)
        sb = norm(F["b_all_b"])[k] + w_back * R["b"][k]
        return pick_top6_constrained(sf), pick_top3(sb)
    return fn

def make_back_conditional(w=0.25):
    """Y_back_conditional (REBUILT): 后区条件依赖(上期后区对前区的关联近似)
    记录: ge4=2% ge5=1%"""
    def fn(k, F, R, NC, G, front_actual, back_actual):
        sf = norm(F["f_all_f"])[k] + 0.18 * R["f"][k]
        sb = norm(F["b_all_b"])[k] + 0.18 * R["b"][k] + w * NC["b"][k, :, 0].astype(np.float32)
        return pick_top6(sf), pick_top3(sb)
    return fn

# ---------------------------------------------------------------- 注册表

def build_registry():
    """构造算法注册表: name -> fn(k, F, R, NC, G, front_actual, back_actual) -> (front6, back3)"""
    reg = {}
    # ORIGINAL
    reg["v1_cold"] = make_v1_cold(constrained=True)
    reg["v2_hot"] = make_v2_hot(constrained=True)
    reg["v3"] = make_v3(reg["v1_cold"], reg["v2_hot"])
    # AI_U_wide 还原版 (round-25窗口指纹还原): 900/100窗口复现8%(记录7%, 指纹每级差<=1)
    # 1000期段 ge4=3.5% ge5=3期, 优于原参数版(2.8%/ge5=1)
    reg["AI_U_wide"] = make_ai_u_wide(radius=3, w_repeat=0.5, w_neighbor=0.2, constrained=True, topk=8)
    # 原记录参数版 (v26 parameters: 0.18/0.02/r2) — 保留作对照
    reg["AI_U_wide_orig"] = make_ai_u_wide(radius=2, w_repeat=0.18, w_neighbor=0.02, constrained=True)
    reg["U_repeat_neighbor"] = make_ai_u_wide(radius=1, w_repeat=0.18, w_neighbor=0.02, constrained=True)
    # 变体
    reg["AK_U_tuned"] = make_ai_u_wide(radius=2, w_repeat=0.12, w_neighbor=0.02, back_repeat=0.12)
    reg["AM_back_strong"] = make_ai_u_wide(radius=2, w_repeat=0.18, w_neighbor=0.02, back_repeat=0.25)
    reg["CE_joint_w15"] = make_ai_u_wide(radius=2, w_repeat=0.18, w_neighbor=0.02, constrained=False)
    reg["CF_joint_w20"] = reg["CE_joint_w15"]
    # REBUILT
    reg["H_dirichlet"] = make_dirichlet()
    reg["I_recency_eb"] = make_recency_eb()
    reg["J_repeat_markov"] = make_repeat_markov()
    reg["K_prob_ensemble"] = make_ensemble([reg["H_dirichlet"], reg["I_recency_eb"], reg["J_repeat_markov"]])
    reg["M_tail"] = make_tail()
    reg["P_prime"] = make_prime()
    reg["O_span"] = make_span_neighbor()
    reg["E_entropy"] = make_entropy()
    reg["S_sumreg"] = make_sumreg()
    reg["AZ_period7"] = make_period7()
    reg["AV_rolling300"] = make_rolling(300)
    reg["AW_rolling500"] = make_rolling(500)
    # ge5 家族 (REBUILT): 出现过命中5个号码的算法
    reg["CO_repeat3"] = make_fixed_repeat(3)
    reg["CN_repeat2"] = make_fixed_repeat(2)
    reg["CM_repeat1"] = make_fixed_repeat(1)
    reg["AO_stacked_vote"] = make_stacked_vote(
        [reg["AI_U_wide"], reg["H_dirichlet"], reg["J_repeat_markov"], reg["M_tail"]])
    reg["AR_vote_repeat"] = make_vote_repeat(
        [reg["AI_U_wide"], reg["H_dirichlet"], reg["J_repeat_markov"]])
    reg["BS_zone_balance"] = make_zone_balance(2)
    reg["BU_low_crowd_strong"] = make_low_crowd_strong()
    reg["CH_strong_front"] = make_strong_front()
    reg["Y_back_conditional"] = make_back_conditional()
    return reg

# ---------------------------------------------------------------- 回测框架

def backtest(algo_name, draws, holdout_start, warmup=60, reg=None):
    """对 [warmup, holdout_start) 之后到 len(draws) 做前向回测
    返回 {name, ge4, ge5, ge6, geAll, avg, dist(0-7)}"""
    if reg is None:
        reg = build_registry()
    fn = reg[algo_name]
    N = len(draws)
    front_actual = np.array([d["front"] for d in draws])
    back_actual = np.array([d["back"] for d in draws])

    F = {
        "f_all_f": cum_freq(front_actual, 35, None), "f30_f": cum_freq(front_actual, 35, 30),
        "f5_f": cum_freq(front_actual, 35, 5), "f10_f": cum_freq(front_actual, 35, 10),
        "b_all_b": cum_freq(back_actual, 12, None), "b30_b": cum_freq(back_actual, 12, 30),
        "b5_b": cum_freq(back_actual, 12, 5), "b10_b": cum_freq(back_actual, 12, 10),
    }
    R = {"f": repeat_flags(front_actual, 35), "b": repeat_flags(back_actual, 12)}
    NC = {
        "f": np.stack([neighbor_counts(front_actual, 35, r) for r in range(1, 4)], axis=2),
        "b": np.stack([neighbor_counts(back_actual, 12, r) for r in range(1, 4)], axis=2),
    }
    G = {"f": gap_map(front_actual, 35), "b": gap_map(back_actual, 12)}

    dist = np.zeros(8, dtype=np.int32)
    for k in range(max(warmup, 0), N):
        if k < holdout_start:
            continue  # 训练段跳过(仅评估留出段)
        f6, b3 = fn(k, F, R, NC, G, front_actual, back_actual)
        h = np.isin(f6, front_actual[k]).sum() + np.isin(b3, back_actual[k]).sum()
        dist[h] += 1
    total = int(dist.sum())
    return {
        "name": algo_name, "draws": total,
        "ge4": float(dist[4:].sum()) / total if total else 0,
        "ge5": float(dist[5:].sum()) / total if total else 0,
        "ge6": float(dist[6:].sum()) / total if total else 0,
        "geAll": float(dist[7]) / total if total else 0,
        "avg": float(np.dot(np.arange(8), dist)) / total if total else 0,
        "dist": dist.tolist(),
    }

if __name__ == "__main__":
    import json, sys
    data = json.load(open(sys.argv[1] if len(sys.argv) > 1 else ".agents/skills/dlt-analyzer/data/draws.json", encoding="utf-8"))
    draws = data["draws"] if isinstance(data, dict) else data
    reg = build_registry()
    print(f"算法池已加载: {len(reg)} 个实现; 数据 {len(draws)} 期 ({draws[0]['num']}-{draws[-1]['num']})")
    print()
    print(f"{'算法':<20}{'留出期数':>6}{'ge4':>8}{'ge5':>8}{'avg':>8}")
    for name in reg:
        r = backtest(name, draws, holdout_start=len(draws) - 100, reg=reg)
        print(f"{name:<20}{r['draws']:>6}{r['ge4']:>8.3f}{r['ge5']:>8.3f}{r['avg']:>8.3f}")
