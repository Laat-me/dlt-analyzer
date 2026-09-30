# -*- coding: utf-8 -*-
"""圆周率 × 全历史 多规则取数规律挖掘（含打乱对照）
每种取数规则：π 命中数 vs 理论期望 vs 打乱π对照 —— 三重对照判断"规律"真伪"""
import json, sys
import numpy as np
from decimal import Decimal, getcontext
from pathlib import Path

CACHE = Path('/Users/mac/dream/dlt-analyzer/pi_1m.txt')
if CACHE.exists():
    dig = CACHE.read_text().strip()
else:
    print('计算 π 100 万位（首次，约 2 分钟）…')
    getcontext().prec = 1_000_050
    a, b, t, p = Decimal(1), Decimal(1)/Decimal(2).sqrt(), Decimal(1)/4, 1
    for _ in range(20):
        an = (a+b)/2; b = (a*b).sqrt(); t = t - p*(a-an)**2; a = an; p *= 2
    pi = (a+b)**2/(4*t)
    dig = str(pi).replace('.', '')[1:1_000_001]
    CACHE.write_text(dig)
N = len(dig)
print(f'π 小数位 {N}，前缀 3.{dig[:12]}…')

# 目标：全部历史前区集合
DLT = json.load(open('/Users/mac/dream/dlt_full_history.json'))['draws']
SSQ = json.load(open('/Users/mac/dream/ssq-analyzer/data.json'))[::-1]
target = set()
for d in DLT: target.add(frozenset(d['front']))
for d in SSQ: target.add(frozenset(d['r']))
print(f'目标前区集合 {len(target)} 个')

def scan(darr, offs, k=2, mod=None, step=1):
    """darr: uint8 数字数组；offs: 5 个偏移；k: 每组位数；mod: 取模映射；step: 起始位步长
    返回命中期数与候选窗口数"""
    cols = []
    for o in offs:
        if k == 2:
            v = darr[o:N-1] * 10 + darr[o+1:N]
        elif k == 3:
            v = darr[o:N-2] * 100 + darr[o+1:N-1] * 10 + darr[o+2:N]
        cols.append(v)
    L = min(len(c) for c in cols)
    W = np.column_stack([c[:L] for c in cols])
    if mod:
        W = W % mod + 1
    ok = (W >= 1) & (W <= 35)
    mask = ok.all(axis=1)
    # 五数互不相同
    d5 = mask.copy()
    for i in range(5):
        for j in range(i+1, 5):
            d5 &= W[:, i] != W[:, j]
    idx = np.nonzero(d5)[0]
    if step > 1: idx = idx[idx % step == 0]
    hits = 0
    for i in idx:
        if frozenset(W[i].tolist()) in target:
            hits += 1
    return hits, len(idx)

# 取数规则族（名称, 偏移, 每组位数, 取模, 步长）
METHODS = [
    ('顺位两位组（基线）',   [0,2,4,6,8],    2, None, 1),
    ('跳 1 位取组',          [0,3,6,9,12],   2, None, 1),
    ('跳 2 位取组',          [0,4,8,12,16],  2, None, 1),
    ('跳 3 位取组',          [0,5,10,15,20], 2, None, 1),
    ('整块不重疊',           [0,2,4,6,8],    2, None, 10),
    ('两位组反读',           [0,2,4,6,8],    2, 'rev', 1),
    ('三位组 %35+1',         [0,3,6,9,12],   3, 35, 1),
    ('跳 1 位三位组 %35+1',  [0,4,8,12,16],  3, 35, 1),
]

def run_all(darr, tag):
    rows = []
    for name, offs, k, mod, step in METHODS:
        if mod == 'rev':
            # 反读：每对数字倒序
            cols = [darr[o+1:N] * 10 + darr[o:N-1] for o in offs]
            L = min(len(c) for c in cols)
            W = np.column_stack([c[:L] for c in cols])
            ok = (W >= 1) & (W <= 35)
            d5 = ok.all(axis=1)
            for i in range(5):
                for j in range(i+1, 5):
                    d5 &= W[:, i] != W[:, j]
            idx = np.nonzero(d5)[0]
            hits = sum(1 for i in idx if frozenset(W[i].tolist()) in target)
            rows.append((name, hits, len(idx)))
        else:
            hits, cand = scan(darr, offs, k, mod if isinstance(mod, int) else None, step)
            rows.append((name, hits, cand))
    return rows

digits = np.frombuffer(dig.encode(), dtype=np.uint8) - 48
res_pi = run_all(digits, 'π')

rng = np.random.default_rng(7)
shufs = []
for s in range(2):
    d2 = digits.copy(); rng.shuffle(d2)
    shufs.append(run_all(d2, f'打乱{s+1}'))

# 期望估算：候选窗口 × P(集合命中) ≈ cand × 120/35^5 × 3910
print(f'\n{"取数规则":<22}{"候选窗口":>10}{"π 命中":>8}{"期望":>8}{"打乱1":>7}{"打乱2":>7}')
print('-' * 64)
for (name, h, c), (_, h1, _), (_, h2, _) in zip(res_pi, shufs[0], shufs[1]):
    exp = c * (120 / 35**5) * len(target)
    flag = '  ← 超期望' if h > exp + 3 * max(exp**0.5, 1) else ''
    print(f'{name:<22}{c:>10}{h:>8}{exp:>8.1f}{h1:>7}{h2:>7}{flag}')

# 日期定位法：每期开奖日作为 π 定位偏移，取其后 10 位
print('\n=== 日期定位法（开奖日 YYYYMMDD % 100万 定位取 10 位）===')
from datetime import date
hits_d = 0
for d in DLT:
    y, m, dd = map(int, d['date'].split('-'))
    pos = (y * 10000 + m * 100 + dd) % (N - 10)
    g = [int(dig[pos + 2*k:pos + 2*k + 2]) for k in range(5)]
    if all(1 <= n <= 35 for n in g) and len(set(g)) == 5 and frozenset(g) in target:
        hits_d += 1
        print(f'  命中：{d["num"]}（{d["date"]}）π 第 {pos} 位 → {g}')
exp_d = len(DLT) * (35/99)**5 * 0.867 * (120/35**5) * len(target) / 1  # 粗略
print(f'日期定位 {len(DLT)} 次尝试，命中 {hits_d}（随机期望 ≈ {len(DLT)*(35/99)**5*0.87*len(target)*120/35**5:.2f}）')
