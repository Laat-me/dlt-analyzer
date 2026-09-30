# -*- coding: utf-8 -*-
"""二进制实验 · 深挖第二轮：
T2' 号码共现必须扣掉边际频率（热号天然更容易同现）→ 加权模拟零分布
F1  频率均匀性 χ² 检验（全量 / 前半 / 后半），多重校正
F2  分半复制：前半找出的热号，后半是否还热（排除同批数据自证）
A3  频率加权算法 walk-forward 100 期（滚动 500 期窗口取 top5）
"""
import json, math, random
from collections import Counter

d = json.load(open('/Users/mac/dream/dlt_full_history.json'))
draws = d['draws']
N = len(draws)

freq = Counter()
for dr in draws:
    for n in dr['front']:
        freq[n] += 1
expf = N * 5 / 35

print('=== F1 频率均匀性 ===')
def chi2(sub):
    c = Counter()
    for dr in sub:
        for n in dr['front']:
            c[n] += 1
    e = len(sub) * 5 / 35
    x2 = sum((c[n] - e) ** 2 / e for n in range(1, 36))
    return x2
x2_all = chi2(draws)
x2_1 = chi2(draws[: N // 2])
x2_2 = chi2(draws[N // 2:])
print(f'全量 χ²(34) = {x2_all:.1f}（α=0.05 临界 48.6，α=0.001 临界 63.9）')
print(f'前半 χ² = {x2_1:.1f}，后半 χ² = {x2_2:.1f}')
top1 = sorted(((freq[n], n) for n in range(1, 36)), reverse=True)[:6]
print('最热 6 号:', [(n, c) for c, n in top1], f'期望 {expf:.0f}')

print('\n=== F2 分半复制 ===')
def topk(sub, k=8):
    c = Counter()
    for dr in sub:
        for n in dr['front']:
            c[n] += 1
    return set(n for n, _ in c.most_common(k))
h1, h2 = topk(draws[: N // 2]), topk(draws[N // 2:])
print(f'前半热号 top8: {sorted(h1)}')
print(f'后半热号 top8: {sorted(h2)}')
print(f'交集 {len(h1 & h2)} 个（随机期望 {8 * 8 / 35:.1f} 个）')
# 后半中前半热号的平均出现率 vs 无条件
c2 = Counter()
for dr in draws[N // 2:]:
    for n in dr['front']:
        c2[n] += 1
N2 = N - N // 2
rate_hot = sum(c2[n] for n in h1) / (N2 * 5 / 35) / 8
print(f'前半热号在后半的相对频率: {rate_hot:.3f}（1.0 = 无延续性）')

print('\n=== T2\' 共现显著性（扣除边际频率，加权蒙特卡洛）===')
obs = Counter()
for dr in draws:
    s = sorted(dr['front'])
    for i in range(len(s)):
        for j in range(i + 1, len(s)):
            obs[(s[i], s[j])] += 1
# 按观察频率加权、无放回抽样（Efraimidis–Spirakis），保持边际
rnd = random.Random(7)
w = {n: freq[n] for n in range(1, 36)}
sim = Counter()
REP = 40000
for _ in range(REP):
    keys = sorted(((rnd.random() ** (1 / w[n]), n) for n in range(1, 36)), reverse=True)[:5]
    s = sorted(n for _, n in keys)
    for i in range(5):
        for j in range(i + 1, 5):
            sim[(s[i], s[j])] += 1
mu = {pr: sim[pr] / REP * 1 for pr in sim}
rows = []
for pr in obs:
    m = sim.get(pr, 0) / REP
    sd = math.sqrt(max(m * (1 - m / N), 1e-9) * N)  # 近似
    z = (obs[pr] - m) / (math.sqrt(m * (1 - m / N)) + 1e-9)
    rows.append((pr, obs[pr], round(m, 1), round(z, 2)))
rows.sort(key=lambda x: -x[3])
print('扣除边际后最黏 6 对:', rows[:6])
n_sig = sum(1 for r in rows if abs(r[3]) > 3.94)
print(f'超 Bonferroni 阈值（|z|>3.94）对数: {n_sig}')

print('\n=== A3 频率加权算法 walk-forward（最近 100 期，滚动 500 期窗）===')
hitA3 = 0
for t in range(N - W if (W := 100) else 0, N):
    c = Counter()
    for dr in draws[max(0, t - 500):t]:
        for n in dr['front']:
            c[n] += 1
    pred = set(n for n, _ in c.most_common(5))
    hitA3 += len(pred & set(draws[t]['front']))
print(f'前区总命中 {hitA3}（随机期望 {W * 0.714:.1f}），均值 {hitA3 / W:.3f}/期')

c = Counter()
for dr in draws[-500:]:
    for n in dr['front']:
        c[n] += 1
print('A3 → 26111 预测前区:', sorted(n for n, _ in c.most_common(5)))
