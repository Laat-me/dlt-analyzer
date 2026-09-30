# -*- coding: utf-8 -*-
"""在圆周率小数位中检索历史开奖号码（大乐透 2929 期 + 双色球 1002 期）
匹配规则：从某位起连续 5 个两位组全部落在 01~35 且不重复，组成的集合恰好等于某期前区；
         若紧接的 2 个两位组落在 01~12 且等于同期后区，则算 5+2 全对上。"""
import json, math
from decimal import Decimal, getcontext

import sys
DIGITS = int(sys.argv[1]) if len(sys.argv) > 1 else 100_000
getcontext().prec = DIGITS + 50

def pi_digits(n):
    """Gauss-Legendre，二次收敛，~17 次迭代得 10 万位"""
    a = Decimal(1)
    b = Decimal(1) / Decimal(2).sqrt()
    t = Decimal(1) / 4
    p = 1
    for _ in range(20):
        an = (a + b) / 2
        b = (a * b).sqrt()
        t = t - p * (a - an) ** 2
        a = an
        p *= 2
    pi = (a + b) ** 2 / (4 * t)
    s = str(pi).replace('.', '')
    return s[1:n + 1]          # 去掉整数位的 3，取小数位

print(f'计算圆周率 {DIGITS//10000} 万位…')
dig = pi_digits(DIGITS)
assert dig[:15] == '141592653589793', dig[:20]
print(f'校验前缀 3.{dig[:15]}… OK')

# 历史开奖
DLT = json.load(open('/Users/mac/dream/dlt_full_history.json'))['draws']
SSQ = json.load(open('/Users/mac/dream/ssq-analyzer/data.json'))[::-1]
front_map = {}    # frozenset(front) -> [(彩种, 期号, 日期, front, back)]
for d in DLT:
    front_map.setdefault(frozenset(d['front']), []).append(('大乐透', d['num'], d['date'], d['front'], d['back']))
for d in SSQ:
    front_map.setdefault(frozenset(d['r']), []).append(('双色球', d['c'], d['d'][:10], d['r'], [d['b']]))
print(f'目标前区集合 {len(front_map)} 个')

hits, full = [], []
scanned = 0
for i in range(0, DIGITS - 14):
    g = [int(dig[i + 2*k:i + 2*k + 2]) for k in range(5)]
    if any(n < 1 or n > 35 for n in g) or len(set(g)) < 5:
        continue
    scanned += 1
    key = frozenset(g)
    if key in front_map:
        bg = [int(dig[i + 10:i + 12]), int(dig[i + 12:i + 14])]
        for game, num, date, front, back in front_map[key]:
            hits.append((i + 1, game, num, date, front, back, g))
            if bg[0] in back and bg[1] in back and bg[0] != bg[1]:
                full.append((i + 1, game, num, date, front, back, g, bg))

print(f'\n有效五连窗口 {scanned} 个（≈{scanned/DIGITS*100:.2f}% 的扫描位）')
print(f'\n===== 前区对上的（共 {len(hits)} 处）=====')
for pos, game, num, date, front, back, g in hits:
    print(f'  π 第 {pos} 位起 …{dig[pos-1:pos+9]}… → {" ".join(f"{n:02d}" for n in g)} ＝ {game} {num}（{date}）开奖 {" ".join(f"{n:02d}" for n in front)} + {" ".join(f"{n:02d}" for n in back)}')
if full:
    print(f'\n===== 5+2 全对上的（{len(full)} 处）=====')
    for pos, game, num, date, front, back, g, bg in full:
        print(f'  π 第 {pos} 位：{g}+{bg} ＝ {game} {num}（{date}）')
else:
    print('\n===== 5+2 全对上的：0 处（前区对上后紧接的两组没有对上同期后区）=====')

# 期望估算
p5 = (35/99) ** 5
print(f'\n理论：单窗口五组全有效概率 {p5:.5f}，有效后恰好等于某期前区约 120/35^5 = {120/35**5:.2e}；')
print(f'10 万位 × {len(front_map)} 个目标 → 期望对上 ≈ {DIGITS * p5 * (120/35**5) * len(front_map):.1f} 处')
