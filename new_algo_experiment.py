# -*- coding: utf-8 -*-
"""
新算法实验：验证「至少一次全部号码正确」能否通过正经预测方法达到。
四个对照组（最近 HOLDOUT 期留出回测，复式口径 前区6 + 后区3）：
  1. GA_combo     遗传算法（共现对+频次适应度）
  2. Pair_markov  共现对贪心（纯 numpy）
  3. MLP          神经网络（sklearn MLPClassifier，近10/30/100期频次特征）
  4. copy_prev    照抄上期号码（无偷看基线）
  5. memorize     直接输出当期真实开奖号（答案泄露对照，证明「全中」只能是作弊）
"""
import json
import numpy as np
from itertools import combinations

BASE = "/Users/mac/dream/dlt-analyzer/.agents/skills/dlt-analyzer"
DATA = json.load(open(f"{BASE}/data/draws.json"))["draws"]
HOLDOUT = 100
NF, NB = 35, 12          # 前区 1..35, 后区 1..12
PF, PB = 6, 3            # 复式口径：前区6 后区3

n_total = len(DATA)
n_train = n_total - HOLDOUT
print(f"总期数={n_total} 训练={n_train} 回测={HOLDOUT}")

# ---------- 工具 ----------
def onehot(front, back, nf=NF, nb=NB):
    f = np.zeros(nf); b = np.zeros(nb)
    for x in front: f[x - 1] += 1
    for x in back: b[x - 1] += 1
    return f, b

def score_hits(pred_front, pred_back, draw):
    return len(set(pred_front) & set(draw["front"])) + len(set(pred_back) & set(draw["back"]))

def eval_preds(preds, lo, hi):
    """preds: list of (front6, back3) 对应 DATA[lo:hi]"""
    hits = [score_hits(f, b, DATA[k]) for k, (f, b) in zip(range(lo, hi), preds)]
    hits = np.array(hits)
    return {
        "ge4_rate": round(float((hits >= 4).mean()) * 100, 2),
        "avg_hits": round(float(hits.mean()), 3),
        "full_hit_times": int((hits == 7).sum()),   # 复式口径满分 = 全中
        "hit_dist": {int(h): int((hits == h).sum()) for h in range(8)},
    }

# ---------- 前缀统计（无前视） ----------
# pairF[i,j] = 前区 i 与 j 同期出现次数（截至 k 期）；同理 pairB 后区 12x12
pairF_all = np.zeros((NF, NF)); pairB_all = np.zeros((NB, NB))
freqF_all = np.zeros(NF); freqB_all = np.zeros(NB)
for d in DATA:
    f, b = onehot(d["front"], d["back"])
    freqF_all += f; freqB_all += b
    pairF_all += np.outer(f, f); pairB_all += np.outer(b, b)

# 为了在回测每期 k 快速拿到「截至 k-1」的统计，做前缀差分太重，
# 直接在每个预测函数里用切片重算（100 期 * 小矩阵，numpy 足够快）。

def stats_upto(k):
    """返回截至第 k-1 期（不含 k）的频次与共现矩阵"""
    pairF = np.zeros((NF, NF)); pairB = np.zeros((NB, NB))
    freqF = np.zeros(NF); freqB = np.zeros(NB)
    for d in DATA[:k]:
        f, b = onehot(d["front"], d["back"])
        freqF += f; freqB += b
        pairF += np.outer(f, f); pairB += np.outer(b, b)
    return freqF, freqB, pairF, pairB

# ---------- 1. Pair_markov 共现贪心 ----------
def pair_greedy(freq, pair, pick, n):
    """从 freq 最高的种子出发，每次选与已选集合共现最强的号，直到凑够 n 个"""
    first = int(np.argmax(freq))
    chosen = [first]
    while len(chosen) < n:
        cand_score = pair[chosen].sum(axis=0)          # 与已选号的共现强度
        cand_score[chosen] = -1
        # 共现分 + 0.1*频次 作为 tie-break
        chosen.append(int(np.argmax(cand_score + 0.1 * freq / max(freq.max(), 1))))
    return sorted(x + 1 for x in chosen)

def predict_pair_markov(k):
    freqF, freqB, pairF, pairB = stats_upto(k)
    return pair_greedy(freqF, pairF, 6, PF), pair_greedy(freqB, pairB, 3, PB)

# ---------- 2. GA_combo 遗传算法 ----------
def ga_combo(freq, pair, n, pop=80, gens=40, seed=0):
    rng = np.random.default_rng(seed)
    m = len(freq)
    # 初始种群：偏置随机
    def rand_ind():
        w = freq / max(freq.sum(), 1)
        idx = rng.choice(m, size=n, replace=False, p=w)
        return np.sort(idx)
    pop_arr = np.array([rand_ind() for _ in range(pop)])
    norm_f = freq / max(freq.max(), 1)
    def fitness(ind):
        s = norm_f[ind].sum()
        for a, b in combinations(ind, 2):
            s += pair[a, b] / max(pair.max(), 1)
        return s
    fit = np.array([fitness(i) for i in pop_arr])
    for g in range(gens):
        # 锦标赛选择
        tsize = 3
        parents = []
        for _ in range(pop):
            cand = rng.integers(0, pop, tsize)
            parents.append(pop_arr[cand[np.argmax(fit[cand])]])
        parents = np.array(parents)
        # 单点交换 + 修复
        children = parents.copy()
        for i in range(0, pop - 1, 2):
            cut = rng.integers(1, n)
            c = np.concatenate([parents[i][:cut], parents[i + 1][cut:]])
            c = np.unique(c)
            while len(c) < n:                     # 去重后补足
                c = np.append(c, rng.integers(0, m))
                c = np.unique(c)
            children[i] = np.sort(c[:n])
        # 变异：换号
        for i in range(pop):
            if rng.random() < 0.2:
                j = rng.integers(0, n)
                new = rng.integers(0, m)
                while new in children[i]:
                    new = rng.integers(0, m)
                children[i][j] = new
                children[i] = np.sort(children[i])
        pop_arr = children
        fit = np.array([fitness(i) for i in pop_arr])
    best = pop_arr[np.argmax(fit)]
    return sorted(x + 1 for x in best)

def predict_ga(k, seed=0):
    freqF, freqB, pairF, pairB = stats_upto(k)
    return ga_combo(freqF, pairF, PF, seed=seed), ga_combo(freqB, pairB, PB, pop=60, gens=30, seed=seed)

# ---------- 3. MLP 神经网络 ----------
from sklearn.neural_network import MLPClassifier

def build_mlp_dataset(k_end):
    """用 DATA[:k_end] 构造 (X, yF, yB)：X=近 W 期号码 onehot 拼接，y=下一期"""
    W = 10
    X, yF, yB = [], [], []
    for k in range(max(W, 30), k_end):
        row = []
        for w in (10, 30, 100):
            ff = np.zeros(NF); bb = np.zeros(NB)
            for d in DATA[k - w:k]:
                f, b = onehot(d["front"], d["back"])
                ff += f; bb += b
            row += list(ff / w) + list(bb / w)
        X.append(row)
        f, b = onehot(DATA[k]["front"], DATA[k]["back"])
        yF.append(f); yB.append(b)
    return np.array(X), np.array(yF), np.array(yB)

_mlp_cache = {}
def predict_mlp(k, seed=0):
    key = (k // 10) * 10          # 每 10 期重训一次，省时间
    if key not in _mlp_cache:
        X, yF, yB = build_mlp_dataset(k)
        mF = MLPClassifier(hidden_layer_sizes=(64, 32), max_iter=300, random_state=0)
        mB = MLPClassifier(hidden_layer_sizes=(32,), max_iter=300, random_state=0)
        mF.fit(X, np.argmax(yF, axis=1)); mB.fit(X, np.argmax(yB, axis=1))
        _mlp_cache[key] = (mF, mB)
    mF, mB = _mlp_cache[key]
    W = 10
    row = []
    for w in (10, 30, 100):
        ff = np.zeros(NF); bb = np.zeros(NB)
        for d in DATA[k - w:k]:
            f, b = onehot(d["front"], d["back"])
            ff += f; bb += b
        row += list(ff / w) + list(bb / w)
    pf = mF.predict_proba([row])[0]
    pb = mB.predict_proba([row])[0]
    return sorted((np.argsort(-pf)[:PF] + 1).tolist()), sorted((np.argsort(-pb)[:PB] + 1).tolist())

# ---------- 4/5. copy_prev / memorize ----------
def predict_copy_prev(k):
    # 复式口径需 6+3，上期只有 5+2，补一个固定号（交集按 set 算，不影响口径）
    return sorted(DATA[k - 1]["front"] + [1])[:PF], sorted(DATA[k - 1]["back"] + [1])[:PB]

def predict_memorize(k):
    f = DATA[k]["front"]; b = DATA[k]["back"]
    return sorted(f + [f[0]])[:PF], sorted(b + [b[0]])[:PB]

# ---------- 回测 ----------
results = {}
groups = {
    "Pair_markov": predict_pair_markov,
    "GA_combo": predict_ga,
    "MLP": predict_mlp,
    "copy_prev": predict_copy_prev,
    "memorize(作弊)": predict_memorize,
}
for name, fn in groups.items():
    preds = []
    for k in range(n_train, n_total):
        preds.append(fn(k))
    results[name] = eval_preds(preds, n_train, n_total)
    print(f"[{name}] {results[name]}")

out = {
    "holdout": HOLDOUT,
    "train_size": n_train,
    "criteria": "复式口径 前区6+后区3；full_hit = 6前+3后全对开奖号",
    "groups": results,
}
json.dump(out, open("/Users/mac/dream/dlt-analyzer/new_algo_result.json", "w"),
          ensure_ascii=False, indent=2)
print("\nsaved -> /Users/mac/dream/dlt-analyzer/new_algo_result.json")
