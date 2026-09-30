# -*- coding: utf-8 -*-
"""二进制三算法的后区版本（12 位掩码，选 2 个）：100 期 walk-forward + 26111 预测"""
import json
from collections import Counter

d = json.load(open('/Users/mac/dream/dlt_full_history.json'))
draws = d['draws']
N = len(draws)
W = 100

def mask(nums):
    v = 0
    for n in nums: v |= 1 << (n - 1)
    return v

def rotl(v, k, m):
    k %= m
    return ((v << k) | (v >> (m - k))) & ((1 << m) - 1)

pop = lambda v: bin(v).count('1')
BM = [mask(dr['back']) for dr in draws]
EXP = 2 * 2 / 12   # 后区随机期望命中 0.333/期

# A1 旋转跟随（后区，k=1..11，滚动 50 期找最热 k）
hitA1 = 0
for t in range(N - W, N):
    best_k, best_mu = 1, -1
    for k in range(1, 12):
        ovs = [pop(rotl(BM[i], k, 12) & BM[i + 1]) for i in range(t - 50, t - 1)]
        mu = sum(ovs) / len(ovs)
        if mu > best_mu: best_mu, best_k = mu, k
    hitA1 += pop(rotl(BM[t - 1], best_k, 12) & BM[t])

# A2 搭档加成（后区 66 对，滚动 500 期）
hitA2 = 0
for t in range(N - W, N):
    cnt = Counter()
    for dr in draws[max(0, t - 500):t]:
        s = sorted(dr['back'])
        if len(s) == 2:
            cnt[(s[0], s[1])] += 1
    last = set(draws[t - 1]['back'])
    sc = {n: sum(cnt.get(tuple(sorted((n, m))), 0) for m in last) for n in range(1, 13) if n not in last}
    pred = set(sorted(sc, key=lambda n: -sc[n])[:2])
    hitA2 += len(pred & set(draws[t]['back']))

# A3 频率加权（后区滚动 500 期 top2）
hitA3 = 0
for t in range(N - W, N):
    c = Counter()
    for dr in draws[max(0, t - 500):t]:
        for n in dr['back']:
            c[n] += 1
    pred = set(n for n, _ in c.most_common(2))
    hitA3 += len(pred & set(draws[t]['back']))

print(f'后区 100 期 walk-forward（随机期望 {W * EXP:.1f} 个）：')
print(f'  A1 旋转跟随: {hitA1}（{hitA1 / W:.3f}/期）')
print(f'  A2 搭档加成: {hitA2}（{hitA2 / W:.3f}/期）')
print(f'  A3 频率加权: {hitA3}（{hitA3 / W:.3f}/期）')

# 26111 后区预测
best_k, best_mu = 1, -1
for k in range(1, 12):
    ovs = [pop(rotl(BM[i], k, 12) & BM[i + 1]) for i in range(N - 51, N - 1)]
    mu = sum(ovs) / len(ovs)
    if mu > best_mu: best_mu, best_k = mu, k
b1 = sorted(n for n in range(1, 13) if rotl(BM[-1], best_k, 12) >> (n - 1) & 1)
cnt = Counter()
for dr in draws[-500:]:
    s = sorted(dr['back'])
    cnt[(s[0], s[1])] += 1
last = set(draws[-1]['back'])
sc = {n: sum(cnt.get(tuple(sorted((n, m))), 0) for m in last) for n in range(1, 13) if n not in last}
b2 = sorted(sorted(sc, key=lambda n: -sc[n])[:2])
c = Counter()
for dr in draws[-500:]:
    for n in dr['back']:
        c[n] += 1
b3 = sorted(n for n, _ in c.most_common(2))
print(f'\n26111 后区预测：A1（k={best_k}）{b1}  A2 {b2}  A3 {b3}')
