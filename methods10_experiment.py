# -*- coding: utf-8 -*-
"""
十流派 5 注单式大比拼：每期 5 注 5+2，目标「至少一注合计命中 ≥5 码」。
流派: 随机基线 / 热号多窗 / 冷号gap / 重号邻号系 / 旋转覆盖 / MLP神经网络 /
      遗传算法池 / 共现贪心 / 条件策略 / 纯频次多窗。
回测 200 期 (留出921-1020 + 复现821-920)，与随机期望对比。
"""
import json
import numpy as np

BASE = "/Users/mac/dream/dlt-analyzer/.agents/skills/dlt-analyzer"
draws = json.load(open(f"{BASE}/data/draws.json"))["draws"]
T = len(draws); NF, NB, NFR, NBA = 35, 12, 5, 2

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

def feats(k, zone, hot_w=10, cold_w=5):
    cum, gap, X, N = (cumF, gapF, F, NF) if zone == "f" else (cumB, gapB, B, NB)
    rep, nb = rep_nb(X, k, N)
    return {"rep": rep, "nb": nb,
            "hot": (cum[k] - cum[max(k - hot_w, 0)]) / hot_w,
            "cold": 1 - np.minimum(cum[k] - cum[max(k - cold_w, 0)], 1),
            "tall": cum[k] / max(k, 1), "gap": gap[k]}

def topn(score, n):
    return tuple(np.argsort(-(score + 1e-12 * np.random.random(score.shape)))[:n])

# ---------- 各流派: 返回 5 注 [(front5, back2), ...] ----------
def m_rand(k, rng):
    return [(tuple(sorted(rng.choice(NF, 5, replace=False))), tuple(sorted(rng.choice(NB, 2, replace=False)))) for _ in range(5)]

def m_hot_windows(k, rng):
    out = []
    for w in (3, 5, 10, 20, 30):
        ff = feats(k, "f", hot_w=w); fb = feats(k, "b", hot_w=w)
        out.append((topn(ff["hot"], NFR), topn(fb["hot"], NBA)))
    return out

def m_cold_gap(k, rng):
    ff, fb = feats(k, "f"), feats(k, "b")
    out = []
    for jitter in range(5):
        s = ff["gap"] * 4 + ff["cold"] + 1e-9 * rng.random(NF) * (jitter + 1)
        sb = fb["gap"] * 4 + fb["cold"] + 1e-9 * rng.random(NB) * (jitter + 1)
        out.append((topn(s, NFR), topn(sb, NBA)))
    return out

def m_rep_nb(k, rng):
    ff, fb = feats(k, "f"), feats(k, "b")
    combos = [({"rep": 4, "hot": 1}, {"rep": 4, "hot": 1}),
              ({"nb": 4, "hot": 1}, {"nb": 2, "hot": 1}),
              ({"rep": 2, "nb": 2, "hot": 2}, {"rep": 2, "hot": 2}),
              ({"rep": 1, "nb": 1, "hot": 4}, {"hot": 4}),
              ({"rep": 4, "nb": 4, "hot": 1}, {"rep": 1, "nb": 1})]
    out = []
    for wf, wb in combos:
        sf = sum(w * ff[x] for x, w in wf.items()); sb = sum(w * fb[x] for x, w in wb.items())
        out.append((topn(sf, NFR), topn(sb, NBA)))
    return out

def m_rotation(k, rng):
    """旋转覆盖: 前区按热号排名蛇形分5组, 每组5个; 后区同理分5组2个"""
    ff, fb = feats(k, "f"), feats(k, "b")
    order_f = list(np.argsort(-(ff["hot"] + ff["tall"])))
    order_b = list(np.argsort(-(fb["hot"] + fb["tall"])))
    front = [[] for _ in range(5)]
    for i, n in enumerate(order_f):
        front[i % 5 if (i // 5) % 2 == 0 else 4 - i % 5].append(n)   # 蛇形
    back = [[] for _ in range(5)]
    for i, n in enumerate(order_b):
        back[i % 5 if (i // 2) % 2 == 0 else 4 - i % 5].append(n)
    return [(tuple(sorted(g))[:NFR], tuple(sorted(b))[:NBA]) for g, b in zip(front, back)]

_mlp_cache = {}
def m_mlp(k, rng):
    key = k // 20
    if key not in _mlp_cache:
        from sklearn.neural_network import MLPClassifier
        W = 10
        def build(k_end):
            X, yF, yB = [], [], []
            for kk in range(max(W, 60), k_end):
                row = []
                for w in (10, 30, 100):
                    ff = np.zeros(NF); bb = np.zeros(NB)
                    for d in draws[kk - w:kk]:
                        for x in d["front"]: ff[x - 1] += 1
                        for x in d["back"]: bb[x - 1] += 1
                    row += list(ff / w) + list(bb / w)
                X.append(row)
                f = np.zeros(NF); b = np.zeros(NB)
                for x in draws[kk]["front"]: f[x - 1] = 1
                for x in draws[kk]["back"]: b[x - 1] = 1
                yF.append(np.argmax(f)); yB.append(np.argmax(b))
            return np.array(X), np.array(yF), np.array(yB)
        X, yF, yB = build(k)
        mF = MLPClassifier((64, 32), max_iter=200, random_state=0).fit(X, yF)
        mB = MLPClassifier((32,), max_iter=200, random_state=0).fit(X, yB)
        _mlp_cache[key] = (mF, mB)
    mF, mB = _mlp_cache[key]
    W = 10; row = []
    for w in (10, 30, 100):
        ff = np.zeros(NF); bb = np.zeros(NB)
        for d in draws[k - w:k]:
            for x in d["front"]: ff[x - 1] += 1
            for x in d["back"]: bb[x - 1] += 1
        row += list(ff / w) + list(bb / w)
    pf, pb = mF.predict_proba([row])[0], mB.predict_proba([row])[0]
    pf_full = np.zeros(NF); pf_full[mF.classes_] = pf     # 补全未见类别
    pb_full = np.zeros(NB); pb_full[mB.classes_] = pb
    out = [(tuple(sorted(np.argsort(-pf_full)[:NFR])), tuple(sorted(np.argsort(-pb_full)[:NBA])))]
    for _ in range(4):   # 概率扰动采样
        ef = pf_full * rng.random(NF); eb = pb_full * rng.random(NB)
        out.append((tuple(sorted(np.argsort(-ef)[:NFR])), tuple(sorted(np.argsort(-eb)[:NBA]))))
    return out

def m_ga(k, rng):
    """GA 演化 5 注池: 适应度=池内共现+频次, 每期独立演化"""
    def evolve(X, cum, n_pool, n_pick, seed):
        r = np.random.default_rng(seed); N = X.shape[1]
        norm = cum[k] / max(cum[k].sum(), 1)
        P = np.array([np.sort(r.choice(N, n_pick, replace=False, p=norm)) for _ in range(n_pool)])
        def fit(ticket):
            s = norm[ticket].sum()
            for a, b in combinations(ticket, 2):
                s += cum_pair[k][a, b] / pcmax
            return s
        for g in range(12):
            f = np.array([fit(p) for p in P])
            t = r.integers(0, n_pool, (n_pool, 3))
            P = P[t[np.arange(n_pool), np.argmax(f[t], 1)]]
            for i in range(n_pool):
                if r.random() < 0.25:
                    j = r.integers(0, n_pick); nv = r.integers(0, N)
                    while nv in P[i]: nv = r.integers(0, N)
                    P[i][j] = nv; P[i] = np.sort(P[i])
        return [tuple(sorted(p)) for p in P]
    return list(zip(evolve(F, cumF, 5, NFR, k), evolve(B, cumB, 5, NBA, k)))

from itertools import combinations
def _pair_cum():
    pcF = np.zeros((T + 1, NF, NF)); pcB = np.zeros((T + 1, NB, NB))
    for k in range(T):
        pcF[k + 1] = pcF[k] + np.outer(F[k], F[k])
        pcB[k + 1] = pcB[k] + np.outer(B[k], B[k])
    return pcF, pcB
cum_pairF, cum_pairB = _pair_cum()
cum_pair, pcmax = None, 1.0

def m_pair(k, rng):
    """共现贪心 5 变体: 不同种子/起点"""
    def greedy(cum, pc, n_pick, N, seeds):
        outs = []
        for sd in seeds:
            r = np.random.default_rng(sd)
            norm = cum[k] / max(cum[k].max(), 1)
            first = int(np.argmax(norm + 1e-9 * r.random(N)))
            ch = [first]
            while len(ch) < n_pick:
                sc = pc[k][ch].sum(0) + 0.1 * norm + 1e-9 * r.random(N)
                sc[ch] = -1
                ch.append(int(np.argmax(sc)))
            outs.append(tuple(sorted(ch)))
        return outs
    return list(zip(greedy(cumF, cum_pairF, NFR, NF, [k, k + 1, k + 2, k + 3, k + 4]),
                   greedy(cumB, cum_pairB, NBA, NB, [k, k + 1, k + 2, k + 3, k + 4])))

def m_cond(k, rng):
    """条件策略: 上期前区重号数决定本期风格"""
    prev = draws[k - 1]["front"]
    n_rep_prev = len(set(prev) & set(draws[k - 2]["front"]))
    ff, fb = feats(k, "f"), feats(k, "b")
    if n_rep_prev >= 2:
        combos = [({"rep": 4, "hot": 2}, {"rep": 4}), ({"rep": 2, "hot": 2}, {"rep": 2, "hot": 2})] * 3
    else:
        combos = [({"cold": 4, "gap": 2}, {"cold": 4}), ({"cold": 2, "hot": 2}, {"cold": 2, "hot": 2})] * 3
    combos = combos[:5]
    out = []
    for wf, wb in combos:
        sf = sum(w * ff[x] for x, w in wf.items()); sb = sum(w * fb[x] for x, w in wb.items())
        out.append((topn(sf, NFR), topn(sb, NBA)))
    return out

def m_freq(k, rng):
    """纯频次多窗"""
    out = []
    for w in (5, 15, 50, 150, 300):
        sf = (cumF[k] - cumF[max(k - w, 0)]) / w
        sb = (cumB[k] - cumB[max(k - w, 0)]) / w
        out.append((topn(sf, NFR), topn(sb, NBA)))
    return out

METHODS = [("随机基线", m_rand), ("热号多窗", m_hot_windows), ("冷号gap", m_cold_gap),
           ("重号邻号系", m_rep_nb), ("旋转覆盖", m_rotation), ("MLP神经网络", m_mlp),
           ("GA演化池", m_ga), ("共现贪心", m_pair), ("条件策略", m_cond), ("纯频次多窗", m_freq)]

def run(lo, hi, use_ga=True):
    res = {}
    for name, fn in METHODS:
        if name == "GA演化池" and not use_ga: continue
        ge5 = 0; maxhits = []; total_tickets = 0
        for k in range(lo, hi):
            rng = np.random.default_rng(1000 + k)
            if name == "GA演化池":
                global cum_pair, pcmax
                cum_pair, pcmax = cum_pairF, max(cum_pairF[k].max(), 1)
            tickets = fn(k, rng)
            af = set(np.where(F[k] > 0)[0]); ab = set(np.where(B[k] > 0)[0])
            mx = 0
            for f, b in tickets:
                mx = max(mx, len(set(f) & af) + len(set(b) & ab))
                total_tickets += 1
            maxhits.append(mx)
            ge5 += mx >= 5
        mh = np.array(maxhits)
        res[name] = {"ge5_periods": int(ge5), "avg_max_hit": round(float(mh.mean()), 2),
                     "max_ever": int(mh.max()), "n4": int((mh == 4).sum())}
        print(f"  [{name}] ≥5命期数={ge5} 场均最大命中={mh.mean():.2f} 最高单期={mh.max()} 4码期数={(mh==4).sum()}")
    return res

print("=== 复现窗口 821-920 ===")
r1 = run(T - 200, T - 100)
print("=== 留出窗口 921-1020 (含GA) ===")
r2 = run(T - 100, T)
print("=== 留出窗口 921-1020 (不含GA, 复跑稳定性) ===")
r3 = run(T - 100, T, use_ga=False)

json.dump({"window1": r1, "window2": r2, "window2_noga": r3,
           "random_expectation_ge5_per_100": 0.176},
          open("/Users/mac/dream/dlt-analyzer/methods10_result.json", "w"), ensure_ascii=False, indent=1)
print("\nsaved -> methods10_result.json")
