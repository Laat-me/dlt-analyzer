# -*- coding: utf-8 -*-
"""双色球 × 大乐透 跨彩种重号研究
配对规则：按开奖日期排序，每期与「时间上紧邻的上一期对方彩种」配对。
  - 双色球 周二/四/日，大乐透 周一/三/六 → 周日双色球 ↔ 周一大乐透 仅隔 1 天，是最紧的对。
对照：理论超几何期望 + 打乱配对零假设。
"""
import json, random, bisect
from math import comb
from collections import Counter

SSQ = json.load(open('/Users/mac/dream/ssq-analyzer/data.json'))[::-1]          # 升序 {c,d,r,b}
DLT = json.load(open('/Users/mac/dream/dlt_full_history.json'))['draws']        # 升序 {num,date,front,back}
print(f'双色球 {len(SSQ)} 期（{SSQ[0]["d"][:10]} ~ {SSQ[-1]["d"][:10]}）｜大乐透 {len(DLT)} 期（{DLT[0]["date"]} ~ {DLT[-1]["date"]}）')

ssq_dates = [x['d'][:10] for x in SSQ]
dlt_dates = [x['date'] for x in DLT]

def overlap(a, b): return len(set(a) & set(b))

# ---- 双向配对：每期找开奖日期严格早于自己的最后一期对方彩种 ----
pairs_s2l, pairs_l2s = [], []
for i, s in enumerate(SSQ):
    j = bisect.bisect_left(dlt_dates, s['d'][:10]) - 1      # 严格早于本期双色球的最近一期大乐透
    if j >= 0: pairs_s2l.append((i, j))
for j, l in enumerate(DLT):
    i = bisect.bisect_left(ssq_dates, l['date']) - 1        # 严格早于本期大乐透的最近一期双色球
    if i >= 0: pairs_l2s.append((i, j))

def dist_of(pairs, direction):
    """direction='l2s': 统计 SSQ红 ∩ 上一期DLT前区；'s2l': DLT前区 ∩ 上一期SSQ红"""
    c = Counter()
    gap = Counter()
    for i, j in pairs:
        if direction == 'l2s':
            ov = overlap(SSQ[i]['r'], DLT[j]['front'])
            dd = SSQ[i]['d'][:10]; pp = DLT[j]['date']
        else:
            ov = overlap(DLT[j]['front'], SSQ[i]['r'])
            dd = DLT[j]['date']; pp = SSQ[i]['d'][:10]
        c[ov] += 1
        from datetime import date
        y1,m1,d1 = map(int, dd.split('-')); y2,m2,d2 = map(int, pp.split('-'))
        gap[(date(y1,m1,d1) - date(y2,m2,d2)).days] += 1
    return c, gap

c_s2l, gap_s2l = dist_of(pairs_s2l, 's2l')
c_l2s, gap_l2s = dist_of(pairs_l2s, 'l2s')

# 理论分布：SSQ红6/33 ∩ DLT前5/35，n=34,35 永不中
def theo(k):
    # 把 35 格分三段：33 格中 SSQ 占 6；DLT 抽 5。P(交集=k)
    tot = 0
    for hi in range(max(0, k - 0), 6):  # 直接用数值卷积
        pass
    # 数值法：DLT5 个里有 j 个落在 1~33（超几何），其中 k 个撞上 SSQ 的 6 红
    s = 0
    for j in range(k, 6):
        p_j = comb(33, j) * comb(2, 5 - j) / comb(35, 5) if 5 - j <= 2 else 0
        p_kgj = comb(j, k) * comb(33 - j, 6 - k) / comb(33, 6) if 6 - k <= 33 - j else 0
        s += p_j * p_kgj
    return s

EXP = 6 * 5 / 35
print(f'\n理论：任意一对相邻期期望重号 {EXP:.3f} 个')
print('理论分布：', {k: round(theo(k), 4) for k in range(6)})

def report(name, c, gap, n):
    tot = sum(c.values())
    mean = sum(k * v for k, v in c.items()) / tot
    print(f'\n【{name}】{tot} 对')
    print(f'  场均重号 {mean:.3f}（理论 {EXP:.3f}）')
    print('  分布：' + '  '.join(f'{k}个={c.get(k,0)}期({c.get(k,0)/tot*100:.1f}%)' for k in range(7)))
    print('  日期间隔：' + '  '.join(f'{g}天={n2}次' for g, n2 in sorted(gap.items())))

report('DLT前区 ∩ 上一期双色球红球', c_s2l, gap_s2l, len(pairs_s2l))
report('双色球红球 ∩ 上一期大乐透前区', c_l2s, gap_l2s, len(pairs_l2s))

# ---- 零假设：打乱 SSQ 顺序重配对 ----
rnd = random.Random(7)
idx = list(range(len(SSQ))); rnd.shuffle(idx)
SSQ_s = [SSQ[i] for i in idx]
SSQ_s = sorted(SSQ_s, key=lambda x: x['d'])   # 保持日期轴、号码打乱
# 更干净的打乱：号码池不变、期序重排（日期保持原序，号码按打乱后的序列贴回去）
shuf_r = [SSQ[i]['r'] for i in idx]
c_shuf = Counter()
for j, l in enumerate(DLT):
    i = bisect.bisect_left(ssq_dates, l['date']) - 1
    if i >= 0: c_shuf[overlap(shuf_r[i], l['front'])] += 1
tot_s = sum(c_shuf.values()); mean_s = sum(k*v for k,v in c_shuf.items())/tot_s
print(f'\n【零假设：双色球号码打乱期序后】DLT前区∩上期红球 场均 {mean_s:.3f}（真实 {sum(k*v for k,v in c_s2l.items())/sum(c_s2l.values()):.3f}）')

# ---- 最近 10 个「周日双色球 → 周一大乐透」紧对（间隔 1 天）逐对明细 ----
print('\n最近 10 对相邻交叉明细（大乐透期 ← 上一期双色球）：')
shown = 0
for i, j in reversed(pairs_s2l):
    if shown >= 10: break
    ov = sorted(set(SSQ[i]['r']) & set(DLT[j]['front']))
    print(f"  {DLT[j]['num']}({DLT[j]['date'][5:]}) {' '.join(f'{x:02d}' for x in DLT[j]['front'])}  ←  {SSQ[i]['c']} {' '.join(f'{x:02d}' for x in SSQ[i]['r'])}  重号 {len(ov)} 个: {' '.join(f'{x:02d}' for x in ov)}")
    shown += 1

# ---- 今晚视角：最新双色球 与 最新大乐透 互查 ----
print(f"\n最新一期双色球 {SSQ[-1]['c']}（{SSQ[-1]['d'][:10]}）：{' '.join(f'{x:02d}' for x in SSQ[-1]['r'])} + {SSQ[-1]['b']:02d}")
print(f"最新一期大乐透 {DLT[-1]['num']}（{DLT[-1]['date']}）：{' '.join(f'{x:02d}' for x in DLT[-1]['front'])} + {' '.join(f'{x:02d}' for x in DLT[-1]['back'])}")
print(f"两期交叉重号：{sorted(set(SSQ[-1]['r']) & set(DLT[-1]['front']))}")
