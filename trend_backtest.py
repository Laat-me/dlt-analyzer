# -*- coding: utf-8 -*-
"""
走势页四规则打分 walk-forward 回测（round-33）
规则（与走势版预测页同构）：
  直落 +3（上期原号再现）、斜连 +2（上期号±1 邻号）、回补 +2（当前遗漏 ≥1.5×期望间隔），
  前区取分 top12 为候选池 → 3 注单式（轮转发牌，允许共享），后区同规则 top3 配对。
  对照变体：配额池（直落≤3 / 斜连≤4 / 回补≥2 / 散号补足）——检验「池子聚类」是否伤害命中率。
口径：5+2 单注，7 码合计命中 ≥4 为达标；指标 = max(3注) 达标期占比与平均最大命中。
诚实预期：开奖独立均匀 → 应与随机 3 注基线打平（EV 与选号无关，round-25/29 已证）。
"""
import json
import numpy as np
from itertools import combinations
from math import comb

BASE = "/Users/mac/dream/dlt-analyzer/.agents/skills/dlt-analyzer"
draws = json.load(open(f"{BASE}/data/draws.json"))["draws"]
T = len(draws)
WARM = 50
EXP_FRONT, EXP_BACK = 7, 6          # 期望间隔 35/5、12/2

def omission(draws, upto, n_max, zone="front"):
    """截至 upto-1 期，各号当前遗漏（0=上期刚开）"""
    last = [-1] * (n_max + 1)
    key = "front" if zone == "front" else "back"
    for k in range(upto):
        for x in draws[k][key]: last[x] = k
    return [upto - 1 - last[n] if last[n] >= 0 else upto for n in range(n_max + 1)]

def trend_pool(prev, omit_f, topn, quota=None):
    """走势四规则打分 → 候选池。quota=None 用原始 top-n（页面现行做法）"""
    pf, pb = set(prev["front"]), set(prev["back"])
    nei = {n for p in pf if (n := p - 1) >= 1} | {n for p in pf if (n := p + 1) <= 35}
    nei -= pf
    scored = {}
    for n in range(1, 36):
        s = 0
        if n in pf: s += 3
        elif n in nei: s += 2
        if omit_f[n] >= 1.5 * EXP_FRONT: s += 2
        scored[n] = s
    order = sorted(scored, key=lambda n: (-scored[n], n))
    if quota:
        pool, used = [], {"zl": 0, "xl": 0, "hb": 0}
        for n in order:
            cat = "zl" if n in pf else ("xl" if n in nei else ("hb" if scored[n] >= 2 and n not in pf and n not in nei else "san"))
            lim = {"zl": 3, "xl": 4, "hb": None}.get(cat)
            if cat == "hb" and omit_f[n] < 1.5 * EXP_FRONT: cat = "san"
            if cat == "zl" and used["zl"] >= 3: continue
            if cat == "xl" and used["xl"] >= 4: continue
            pool.append(n)
            if cat in used: used[cat] += 1
            if len(pool) == topn: break
        while len(pool) < topn:
            for n in order:
                if n not in pool: pool.append(n); break
    else:
        pool = order[:topn]
    return pool, scored

def build_tickets(pool_f, pool_b, mode="orig"):
    """orig: 12 号池轮转发牌（3 注共享 3 号）；wide15: 15 号池三注完全不重号"""
    if mode == "wide15":
        tf = [tuple(sorted(pool_f[i:i+5])) for i in (0, 5, 10)]
    else:
        order = [pool_f[i] for i in range(len(pool_f))]
        slots = [[0, 1, 3, 6, 9], [2, 4, 7, 10, 1], [5, 8, 11, 3, 2]]
        tf = [tuple(sorted(order[i] for i in sl)) for sl in slots]
    tb = [tuple(sorted((pool_b[0], pool_b[1]))), tuple(sorted((pool_b[2], pool_b[0]))), tuple(sorted((pool_b[1], pool_b[2])))]
    return tf, tb

def hits(tickets_f, tickets_b, act_f, act_b):
    out = []
    for f, b in zip(tickets_f, tickets_b):
        out.append(len(set(f) & act_f) + len(set(b) & act_b))
    return out

def run(mode):
    best_hist, ge4 = [], 0
    topn = 15 if mode == "wide15" else 12
    for k in range(WARM, T):
        omit_f = omission(draws, k, 35)
        pool_f, _ = trend_pool(draws[k - 1], omit_f, topn, quota=(mode == "quota"))
        # 后区同规则
        prev_b = set(draws[k - 1]["back"])
        bnei = {n for p in prev_b if (n := p - 1) >= 1} | {n for p in prev_b if (n := p + 1) <= 12}
        bnei -= prev_b
        omit_b = omission(draws, k, 12, zone="back")
        sb = []
        for n in range(1, 13):
            s = 0
            if n in prev_b: s += 3
            elif n in bnei: s += 2
            if omit_b[n] >= 1.5 * EXP_BACK: s += 2
            sb.append((-s, n))
        sb.sort()
        pool_b = [n for _, n in sb[:3]]
        tf, tb = build_tickets(pool_f, pool_b, mode=mode)
        hs = hits(tf, tb, set(draws[k]["front"]), set(draws[k]["back"]))
        best_hist.append(max(hs))
        ge4 += max(hs) >= 4
    return ge4, np.mean(best_hist), len(best_hist)

# 匹配结构基线：前区 15 个不重号切成三注，后区固定 3 个池组成三对。
# 这比“3 注完全独立随机票”更公平，因为 wide15 的优势只允许来自选号规则，
# 不把不重号覆盖结构本身误算成走势预测力。
rng = np.random.default_rng(7)
trials = 300000
cnt = 0
for _ in range(trials):
    front = rng.choice(35, 15, replace=False) + 1
    rng.shuffle(front)
    picks = [set(front[i:i+5]) for i in (0, 5, 10)]
    back = rng.choice(12, 3, replace=False) + 1
    backs = [{back[0], back[1]}, {back[2], back[0]}, {back[1], back[2]}]
    af = set(rng.choice(35, 5, replace=False) + 1)
    ab = set(rng.choice(12, 2, replace=False) + 1)
    best = max(len(p & af) + len(b & ab) for p, b in zip(picks, backs))
    cnt += best >= 4
mc_structured = cnt / trials

# 单注精确基线仅用于参考；最终比较 wide15 使用上面的同结构 Monte Carlo。
C355, C122 = comb(35, 5), comb(12, 2)
p_ge4 = sum(comb(5, f) * comb(30, 5 - f) / C355 * comb(2, b) * comb(10, 2 - b) / C122
            for f in range(6) for b in range(3) if f + b >= 4)

res = {}
for mode in ("orig", "quota", "wide15"):
    ge4, avg, n = run(mode)
    res[mode] = {"ge4_rate": ge4 / n, "avg_best": round(avg, 3), "periods": n}
    print(f"[{mode}] 达标率 {ge4}/{n} = {ge4/n*100:.2f}% ｜ 平均最大命中 {avg:.2f}")

print(f"[随机结构基线] 前区15号不重号+后区3池三对，MC({trials}) = {mc_structured*100:.3f}%")
json.dump({"trend_orig": res["orig"], "trend_quota": res["quota"], "trend_wide15": res["wide15"],
           "random": {"single_ge4": p_ge4, "max3_indep": 1 - (1 - p_ge4) ** 3,
                      "mc_structured": mc_structured, "trials": trials},
           "note": "走势四规则（直落/斜连/回补/跨度带打分）walk-forward，5+2 单注 max(3注)≥4 口径；wide15=15号池三注不重号；最终与同结构随机基线比较"},
          open("/Users/mac/dream/dlt-analyzer/trend_backtest_result.json", "w"), ensure_ascii=False, indent=1)
print("saved -> trend_backtest_result.json")
