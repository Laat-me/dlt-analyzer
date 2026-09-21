# -*- coding: utf-8 -*-
"""
特征组合网格搜索 v2（向量化版）
特征: 重号 / 严格邻号(±1) / 热号窗口 / 冷号窗口 / 全史频次, 权重 {0,1,2,4}^5
前区 1024 组 × 后区 1024 组 = 1,048,576 组合, 各在留出100期上回测(6+3复式口径)。
对 ≥6 命配置换窗口(821-920)复现验证。
"""
import json
import numpy as np
from itertools import product

BASE = "/Users/mac/dream/dlt-analyzer/.agents/skills/dlt-analyzer"
draws = json.load(open(f"{BASE}/data/draws.json"))["draws"]
T = len(draws)
NF, NB, PF, PB = 35, 12, 6, 3

F = np.zeros((T, NF)); B = np.zeros((T, NB))
for i, d in enumerate(draws):
    for x in d["front"]: F[i, x - 1] = 1
    for x in d["back"]: B[i, x - 1] = 1
cumF = np.vstack([np.zeros((1, NF)), np.cumsum(F, 0)])
cumB = np.vstack([np.zeros((1, NB)), np.cumsum(B, 0)])

def gap_mat(X):
    Tn, N = X.shape
    g = np.zeros((Tn + 1, N))
    last = np.full(N, -1)
    for k in range(Tn):
        g[k] = np.where(last < 0, k, k - 1 - last)
        last[X[k] > 0] = k
    g[Tn] = np.where(last < 0, Tn, Tn - 1 - last)
    return g / Tn

gapF, gapB = gap_mat(F), gap_mat(B)
WINDOWS = [3, 5, 10, 20, 30, 50, 100]

def rep_nb(X, k, N):
    rep = X[k - 1].copy()
    nb = np.zeros(N)
    for n in np.where(X[k - 1] > 0)[0]:
        for m in (n - 1, n + 1):
            if 0 <= m < N: nb[m] = 1
    nb[X[k - 1] > 0] = 0
    return rep, nb

HO_LO, HO_HI = T - 100, T
VA_LO, VA_HI = T - 200, T - 100

# ---------- 阶段1: 单特征选窗口 ----------
def single(zone, lo, hi):
    cum, gap, X, n_pick = (cumF, gapF, F, PF) if zone == "f" else (cumB, gapB, B, PB)
    keys = ["rep", "nb", "tall", "gap"] + [f"hot{w}" for w in WINDOWS] + [f"cold{w}" for w in WINDOWS]
    rows = {key: [] for key in keys}
    for k in range(lo, hi):
        rep, nb = rep_nb(X, k, X.shape[1])
        base = {"rep": rep, "nb": nb, "tall": cum[k] / max(k, 1), "gap": gap[k]}
        for w in WINDOWS:
            base[f"hot{w}"] = (cum[k] - cum[max(k - w, 0)]) / w
            base[f"cold{w}"] = 1 - np.minimum(cum[k] - cum[max(k - w, 0)], 1)
        act = set(np.where(X[k] > 0)[0])
        for key in keys:
            v = base[key] + 1e-9 * np.arange(X.shape[1])
            rows[key].append(len(set(np.argsort(-v)[:n_pick]) & act))
    return {key: round(float(np.mean(v)), 3) for key, v in rows.items()}

s1f, s1b = single("f", HO_LO, HO_HI), single("b", HO_LO, HO_HI)
print("阶段1 单特征场均命中(前区):", dict(sorted(s1f.items(), key=lambda x: -x[1])[:8]))
print("阶段1 单特征场均命中(后区):", dict(sorted(s1b.items(), key=lambda x: -x[1])[:8]))
hot_w = max(WINDOWS, key=lambda w: s1f[f"hot{w}"] + s1b[f"hot{w}"])
cold_w = max(WINDOWS, key=lambda w: s1f[f"cold{w}"] + s1b[f"cold{w}"])
print(f"选定窗口 hot={hot_w} cold={cold_w}")

# ---------- 阶段2: 向量化网格 ----------
W = np.array([w for w in product([0, 1, 2, 4], repeat=5) if max(w) > 0], dtype=np.float32)  # (1023,5)
M = len(W)
eps = (((np.arange(M) * 2654435761) % 997) / 9970.0).astype(np.float32).reshape(M, 1)

def zone_hit_matrix(lo, hi, zone):
    """返回 (n_periods, M) 每期每配置命中数"""
    cum, X, n_pick, N = (cumF, F, PF, NF) if zone == "f" else (cumB, B, PB, NB)
    H = np.zeros((hi - lo, M), dtype=np.int8)
    for idx, k in enumerate(range(lo, hi)):
        rep, nb = rep_nb(X, k, N)
        feat = np.stack([rep, nb,
                         (cum[k] - cum[max(k - hot_w, 0)]) / hot_w,
                         1 - np.minimum(cum[k] - cum[max(k - cold_w, 0)], 1),
                         cum[k] / max(k, 1)])                    # (5,N)
        S = W @ feat + eps                                       # (M,N)
        pick = np.argpartition(-S, n_pick, axis=1)[:, :n_pick]   # (M,n_pick)
        act = set(np.where(X[k] > 0)[0])
        hitmask = np.isin(pick, list(act))
        H[idx] = hitmask.sum(axis=1)
    return H

print("计算前区命中矩阵...")
HF = zone_hit_matrix(HO_LO, HO_HI, "f")
print("计算后区命中矩阵...")
HB = zone_hit_matrix(HO_LO, HO_HI, "b")

ge4 = np.zeros((M, M), dtype=np.int16)
ge5 = np.zeros((M, M), dtype=np.int16)
ge6 = np.zeros((M, M), dtype=np.int16)
ge7 = np.zeros((M, M), dtype=np.int16)
for i in range(M):
    s = HF[:, i][:, None] + HB                    # (100, M)
    ge4[i] = (s >= 4).sum(0); ge5[i] = (s >= 5).sum(0)
    ge6[i] = (s >= 6).sum(0); ge7[i] = (s >= 7).sum(0)

best = []
for i in range(M):
    j = np.argmax(ge6[i] * 100 + ge7[i] * 100 + ge5[i] * 10 + ge4[i])
    best.append((int(ge6[i, j]), int(ge7[i, j]), int(ge5[i, j]), int(ge4[i, j]), i, int(j)))
best.sort(reverse=True)
print(f"\n阶段2: {M}×{M} = {M*M:,} 组组合 × 100期留出")
print("TOP10:")
for g6, g7, g5, g4, i, j in best[:10]:
    print(f"  wF={W[i].astype(int).tolist()} wB={W[j].astype(int).tolist()} ge4={g4}% ge5={g5} ge6={g6} ge7={g7}")

cand = [(i, j) for g6, g7, g5, g4, i, j in best if g6 + g7 > 0]
print(f"留出中 ≥6命 的组合数: {len(cand)}")

# ---------- 阶段3: 复现验证(821-920窗口) ----------
def pair_hits(i, j, lo, hi):
    HFn = zone_hit_matrix(lo, hi, "f")
    HBn = zone_hit_matrix(lo, hi, "b")
    s = HFn[:, i] + HBn[:, j]
    return s

repro = []
for i, j in cand[:20]:
    s = pair_hits(i, j, VA_LO, VA_HI)
    repro.append({"wF": W[i].astype(int).tolist(), "wB": W[j].astype(int).tolist(),
                  "holdout_ge6": int((HF[:, i] + HB[:, j] >= 6).sum()),
                  "valid_ge6": int((s >= 6).sum()),
                  "valid_ge4": int((s >= 4).sum()),
                  "valid_dist": np.bincount(s, minlength=8).tolist()})
    print(f"  复现 wF={W[i].astype(int).tolist()} wB={W[j].astype(int).tolist()}: 留出≥6={int((HF[:,i]+HB[:,j]>=6).sum())} → 验证窗≥6={int((s>=6).sum())}, 验证窗ge4={int((s>=4).sum())}%")

json.dump({"hot_window": hot_w, "cold_window": cold_w, "M": M,
           "top10": [{"wF": W[i].astype(int).tolist(), "wB": W[j].astype(int).tolist(),
                      "ge4": g4, "ge5": g5, "ge6": g6, "ge7": g7} for g6, g7, g5, g4, i, j in best[:10]],
           "n_ge6_pairs": len(cand), "repro": repro},
          open("/Users/mac/dream/dlt-analyzer/grid_search_result.json", "w"),
          ensure_ascii=False, indent=1)
print("\nsaved -> grid_search_result.json")
