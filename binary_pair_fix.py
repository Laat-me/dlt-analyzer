# -*- coding: utf-8 -*-
"""T2' 修正版：共现 z 分数（单位 bug 修复：期望换成"次数"量纲）"""
import json, math, random
from collections import Counter

d = json.load(open('/Users/mac/dream/dlt_full_history.json'))
draws = d['draws']
N = len(draws)

freq = Counter()
obs = Counter()
for dr in draws:
    s = sorted(dr['front'])
    for n in s:
        freq[n] += 1
    for i in range(len(s)):
        for j in range(i + 1, len(s)):
            obs[(s[i], s[j])] += 1

rnd = random.Random(7)
w = {n: freq[n] for n in range(1, 36)}
sim = Counter()
REP = 40000
for _ in range(REP):
    pick = sorted(sorted(((rnd.random() ** (1 / w[n]), n) for n in range(1, 36)), reverse=True)[:5])
    s = sorted(n for _, n in pick)
    for i in range(5):
        for j in range(i + 1, 5):
            sim[(s[i], s[j])] += 1

rows = []
for pr, c in obs.items():
    p_hat = sim.get(pr, 0) / REP          # 模拟中每"期"该对出现概率
    mu = p_hat * N                        # 期望次数
    sd = math.sqrt(N * p_hat * (1 - p_hat))
    if sd == 0:
        continue
    rows.append((pr, c, round(mu, 1), round((c - mu) / sd, 2)))
rows.sort(key=lambda x: -x[3])
print('扣除边际后最黏 6 对（期号对, 实际, 期望, z）:')
for r in rows[:6]:
    print('  ', r)
print('最冷 3 对:')
for r in rows[-3:]:
    print('  ', r)
n_sig = sum(1 for r in rows if abs(r[3]) > 3.94)
print(f'超 Bonferroni（|z|>3.94）对数: {n_sig}（纯随机期望 ≈0.05）')
