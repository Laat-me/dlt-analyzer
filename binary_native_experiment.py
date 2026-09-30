# -*- coding: utf-8 -*-
"""大乐透二进制原生规律挖掘（全量 2928 期 + 100 期窗口对照）
T1 循环移位相关：rotl35(上期掩码, k) 与本期掩码的重合数，k=1..34 扫描
T2 号码搭档挖掘：595 对前区 + 66 对后区共现 z 分数（Bonferroni 阈值）
T3 位面频谱：6 个 bit 层置位计数序列的 lag1~10 自相关
T4 掩码结构：1 的段数（0→1 跳变）分布 vs 蒙特卡洛
A1 旋转跟随算法：滚动 50 期找最热移位 k*，预测 = rotl(上期, k*)
A2 搭档加成算法：按与上期号码的历史共现 lift 打分取 top
两者 100 期 walk-forward 回测 + 26111 预测
"""
import json, math
from collections import Counter

d = json.load(open('/Users/mac/dream/dlt_full_history.json'))
draws = d['draws']
N = len(draws)

def mask(nums):
    v = 0
    for n in nums: v |= 1 << (n - 1)
    return v

def rotl(v, k, m):
    k %= m
    return ((v << k) | (v >> (m - k))) & ((1 << m) - 1)

pop = lambda v: bin(v).count('1')

FM = [mask(dr['front']) for dr in draws]
BM = [mask(dr['back']) for dr in draws]

print(f'=== T1 循环移位相关（全量 {N} 期）===')
print('随机期望：任何 k 的重合数均值 ≈ 0.714（前区）/ 0.333（后区），se≈0.0136/0.0101')
def rot_scan(masks, m):
    out = []
    for k in range(1, m):
        ovs = [pop(rotl(masks[t], k, m) & masks[t + 1]) for t in range(len(masks) - 1)]
        mu = sum(ovs) / len(ovs)
        expd = (5 * 5 / 35) if m == 35 else (2 * 2 / 12)
        var = 5 * (5 / 35) * (30 / 35) * (30 / 34) if m == 35 else 2 * (2 / 12) * (10 / 12) * (10 / 11)
        z = (mu - expd) / math.sqrt(var / len(ovs))
        out.append((k, round(mu, 3), round(z, 2)))
    return out
rf = rot_scan(FM, 35)
rb = rot_scan(BM, 12)
top_f = sorted(rf, key=lambda x: -abs(x[2]))[:5]
top_b = sorted(rb, key=lambda x: -abs(x[2]))[:5]
print('前区 |z| 最大 5 个移位:', top_f, '（Bonferroni 阈值 |z|≈3.4）')
print('后区 |z| 最大 3 个移位:', top_b[:3], '（阈值 |z|≈3.1）')

print(f'\n=== T2 号码搭档共现（全量，前区 595 对 / 后区 66 对）===')
def pair_scan(key, m, pick):
    cnt = Counter()
    for dr in draws:
        s = sorted(dr[key])
        for i in range(len(s)):
            for j in range(i + 1, len(s)):
                cnt[(s[i], s[j])] += 1
    p = (pick / m) * ((pick - 1) / (m - 1))
    mu, sd = N * p, math.sqrt(N * p * (1 - p))
    zs = [(pr, c, (c - mu) / sd) for pr, c in cnt.items()]
    zs.sort(key=lambda x: -x[2])
    return zs, mu, sd
zf, muF, sdF = pair_scan('front', 35, 5)
zb, muB, sdB = pair_scan('back', 12, 2)
print(f'前区期望 {muF:.1f}±{sdF:.1f} 次，Bonferroni |z|>3.94 才显著')
print('  最黏 5 对:', [(p, c, round(z, 2)) for p, c, z in zf[:5]])
print('  最冷 5 对:', [(p, c, round(z, 2)) for p, c, z in zf[-5:]])
n_sig = sum(1 for _, _, z in zf if abs(z) > 3.94)
print(f'  超阈值对数: {n_sig}（纯随机期望约 0.05 对）')
print(f'后区期望 {muB:.1f}±{sdB:.1f} 次，最黏 3 对:', [(p, c, round(z, 2)) for p, c, z in zb[:3]])

print('\n=== T3 位面自相关（6 bit 层 × lag 1~10）===')
se = 2 / math.sqrt(N)
any_sig = False
for k in range(6):
    series = [sum(1 for n in dr['front'] if n >> k & 1) for dr in draws]
    mu = sum(series) / N
    var = sum((x - mu) ** 2 for x in series) / N
    hits = []
    for lag in range(1, 11):
        r = sum((series[i] - mu) * (series[i + lag] - mu) for i in range(N - lag)) / (N - lag) / var
        if abs(r) > se:
            hits.append((lag, round(r, 3)))
            any_sig = True
    print(f'  bit{k}（权 {1 << k}）显著 lag: {hits if hits else "无"}')
print('结论:', '存在显著周期' if any_sig else '所有位面所有 lag 均在 2σ 内，无周期振荡')

print('\n=== T4 掩码段数（1 的连续段）分布 vs 蒙特卡洛 ===')
def runs(v, m):
    r, prev = 0, 0
    for i in range(m):
        b = v >> i & 1
        if b and not prev: r += 1
        prev = b
    return r
actual = Counter(runs(v, 35) for v in FM)
import random
sim = Counter()
rnd = random.Random(42)
for _ in range(200000):
    s = rnd.sample(range(35), 5)
    v = 0
    for n in s: v |= 1 << n
    sim[runs(v, 35)] += 1
print('段数 | 实际占比 | 随机占比')
for k in sorted(set(actual) | set(sim)):
    print(f'  {k} 段: {actual.get(k, 0) / N * 100:5.1f}%  {sim.get(k, 0) / 2000:5.1f}%')

print('\n=== A1 旋转跟随算法 walk-forward（最近 100 期）===')
W = 100
hitA1 = 0
for t in range(N - W, N):
    best_k, best_mu = 1, -1
    for k in range(1, 35):
        ovs = [pop(rotl(FM[i], k, 35) & FM[i + 1]) for i in range(t - 50, t - 1)]
        mu = sum(ovs) / len(ovs)
        if mu > best_mu: best_mu, best_k = mu, k
    pred = rotl(FM[t - 1], best_k, 35)
    hitA1 += pop(pred & FM[t])
print(f'前区总命中 {hitA1}（随机期望 {W * 0.714:.1f}），均值 {hitA1 / W:.3f}/期')

print('\n=== A2 搭档加成算法 walk-forward（最近 100 期）===')
hitA2 = 0
for t in range(N - W, N):
    cnt = Counter()
    for dr in draws[max(0, t - 500):t]:
        s = sorted(dr['front'])
        for i in range(len(s)):
            for j in range(i + 1, len(s)):
                cnt[(s[i], s[j])] += 1
    last = set(draws[t - 1]['front'])
    sc = {}
    for n in range(1, 36):
        if n in last: continue
        sc[n] = sum(cnt.get(tuple(sorted((n, m))), 0) for m in last)
    pred = set(sorted(sc, key=lambda n: -sc[n])[:5])
    hitA2 += len(pred & set(draws[t]['front']))
print(f'前区总命中 {hitA2}（随机期望 {W * 0.714:.1f}），均值 {hitA2 / W:.3f}/期')

print('\n=== 26111 预测 ===')
best_k, best_mu = 1, -1
for k in range(1, 35):
    ovs = [pop(rotl(FM[i], k, 35) & FM[i + 1]) for i in range(N - 51, N - 1)]
    mu = sum(ovs) / len(ovs)
    if mu > best_mu: best_mu, best_k = mu, k
pred = rotl(FM[-1], best_k, 35)
frontA1 = sorted(n for n in range(1, 36) if pred >> (n - 1) & 1)
print(f'A1 旋转跟随（k={best_k}，滚动均值 {best_mu:.2f}）：前区 {frontA1}')
cnt = Counter()
for dr in draws[-500:]:
    s = sorted(dr['front'])
    for i in range(len(s)):
        for j in range(i + 1, len(s)):
            cnt[(s[i], s[j])] += 1
last = set(draws[-1]['front'])
sc = {n: sum(cnt.get(tuple(sorted((n, m))), 0) for m in last) for n in range(1, 36) if n not in last}
frontA2 = sorted(sorted(sc, key=lambda n: -sc[n])[:5])
print(f'A2 搭档加成：前区 {frontA2}')
