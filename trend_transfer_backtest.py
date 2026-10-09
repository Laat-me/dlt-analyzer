# -*- coding: utf-8 -*-
"""预注册走势特征迁移实验（round-34）。
固定切分：校准 50:550、迁移观察 550:650、一次性留出 650:end。
只比较预先声明的五个方案，不根据留出结果继续调参。
"""
import json
import numpy as np
from math import comb

BASE = "/Users/mac/dream/dlt-analyzer"
D = json.load(open(f"{BASE}/.agents/skills/dlt-analyzer/data/draws.json"))["draws"]
T = len(D); WARM = 50
BLOCKS = {"calibration": (50, 550), "transfer": (550, 650), "holdout": (650, T)}
CONFIGS = {
    "repeat_only": (3, 0, 0),
    "overdue_only": (0, 0, 2),
    "repeat_neighbor": (3, 2, 0),
    "current_all": (3, 2, 2),
}

def omission(k, n, zone):
    key = "front" if zone == "f" else "back"
    last = [-1] * (n + 1)
    for i in range(k):
        for x in D[i][key]: last[x] = i
    return [k - 1 - last[x] if last[x] >= 0 else k for x in range(n + 1)]

def max_hit(k, cfg):
    wr, wn, wo = cfg; prev = D[k - 1]
    pf, pb = set(prev["front"]), set(prev["back"])
    nf = {x for p in pf for x in (p - 1, p + 1) if 1 <= x <= 35} - pf
    nb = {x for p in pb for x in (p - 1, p + 1) if 1 <= x <= 12} - pb
    of, ob = omission(k, 35, "f"), omission(k, 12, "b")
    sf = {n: wr * (n in pf) + wn * (n in nf) + wo * (of[n] >= 10.5) for n in range(1, 36)}
    sb = {n: wr * (n in pb) + wn * (n in nb) + wo * (ob[n] >= 9) for n in range(1, 13)}
    f = sorted(sf, key=lambda n: (-sf[n], n))[:15]
    b = sorted(sb, key=lambda n: (-sb[n], n))[:3]
    fronts = [set(f[i:i + 5]) for i in (0, 5, 10)]
    backs = [{b[0], b[1]}, {b[2], b[0]}, {b[1], b[2]}]
    af, ab = set(D[k]["front"]), set(D[k]["back"])
    return max(len(x & af) + len(y & ab) for x, y in zip(fronts, backs))

def evaluate(cfg, span):
    hits = [max_hit(k, cfg) for k in range(*span)]
    return {"ge4": sum(h >= 4 for h in hits), "periods": len(hits),
            "ge4Rate": sum(h >= 4 for h in hits) / len(hits),
            "avgMaxHit": float(np.mean(hits)), "zeroPrizeStreak": max_zero_streak(hits)}

def max_zero_streak(hits):
    best = cur = 0
    for h in hits:
        if h < 3: cur += 1; best = max(best, cur)
        else: cur = 0
    return best

out = {name: {block: evaluate(cfg, span) for block, span in BLOCKS.items()}
       for name, cfg in CONFIGS.items()}
# Matched random baseline from 300k simulations (same 15->3 front and 3->3 back structure).
rng = np.random.default_rng(7); trials = 300000; ge4 = 0
for _ in range(trials):
    f = rng.choice(35, 15, replace=False) + 1; rng.shuffle(f)
    fronts = [set(f[i:i + 5]) for i in (0, 5, 10)]
    b = rng.choice(12, 3, replace=False) + 1
    backs = [{b[0], b[1]}, {b[2], b[0]}, {b[1], b[2]}]
    af = set(rng.choice(35, 5, replace=False) + 1); ab = set(rng.choice(12, 2, replace=False) + 1)
    ge4 += max(len(x & af) + len(y & ab) for x, y in zip(fronts, backs)) >= 4
out["matchedRandom"] = {"ge4Rate": ge4 / trials, "trials": trials}
json.dump(out, open(f"{BASE}/trend_transfer_result.json", "w"), ensure_ascii=False, indent=1)
for name in CONFIGS:
    print(name, *(f"{b}={out[name][b]['ge4Rate'] * 100:.2f}%" for b in BLOCKS))
print("matchedRandom=%.2f%%" % (out["matchedRandom"]["ge4Rate"] * 100))
