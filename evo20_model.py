# -*- coding: utf-8 -*-
"""
EVO-20 —— 20元/期 大乐透预测算法（round-29, 2026-09-24）

组成：
  A. 选号预测算法（核心）：多窗口频次 + 遗漏 + 重号/邻号融合评分 →
     「评分配额 + 覆盖式发牌」生成 10 注 5+2（每期 20 元）。
     评分权重静态固定（round-25 已证明训练段调权不迁移，不做权重学习）。
  B. 结算与 EV 引擎：固定奖（三~九等）精确结算；浮动奖按用户简化口径
     一等奖 500 万 / 二等奖 20 万平价计算。派奖期固定奖三~六等+50%、七等翻倍。
  C. 精确概率引擎：枚举全部 21,425,712 种开奖，精确计算 P(单期回本) 等。

诚实基准（简化奖金口径）：
  单注固定奖 EV = 0.5459 元（精确）；
  单注浮动奖 EV = 500万/2143万 + 20×20万/2143万 = 0.4201 元；
  单注总 EV = 0.966 元 / 2元票 → 回报率 48.3%。
  任何选号算法都不改变该 EV（开奖独立均匀 + 奖金平价 → EV 与选号无关）。
  本算法的价值在于：命中分布工程（提高小奖覆盖、压回撤）+ 派奖资格 + 诚实记账。

用法：
  python3 evo20_model.py exact     # 组合精确概率统计
  python3 evo20_model.py predict   # 生成下一期 20 元推荐单 -> evo20_tickets.json
  python3 evo20_model.py verify 26110   # 用实际开奖验证已保存推荐单
"""
import json
import sys
import itertools
import numpy as np
from math import comb

BASE = "/Users/mac/dream/dlt-analyzer"
DLT_DATA = f"{BASE}/.agents/skills/dlt-analyzer/data/draws.json"
TICKETS_FILE = f"{BASE}/evo20_tickets.json"

# ---------------------------------------------------------------- 基本常量
NF, NB, KF, KB = 35, 12, 5, 2
C35_5 = 324_632
C12_2 = 66
TOTAL_COMBOS = C35_5 * C12_2          # 21,425,712
PRICE, BUDGET = 2, 20
NTICKETS = BUDGET // PRICE            # 10 注

# 奖金（用户简化口径：浮动奖平价；固定奖现行规则）
JACKPOT_1ST = 5_000_000               # 一等奖 500 万（平价假设）
PRIZE_2ND = 200_000                   # 二等奖 20 万（平价假设）
FIXED_PRIZE = {3: 10_000, 4: 3_000, 5: 300, 6: 200, 7: 100, 8: 15, 9: 5}

# ---------------------------------------------------------------- 奖级判定
def tier_of(f, b):
    """(前区命中数, 后区命中数) -> 奖级 1..9 / 0=未中奖"""
    if f == 5: return {2: 1, 1: 2, 0: 3}[b]
    if f == 4: return {2: 4, 1: 5, 0: 7}[b]
    if f == 3: return {2: 6, 1: 8, 0: 9}[b]
    if f == 2 and b == 2: return 8
    if f == 2 and b == 1: return 9
    if f == 1 and b == 2: return 9
    if f == 0 and b == 2: return 9
    return 0

COUNT_FB = np.zeros((6, 3), dtype=np.int64)
for f in range(6):
    for b in range(3):
        COUNT_FB[f, b] = comb(5, f) * comb(30, 5 - f) * comb(2, b) * comb(10, 2 - b)
assert int(COUNT_FB.sum()) == TOTAL_COMBOS

def prize_matrix(boost=None):
    """P[f,b] = 单注(前中f, 后中b)的奖金（元）。boost: {奖级: 倍数}（派奖期固定奖）"""
    P = np.zeros((6, 3))
    for f in range(6):
        for b in range(3):
            t = tier_of(f, b)
            if t == 1:   P[f, b] = JACKPOT_1ST
            elif t == 2: P[f, b] = PRIZE_2ND
            elif t >= 3:
                P[f, b] = FIXED_PRIZE[t] * (boost.get(t, 1.0) if boost else 1.0)
    return P

def single_ticket_ev(boost=None):
    """单注 EV（元/2元票）。与选号无关（均匀性）。"""
    return float((COUNT_FB * prize_matrix(boost)).sum() / TOTAL_COMBOS)

EV_NORMAL = single_ticket_ev()                       # ≈0.966
EV_PAIJIANG = single_ticket_ev(PAIJIANG_BOOST := {3: 1.5, 4: 1.5, 5: 1.5, 6: 1.5, 7: 2.0})

# ---------------------------------------------------------------- 派奖窗口
# (起始期号, 结束期号, {奖级: 倍数})；结束期号 "99999" = 进行中。
# 2026 为三~六等+50%、七等翻倍（26050 起）；买入前以体彩官网最新公告核实。
# 2021-2025 各年窗口近似按三~九等+50% 记录（仅影响历史回测，不影响当前推荐）。
PAIJIANG = [
    ("21039", "21058", {3: 1.5, 4: 1.5, 5: 1.5, 6: 1.5, 7: 1.5, 8: 1.5, 9: 1.5}),
    ("22040", "22059", {3: 1.5, 4: 1.5, 5: 1.5, 6: 1.5, 7: 1.5, 8: 1.5, 9: 1.5}),
    ("23040", "23059", {3: 1.5, 4: 1.5, 5: 1.5, 6: 1.5, 7: 1.5, 8: 1.5, 9: 1.5}),
    ("24038", "24057", {3: 1.5, 4: 1.5, 5: 1.5, 6: 1.5, 7: 1.5, 8: 1.5, 9: 1.5}),
    ("25038", "25057", {3: 1.5, 4: 1.5, 5: 1.5, 6: 1.5, 7: 1.5, 8: 1.5, 9: 1.5}),
    ("26050", "99999", PAIJIANG_BOOST),
]

def paijiang_boost(draw_num):
    for lo, hi, boost in PAIJIANG:
        if lo <= draw_num <= hi:
            return boost
    return None

# ================================================================ A. 选号预测算法
# 评分（静态权重，特征与本仓库 v1/v2 同源但融合方式独立）：
#   freq_w  近 w 期频次（多窗口热度）
#   gap     当前遗漏（均值回归：遗漏越久给越高基础分，弱权重）
#   rep     上期重号（本仓库长窗口回测口径下为噪声，给最小权重）
#   nb      上期跨期邻号 ±1（同上，最小权重）
W = {"f10": 0.30, "f30": 0.20, "f100": 0.15, "tall": 0.15, "gap": 0.10,
     "rep": 0.05, "nb": 0.05}

def score_numbers(draws, upto, n_max):
    """返回长度 n_max 的评分向量（0-based 号码索引），只用 draws[:upto]，无前视。"""
    hist = draws[:upto]
    T = len(hist)
    f10 = np.zeros(n_max); f30 = np.zeros(n_max); f100 = np.zeros(n_max)
    tall = np.zeros(n_max); gap = np.zeros(n_max)
    rep = np.zeros(n_max); nb = np.zeros(n_max)
    last_seen = np.full(n_max, -1)
    for i, d in enumerate(hist):
        nums = d["front"] if n_max == NF else d["back"]
        for x in nums:
            j = x - 1
            tall[j] += 1
            last_seen[j] = i
            if i >= T - 10: f10[j] += 1
            if i >= T - 30: f30[j] += 1
            if i >= T - 100: f100[j] += 1
    for j in range(n_max):
        gap[j] = (T - 1 - last_seen[j]) if last_seen[j] >= 0 else T
    if T >= 1:
        prev = (draws[upto - 1]["front"] if n_max == NF else draws[upto - 1]["back"])
        for x in prev:
            rep[x - 1] = 1
            for m in (x - 2, x):
                if 0 <= m < n_max and (m + 1) not in prev:
                    nb[m] = 1
    def norm(v):
        rng = v.max() - v.min()
        return (v - v.min()) / rng if rng > 0 else np.zeros_like(v) + 0.5
    return (W["f10"] * norm(f10) + W["f30"] * norm(f30) + W["f100"] * norm(f100)
            + W["tall"] * norm(tall) + W["gap"] * norm(gap)
            + W["rep"] * rep + W["nb"] * nb)

def build_portfolio(draws, upto, rng):
    """EVO-20 选号：评分排名 → 用量配额（每号保底 1 次 + 高分号加位）→
    排序后轮转发牌到 10 注（注内号码跨度大、覆盖分散，压回撤）。
    返回 [(front5, back2) * 10]，号码升序元组。"""
    sf = score_numbers(draws, upto, NF)
    sb = score_numbers(draws, upto, NB)
    # 加微小扰动使各期组合不同（评分相近的号轮换）
    order_f = np.argsort(-(sf + rng.random(NF) * 1e-6))
    order_b = np.argsort(-(sb + rng.random(NB) * 1e-6))
    multiset_f = [int(order_f[i]) + 1 for i in range(NF)]                      # 保底覆盖
    multiset_f += [int(order_f[i]) + 1 for i in range(NTICKETS * KF - NF)]     # 15 个加位给最高分
    multiset_f.sort()
    buckets_f = [[] for _ in range(NTICKETS)]
    for j, n in enumerate(multiset_f):
        buckets_f[j % NTICKETS].append(n)
    multiset_b = [int(order_b[i]) + 1 for i in range(NB)]
    multiset_b += [int(order_b[i]) + 1 for i in range(NTICKETS * KB - NB)]
    multiset_b.sort()
    buckets_b = [[] for _ in range(NTICKETS)]
    for j, n in enumerate(multiset_b):
        buckets_b[j % NTICKETS].append(n)
    tickets, seen = [], set()
    for i in range(NTICKETS):
        f5 = list(dict.fromkeys(buckets_f[i]))   # 去重保序
        b2 = list(dict.fromkeys(buckets_b[i]))
        while len(f5) < KF:                      # 桶内撞重兜底：按评分从高到低补号
            for cand in order_f:
                if int(cand) + 1 not in f5:
                    f5.append(int(cand) + 1); break
        while len(b2) < KB:
            for cand in order_b:
                if int(cand) + 1 not in b2:
                    b2.append(int(cand) + 1); break
        f5, b2 = tuple(sorted(f5)), tuple(sorted(b2))
        if (f5, b2) in seen:                     # 整注重复兜底：换入评分最高且不在注内的前区号
            for cand in order_f:
                if int(cand) + 1 not in f5:
                    f5 = tuple(sorted(f5[:-1] + (int(cand) + 1,))); break
        seen.add((f5, b2))
        tickets.append((f5, b2))
    assert len(set(tickets)) == NTICKETS
    return tickets

# ================================================================ 对照组构造
def build_random_portfolio(rng):
    return [(tuple(sorted((rng.choice(NF, KF, replace=False) + 1).tolist())),
             tuple(sorted((rng.choice(NB, KB, replace=False) + 1).tolist())))
            for _ in range(NTICKETS)]

def build_popular_portfolio(rng):
    """对照组：拥挤票（生日区+吉利号），现实中分奖风险最高的买法"""
    pool_f = [3, 6, 8, 9, 12, 18, 21, 26, 28, 5, 11, 20, 2, 15, 25]
    pool_b = [5, 6, 8, 9, 2, 11]
    return [(tuple(sorted(rng.choice(pool_f, KF, replace=False).tolist())),
             tuple(sorted(rng.choice(pool_b, KB, replace=False).tolist())))
            for _ in range(NTICKETS)]

def build_same_portfolio(rng):
    """对照组：10 注完全相同（最大方差）"""
    t = (tuple(sorted((rng.choice(NF, KF, replace=False) + 1).tolist())),
         tuple(sorted((rng.choice(NB, KB, replace=False) + 1).tolist())))
    return [t] * NTICKETS

# ================================================================ B/C. 结算与精确概率
def settle_draw(draw, tickets, boost=None):
    """对真实开奖结算组合，返回 (固定奖合计, 浮动奖合计, 命中事件列表)。"""
    af, ab = set(draw["front"]), set(draw["back"])
    fixed = floating = 0.0
    events = []
    for f5, b2 in tickets:
        t = tier_of(len(af & set(f5)), len(ab & set(b2)))
        if t == 0: continue
        if t == 1:   amt, is_f = JACKPOT_1ST, True
        elif t == 2: amt, is_f = PRIZE_2ND, True
        else:
            amt, is_f = FIXED_PRIZE[t] * (boost.get(t, 1.0) if boost else 1.0), False
        if is_f: floating += amt
        else:    fixed += amt
        events.append({"tier": t, "amount": amt})
    return fixed, floating, events

def _masks(values, n):
    combos = np.array(list(itertools.combinations(range(1, n + 1), 5 if n == NF else 2)),
                      dtype=np.int64)
    masks = np.zeros(len(combos), dtype=np.int64)
    for j in range(combos.shape[1]):
        masks |= (1 << combos[:, j])
    return masks

_FRONT_MASKS = _masks(None, NF)
_BACK_MASKS = _masks(None, NB)
_HITS_CACHE = {}

def _ticket_hits(ti):
    if ti not in _HITS_CACHE:
        fm = sum(1 << (x - 1) for x in ti[0])
        bm = sum(1 << (x - 1) for x in ti[1])
        _HITS_CACHE[ti] = (np.bitwise_count(_FRONT_MASKS & fm).astype(np.int8),
                           np.bitwise_count(_BACK_MASKS & bm).astype(np.int8))
    return _HITS_CACHE[ti]

def exact_portfolio_stats(tickets, boost=None, B=BUDGET):
    """枚举 21,425,712 种开奖，返回组合奖金精确统计（含简化浮动奖口径）。"""
    P = prize_matrix(boost)
    total = np.zeros((C35_5, C12_2), dtype=np.float32)
    for ti in tickets:
        hF, hB = _ticket_hits(ti)
        total += P[np.ix_(hF.astype(np.int64), hB.astype(np.int64))]
    return {
        "ev_per_period": round(float(total.mean()), 3),
        "p_net_positive": round(float((total > B).mean()), 6),   # 单期净盈利概率
        "p_break_even": round(float((total >= B).mean()), 6),
        "p_zero": round(float((total == 0).mean()), 6),
        "p_ge100": round(float((total >= 100).mean()), 6),
        "p_ge300": round(float((total >= 300).mean()), 6),
        "prize_dist": {f"{a}~{b}": int(((total >= a) & (total < b)).sum())
                       for a, b in [(0, 5), (5, 15), (15, 100), (100, 300),
                                    (300, 3000), (3000, 10**9)]},
    }

# ================================================================ 预测入口
def load_draws():
    return json.load(open(DLT_DATA))["draws"]

def make_prediction(target=None):
    draws = load_draws()
    nxt = target or str(int(draws[-1]["num"]) + 1)
    upto = len(draws)                       # 只用已开奖期，无前视
    rng = np.random.default_rng(int(nxt))   # 期号作种子，可复现
    tickets = build_portfolio(draws, upto, rng)
    boost = paijiang_boost(nxt)
    stats = exact_portfolio_stats(tickets, boost)
    out = {
        "model": "EVO-20",
        "targetDrawNum": nxt,
        "cost": BUDGET,
        "structure": "1张票×10注单式(5+2)=20元；单票≥18元满足派奖参与门槛",
        "paijiang": bool(boost),
        "tickets": [{"front": list(f), "back": list(b)} for f, b in tickets],
        "ev_normal_per_period": round(EV_NORMAL * NTICKETS, 2),
        "ev_this_period": round((EV_PAIJIANG if boost else EV_NORMAL) * NTICKETS, 2),
        "exact": stats,
    }
    json.dump(out, open(TICKETS_FILE, "w"), ensure_ascii=False, indent=1)
    return out

def verify(draw_num):
    """用实际开奖验证已保存的推荐单"""
    tickets_file = json.load(open(TICKETS_FILE))
    draws = {d["num"]: d for d in load_draws()}
    d = draws[draw_num]
    boost = paijiang_boost(draw_num)
    fixed, floating, events = settle_draw(d, [(t["front"], t["back"]) for t in tickets_file["tickets"]], boost)
    return {"draw": draw_num, "fixed": fixed, "floating": floating,
            "total": fixed + floating, "events": events,
            "actual": {"front": d["front"], "back": d["back"]}}

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "exact"
    print(f"单注EV（简化奖金口径）: 正常期 {EV_NORMAL:.4f} 元 | 派奖期 {EV_PAIJIANG:.4f} 元 / 2元票")
    print(f"  → 回报率 {EV_NORMAL/2*100:.1f}% / {EV_PAIJIANG/2*100:.1f}%（<100% ⇒ 长期数学期望为负）")
    if mode == "predict":
        p = make_prediction(sys.argv[2] if len(sys.argv) > 2 else None)
        print(f"\n=== {p['targetDrawNum']} 期 EVO-20 推荐单（{p['cost']}元，派奖期: {p['paijiang']}）===")
        print(f"期望回报（简化口径）: {p['ev_this_period']} 元 / {p['cost']} 元")
        print(f"精确 P(单期回本): {p['exact']['p_break_even']*100:.2f}%  P(净盈利): {p['exact']['p_net_positive']*100:.2f}%")
        for i, t in enumerate(p["tickets"], 1):
            print(f"  第{i:02d}注: 前区 {' '.join(f'{x:02d}' for x in t['front'])} + 后区 {' '.join(f'{x:02d}' for x in t['back'])}")
    elif mode == "exact":
        draws = load_draws()
        rng = np.random.default_rng(int(draws[-1]["num"]) + 1)
        tk = build_portfolio(draws, len(draws), rng)
        print("EVO-20 下一期组合精确统计:")
        print(json.dumps(exact_portfolio_stats(tk), ensure_ascii=False, indent=1))
    elif mode == "verify":
        print(json.dumps(verify(sys.argv[2]), ensure_ascii=False, indent=1))
