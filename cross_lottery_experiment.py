# -*- coding: utf-8 -*-
"""
交叉彩票 + 原创算法实验：
  A. 双色球→大乐透交叉: SSQ红球热号映射前区 / SSQ蓝球映射后区 / SSQ上期号外重号
  B. 原创: 马尔可夫转移 / 和值跨度遗传 / 形态拟合 / 日期玄学 / 跨彩混合
每期5注5+2单式, 200期双窗口回测, 目标单注≥5码。
泄漏控制: SSQ只用开奖日期 < 当期DLT日期的数据。
"""
import json
import bisect
import numpy as np
from itertools import combinations

DLT = json.load(open("/Users/mac/dream/dlt-analyzer/.agents/skills/dlt-analyzer/data/draws.json"))["draws"]
SSQ = json.load(open("/Users/mac/dream/ssq-analyzer/data.json"))[::-1]     # 转升序
ssq_dates = [x["d"][:10] for x in SSQ]
T = len(DLT); NF, NB, NFR, NBA = 35, 12, 5, 2

F = np.zeros((T, NF)); B = np.zeros((T, NB))
for i, d in enumerate(DLT):
    for x in d["front"]: F[i, x - 1] = 1
    for x in d["back"]: B[i, x - 1] = 1
cumF = np.vstack([np.zeros((1, NF)), np.cumsum(F, 0)])
cumB = np.vstack([np.zeros((1, NB)), np.cumsum(B, 0)])

# SSQ 前缀统计
P = len(SSQ)
SR = np.zeros((P, 33)); SB = np.zeros((P, 16))
for i, s in enumerate(SSQ):
    for x in s["r"]: SR[i, x - 1] = 1
    SB[i, s["b"] - 1] = 1
cumSR = np.vstack([np.zeros((1, 33)), np.cumsum(SR, 0)])
cumSB = np.vstack([np.zeros((1, 16)), np.cumsum(SB, 0)])

def ssq_ptr(k):
    """截至DLT第k期开奖前已开的SSQ期数"""
    return bisect.bisect_left(ssq_dates, DLT[k]["date"])

# 马尔可夫转移前缀: cumTr[k][i][j] = 期号<k 中「i出现在t期且j出现在t+期」的次数
cumTrF = np.zeros((T + 1, NF, NF)); cumTrB = np.zeros((T + 1, NB, NB))
for t in range(T - 1):
    cumTrF[t + 2] = cumTrF[t + 1] + np.outer(F[t], F[t + 1])
    cumTrB[t + 2] = cumTrB[t + 1] + np.outer(B[t], B[t + 1])

def topn(score, n, rng):
    return tuple(np.argsort(-(score + 1e-12 * rng.random(score.shape)))[:n])

def ssq_red_hot(k, w):
    p = ssq_ptr(k)
    v = (cumSR[p] - cumSR[max(p - w, 0)]) / w
    out = np.zeros(NF); out[:33] = v
    return out

def ssq_blue_hot(k, w):
    p = ssq_ptr(k)
    return (cumSB[p] - cumSB[max(p - w, 0)])[:NB] / w

# ---------- 方法家族 ----------
def m_ssq_pure(k, rng):
    return [(topn(ssq_red_hot(k, w), NFR, rng), topn(ssq_blue_hot(k, w), NBA, rng))
            for w in (3, 5, 10, 20, 30)]

def m_ssq_repeat(k, rng):
    p = ssq_ptr(k)
    red = np.zeros(NF); red[:33] = SR[p - 1] if p >= 1 else 0
    blu = np.zeros(NB); blu[:NB] = SB[p - 1][:NB] if p >= 1 else 0
    dlt_hot_f = (cumF[k] - cumF[max(k - 10, 0)]) / 10
    dlt_hot_b = (cumB[k] - cumB[max(k - 10, 0)]) / 10
    out = []
    for a in (8, 4, 2, 1, 0.5):    # SSQ上期号权重渐弱
        out.append((topn(a * red + dlt_hot_f, NFR, rng), topn(a * blu + dlt_hot_b, NBA, rng)))
    return out

def m_hybrid(k, rng):
    dlt_f = (cumF[k] - cumF[max(k - 10, 0)]) / 10
    dlt_b = (cumB[k] - cumB[max(k - 10, 0)]) / 10
    sf, sb = ssq_red_hot(k, 10), ssq_blue_hot(k, 10)
    return [(topn((1 - a) * dlt_f + a * sf, NFR, rng), topn((1 - a) * dlt_b + a * sb, NBA, rng))
            for a in (0, 0.25, 0.5, 0.75, 1.0)]

def m_markov(k, rng):
    sF = cumTrF[k][np.where(F[k - 1] > 0)[0]].sum(0)
    sB = cumTrB[k][np.where(B[k - 1] > 0)[0]].sum(0)
    baseF = (cumF[k] - cumF[max(k - 10, 0)]) / 10
    baseB = (cumB[k] - cumB[max(k - 10, 0)]) / 10
    out = []
    for a in (0, 0.5, 1, 2, 4):
        out.append((topn(baseF + a * sF / max(sF.max(), 1), NFR, rng),
                    topn(baseB + a * sB / max(sB.max(), 1), NBA, rng)))
    return out

SUM_BUCKETS = [70, 90, 110, 130]
def m_sumspan(k, rng):
    """和值遗传: 上期前区和值定桶, 取历史条件众数桶, 拒绝采样生成5注"""
    prev_sum = sum(DLT[k - 1]["front"])
    pb = sum(s > prev_sum for s in SUM_BUCKETS)
    hist = {}
    for t in range(1, k):
        b = sum(s > sum(DLT[t - 1]["front"]) for s in SUM_BUCKETS)
        if b == pb:
            cur = sum(DLT[t]["front"])
            hist[cur // 10 * 10] = hist.get(cur // 10 * 10, 0) + 1
    target = max(hist, key=hist.get) if hist else 90
    out = []
    tries = 0
    while len(out) < 5 and tries < 5000:
        tries += 1
        f = tuple(sorted(rng.choice(NF, NFR, replace=False)))
        if abs(sum(x + 1 for x in f) - target) <= 5:
            out.append((f, topn(ssq_blue_hot(k, 10), NBA, rng)))
    while len(out) < 5:
        out.append((tuple(sorted(rng.choice(NF, NFR, replace=False))), tuple(sorted(rng.choice(NB, NBA, replace=False)))))
    return out

def m_form(k, rng):
    """形态拟合: 上期奇偶比+区间比的条件众数形态, 拒绝采样"""
    def form_of(nums):
        odd = sum(n % 2 for n in nums)
        z = [sum(1 <= n <= 12 for n in nums), sum(13 <= n <= 24 for n in nums), sum(n >= 25 for n in nums)]
        return (odd, tuple(z))
    prev_form = form_of(DLT[k - 1]["front"])
    hist = {}
    for t in range(1, k):
        if form_of(DLT[t - 1]["front"]) == prev_form:
            f = form_of(DLT[t]["front"]); hist[f] = hist.get(f, 0) + 1
    target = max(hist, key=hist.get) if hist else (3, (2, 2, 1))
    out = []
    tries = 0
    while len(out) < 5 and tries < 5000:
        tries += 1
        f = tuple(sorted(rng.choice(NF, NFR, replace=False)))
        if form_of([x + 1 for x in f]) == target:
            out.append((f, topn(ssq_blue_hot(k, 10), NBA, rng)))
    while len(out) < 5:
        out.append((tuple(sorted(rng.choice(NF, NFR, replace=False))), tuple(sorted(rng.choice(NB, NBA, replace=False)))))
    return out

def m_dateluck(k, rng):
    """日期玄学: 按开奖星期几+月份的历史号码命中率加权"""
    dw = DLT[k]["date"]
    # 当期日期的 weekday/month 用于统计历史同期(开奖日相同星期)的号频
    import datetime as dt
    d0 = dt.date.fromisoformat(dw)
    hitF = np.zeros(NF); hitB = np.zeros(NB); cnt = 0
    for t in range(k):
        d1 = dt.date.fromisoformat(DLT[t]["date"])
        if d1.weekday() == d0.weekday() and d1.month == d0.month:
            hitF += F[t]; hitB += B[t]; cnt += 1
    if cnt < 5:
        hitF = cumF[k] / max(k, 1); hitB = cumB[k] / max(k, 1)
    out = []
    for j in range(5):
        out.append((topn(hitF + 1e-9 * j * rng.random(NF), NFR, rng),
                    topn(hitB + 1e-9 * j * rng.random(NB), NBA, rng)))
    return out

METHODS = [("SSQ纯热号", m_ssq_pure), ("SSQ外重号", m_ssq_repeat), ("跨彩混合", m_hybrid),
           ("马尔可夫转移", m_markov), ("和值遗传", m_sumspan), ("形态拟合", m_form),
           ("日期玄学", m_dateluck)]

def run(lo, hi):
    res = {}
    for name, fn in METHODS:
        ge5 = 0; mx_all = []
        for k in range(lo, hi):
            rng = np.random.default_rng(2026 + k)
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

json.dump({"window1": r1, "window2": r2}, open("/Users/mac/dream/dlt-analyzer/cross_lottery_result.json", "w"),
          ensure_ascii=False, indent=1)
print("\nsaved -> cross_lottery_result.json")
