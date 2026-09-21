# -*- coding: utf-8 -*-
"""
移植 KittenCN 技巧实验：
  技巧1 位置级softmax: 估计 P(排序位置p = 号码n) 用历史频率(替他 repo 里 LSTM 的活)
  技巧2 贪心去重采样: 已选号码概率置0再选, 保证每注唯一; 多注用温度采样+跨注去重
对照: 我们现有 top-N 打分法 / methods10 的十流派结果
每期5注5+2, 200期双窗口, 指标: ≥5命期数 / 场均最大命中 / 4码期数
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

# 位置级前缀统计: cumPosF[k][p][n] = 期号<k 中前区排序位置p出现号码n的次数
cumPosF = np.zeros((T + 1, NFR, NF)); cumPosB = np.zeros((T + 1, NBA, NB))
for t in range(T):
    cumPosF[t + 1] = cumPosF[t]; cumPosB[t + 1] = cumPosB[t]
    for p, x in enumerate(draws[t]["front"]): cumPosF[t + 1, p, x - 1] += 1
    for p, x in enumerate(draws[t]["back"]): cumPosB[t + 1, p, x - 1] += 1

def pos_probs(k, zone, window=None):
    """KittenCN式位置概率: (n_pos, n_num), 可用近window期或全部历史"""
    cum, N, npos = (cumPosF, NF, NFR) if zone == "f" else (cumPosB, NB, NBA)
    if window:
        lo = max(k - window, 0)
        cnt = cum[k] - cum[lo]
    else:
        cnt = cum[k]
    p = cnt / np.maximum(cnt.sum(1, keepdims=True), 1)
    return p

def hot_score(k, zone, w=10):
    cum, N = (cumF, NF) if zone == "f" else (cumB, NB)
    return (cum[k] - cum[max(k - w, 0)]) / w

def gen_ticket(pos_p, temp, rng, blend=None, blend_w=0.0):
    """位置级采样+贪心去重: 逐位置按softmax(位置logits)采样, 已选置0"""
    npos, N = pos_p.shape
    logits = np.log(np.maximum(pos_p, 1e-12))
    if blend is not None:
        logits = (1 - blend_w) * logits + blend_w * blend      # blend已是log空间分数
    chosen = np.zeros(N, dtype=bool)
    ticket = []
    for p in range(npos):
        z = logits[p] / max(temp, 1e-6)
        z[chosen] = -1e12                     # 贪心去重: 已选号排除
        z = z - z.max()
        pr = np.exp(z); pr /= pr.sum()
        pick = rng.choice(N, p=pr)
        chosen[pick] = True
        ticket.append(pick)
    return tuple(sorted(ticket))

def m_kc_pure(k, rng):
    """纯位置softmax: 1注argmax(去重) + 4注温度采样"""
    pf = np.log(np.maximum(pos_probs(k, "f"), 1e-12))
    pb = np.log(np.maximum(pos_probs(k, "b"), 1e-12))
    tickets = [gen_ticket(pos_probs(k, "f"), 0.3, rng), ]
    # argmax去重注(temp→0近似)
    t1f = gen_ticket(pos_probs(k, "f"), 0.05, rng); t1b = gen_ticket(pos_probs(k, "b"), 0.05, rng)
    out = [(t1f, t1b)]
    for temp in (0.5, 0.8, 1.2, 1.8):
        out.append((gen_ticket(pos_probs(k, "f"), temp, rng), gen_ticket(pos_probs(k, "b"), temp, rng)))
    return out[:5]

def m_kc_window(k, rng):
    """近100期位置概率(替他的窗口概念)"""
    out = [(gen_ticket(pos_probs(k, "f", 100), 0.05, rng), gen_ticket(pos_probs(k, "b", 100), 0.05, rng))]
    for temp in (0.5, 0.8, 1.2, 1.8):
        out.append((gen_ticket(pos_probs(k, "f", 100), temp, rng), gen_ticket(pos_probs(k, "b", 100), temp, rng)))
    return out

def m_kc_hot_blend(k, rng):
    """位置softmax + 热号logit 混合(KC技巧 × 我们的特征)"""
    blend_f = np.log(np.maximum(hot_score(k, "f"), 1e-9))
    blend_b = np.log(np.maximum(hot_score(k, "b"), 1e-9))
    blend_f = blend_f - blend_f.mean(); blend_b = blend_b - blend_b.mean()
    out = []
    for w, temp in ((0.3, 0.05), (0.3, 0.5), (0.5, 0.5), (0.7, 0.8), (0.5, 1.5)):
        bf = (1 - w) * np.log(np.maximum(pos_probs(k, "f"), 1e-12)) + w * blend_f
        bb = (1 - w) * np.log(np.maximum(pos_probs(k, "b"), 1e-12)) + w * blend_b
        bf = bf - bf.mean(1, keepdims=True); bb = bb - bb.mean(1, keepdims=True)
        out.append((gen_ticket(np.exp(bf) / np.exp(bf).sum(1, keepdims=True), temp, rng),
                    gen_ticket(np.exp(bb) / np.exp(bb).sum(1, keepdims=True), temp, rng)))
    return out

def topn(score, n, rng):
    return tuple(np.argsort(-(score + 1e-12 * rng.random(score.shape)))[:n])

def m_ours_topn(k, rng):
    """我们的现行 top-N 打分法(热号+全史)作同场对照"""
    out = []
    for w in (3, 5, 10, 20, 30):
        out.append((topn(hot_score(k, "f", w), NFR, rng), topn(hot_score(k, "b", w), NBA, rng)))
    return out

METHODS = [("KC位置softmax", m_kc_pure), ("KC位置softmax_100窗", m_kc_window),
           ("KC位置x热号混合", m_kc_hot_blend), ("我方topN对照", m_ours_topn)]

def run(lo, hi):
    res = {}
    for name, fn in METHODS:
        ge5 = 0; mx_all = []
        for k in range(lo, hi):
            rng = np.random.default_rng(77 + k)
            tickets = fn(k, rng)
            af = set(np.where(F[k] > 0)[0]); ab = set(np.where(B[k] > 0)[0])
            mx = max(len(set(f) & af) + len(set(b) & ab) for f, b in tickets)
            mx_all.append(mx); ge5 += mx >= 5
        mh = np.array(mx_all)
        res[name] = {"ge5_periods": int(ge5), "avg_max_hit": round(float(mh.mean()), 2),
                     "max_ever": int(mh.max()), "n4": int((mh == 4).sum())}
        print(f"  [{name}] ≥5命期数={ge5} 场均最大命中={mh.mean():.2f} 最高={mh.max()} 4码期数={(mh==4).sum()}")
    return res

print("=== 复现窗口 821-920 ===")
r1 = run(T - 200, T - 100)
print("=== 留出窗口 921-1020 ===")
r2 = run(T - 100, T)

# 与 methods10 十流派对照(同窗口)
old = json.load(open("/Users/mac/dream/dlt-analyzer/methods10_result.json"))
print("\n对照 methods10 同窗口场均最大命中:")
for wname, wkey in (("复现窗", "window1"), ("留出窗", "window2")):
    best_old = max(old[wkey].items(), key=lambda x: x[1]["avg_max_hit"])
    best_new = max((r1 if wname == "复现窗" else r2).items(), key=lambda x: x[1]["avg_max_hit"])
    print(f"  {wname}: 旧最佳 {best_old[0]}={best_old[1]['avg_max_hit']}  新最佳 {best_new[0]}={best_new[1]['avg_max_hit']}")

json.dump({"window1": r1, "window2": r2}, open("/Users/mac/dream/dlt-analyzer/kc_port_result.json", "w"),
          ensure_ascii=False, indent=1)
print("\nsaved -> kc_port_result.json")
