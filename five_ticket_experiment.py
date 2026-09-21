# -*- coding: utf-8 -*-
"""
五注单式实验：每期输出 5 注 5+2 单式，目标「至少一注合计命中 ≥5 码」。
5 注由不同特征权重的配置生成（多样性优先），留出100期回测 + 前一窗口复现。
"""
import json
import numpy as np

BASE = "/Users/mac/dream/dlt-analyzer/.agents/skills/dlt-analyzer"
draws = json.load(open(f"{BASE}/data/draws.json"))["draws"]
T = len(draws); NF, NB = 35, 12

F = np.zeros((T, NF)); B = np.zeros((T, NB))
for i, d in enumerate(draws):
    for x in d["front"]: F[i, x - 1] = 1
    for x in d["back"]: B[i, x - 1] = 1
cumF = np.vstack([np.zeros((1, NF)), np.cumsum(F, 0)])
cumB = np.vstack([np.zeros((1, NB)), np.cumsum(B, 0)])

def gap_mat(X):
    Tn, N = X.shape
    g = np.zeros((Tn + 1, N)); last = np.full(N, -1)
    for k in range(Tn):
        g[k] = np.where(last < 0, k, k - 1 - last)
        last[X[k] > 0] = k
    g[Tn] = np.where(last < 0, Tn, Tn - 1 - last)
    return g / Tn
gapF, gapB = gap_mat(F), gap_mat(B)

def rep_nb(X, k, N):
    rep = X[k - 1].copy(); nb = np.zeros(N)
    for n in np.where(X[k - 1] > 0)[0]:
        for m in (n - 1, n + 1):
            if 0 <= m < N: nb[m] = 1
    nb[X[k - 1] > 0] = 0
    return rep, nb

def feat_vec(k, zone, hot_w=10, cold_w=5):
    cum, gap, X, N = (cumF, gapF, F, NF) if zone == "f" else (cumB, gapB, B, NB)
    rep, nb = rep_nb(X, k, N)
    return {"rep": rep, "nb": nb,
            "hot": (cum[k] - cum[max(k - hot_w, 0)]) / hot_w,
            "cold": 1 - np.minimum(cum[k] - cum[max(k - cold_w, 0)], 1),
            "tall": cum[k] / max(k, 1), "gap": gap[k]}

# 5 注配置（权重: rep, nb, hot, cold, tall, gap）
CONFIGS = [
    ("热号+全史",  {"hot": 1.0, "tall": 4.0}),
    ("重号+热号",  {"rep": 4.0, "nb": 4.0, "hot": 1.0}),
    ("冷号回补",   {"cold": 4.0, "gap": 2.0}),
    ("邻号+热",    {"nb": 4.0, "hot": 2.0}),
    ("均衡全特征", {"rep": 1.0, "nb": 1.0, "hot": 2.0, "cold": 1.0, "tall": 1.0, "gap": 1.0}),
]

def pick_one(k, zone, weights, n, rng):
    fv = feat_vec(k, zone)
    s = np.zeros(len(next(iter(fv.values()))))
    for key, w in weights.items():
        s = s + w * fv[key]
    s = s + 1e-9 * rng.random(s.shape)     # 随机tie-break
    return tuple(np.argsort(-s)[:n])

def five_tickets(k, seed=0):
    rng = np.random.default_rng(seed + k)
    tickets, seen = [], set()
    for name, wf in CONFIGS:
        for _ in range(8):                  # 冲突则重掷tie-break
            f = pick_one(k, "f", wf, 5, rng)
            b = pick_one(k, "b", wf, 2, rng)
            if (f, b) not in seen:
                seen.add((f, b)); break
        tickets.append((name, f, b))
    return tickets

def backtest(lo, hi):
    per_period_max, ge5_events = [], 0
    best_show = []
    for k in range(lo, hi):
        tickets = five_tickets(k)
        af = set(np.where(F[k] > 0)[0]); ab = set(np.where(B[k] > 0)[0])
        mx, detail = 0, []
        for name, f, b in tickets:
            h = len(set(f) & af) + len(set(b) & ab)
            mx = max(mx, h); detail.append((name, int(h), sorted(x+1 for x in f), sorted(x+1 for x in b)))
        per_period_max.append(mx)
        if mx >= 5:
            ge5_events += 1
            best_show.append((draws[k]["num"], detail))
    return np.array(per_period_max), ge5_events, best_show

HO_LO, HO_HI = T - 100, T
VA_LO, VA_HI = T - 200, T - 100

for label, lo, hi in [("留出 921-1020", HO_LO, HO_HI), ("复现 821-920", VA_LO, VA_HI)]:
    mx, ev, show = backtest(lo, hi)
    dist = {int(h): int((mx == h).sum()) for h in range(8)}
    print(f"[{label}] 每期5注最大命中分布: {dist}")
    print(f"  ≥5命期数: {ev} (随机期望 0.18/100期)")
    for num, det in show:
        print("  事件:", num, det)

# 下一期 5 注
print("\n下一期 5 注:")
for name, f, b in five_tickets(T, seed=7):
    print(f"  {name}: 前区 {sorted(x+1 for x in f)} + 后区 {sorted(x+1 for x in b)}")

json.dump({"criteria": "每期5注5+2单式, 目标≥1注合计命中>=5",
           "random_expectation_per_100": 0.18},
          open("/Users/mac/dream/dlt-analyzer/five_ticket_result.json", "w"),
          ensure_ascii=False, indent=1)
print("\nsaved -> five_ticket_result.json")
