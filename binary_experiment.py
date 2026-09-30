# -*- coding: utf-8 -*-
"""大乐透二进制实验：
A. 位图规律检验（35 位前区掩码 + 12 位后区掩码，最近 100 期）
   A1. 每位号码的 lag-1 序列自相关（随机应 ≈ 0，±2/√100=0.2 之外显著）
   A2. 相邻期 XOR 弹位数（=10-2×重号数），与随机理论值对比
   A3. 逐位转移矩阵 P(1→1) / P(0→1)，与无条件概率对比
   A4. 号码 6 位二进制（LSB=奇偶…MSB=32）各位 1 的频率 vs 均匀理论值
B. 二进制马尔可夫算法：每位按 P(下期为1|本期状态) 打分，前区取 top5、后区取 top2
   100 期 walk-forward 回测（前 30 期起报），对照随机期望
C. 用全部数据训练，输出下一期（26111）预测
"""
import json

d = json.load(open('/Users/mac/dream/dlt_full_history.json'))
draws = d['draws']
N100 = draws[-100:]
print(f'实验窗口：{N100[0]["num"]} ~ {N100[-1]["num"]}（{len(N100)} 期）')

def mask(nums, m):
    v = 0
    for n in nums:
        v |= 1 << (n - 1)
    return v

def bits(nums, m):  # [bit_1, bit_2, ...] 0/1
    s = set(nums)
    return [1 if n in s else 0 for n in range(1, m + 1)]

F = [bits(dr['front'], 35) for dr in N100]
B = [bits(dr['back'], 12) for dr in N100]

print('\n=== A1 每位号码 lag-1 自相关（前区 35 位）===')
def lag1(series):
    n = len(series)
    mu = sum(series) / n
    var = sum((x - mu) ** 2 for x in series) / n
    if var == 0:
        return 0.0
    return sum((series[i] - mu) * (series[i + 1] - mu) for i in range(n - 1)) / (n - 1) / var

sig = []
for n in range(35):
    r = lag1([f[n] for f in F])
    if abs(r) > 0.2:
        sig.append((n + 1, round(r, 3)))
print('前区 |r|>0.2（2σ）的位：', sig if sig else '无')
sigb = [(n + 1, round(lag1([b[n] for b in B]), 3)) for n in range(12) if abs(lag1([b[n] for b in B])) > 0.2]
print('后区 |r|>0.2 的位：', sigb if sigb else '无')
rf = [lag1([f[n] for f in F]) for n in range(35)]
print(f'前区 35 位自相关均值 {sum(rf)/35:+.3f}（随机期望 0），最大 |r|={max(map(abs, rf)):.3f}')

print('\n=== A2 相邻期 XOR 弹位数 ===')
xors = []
for i in range(len(N100) - 1):
    x = mask(N100[i]['front'], 35) ^ mask(N100[i + 1]['front'], 35)
    xors.append(bin(x).count('1'))
mean_xor = sum(xors) / len(xors)
print(f'前区相邻期 XOR 弹位数：均值 {mean_xor:.2f}（随机理论 8.57，即平均每期换 4.3 个号）')
print('弹位数分布:', {k: xors.count(k) for k in sorted(set(xors))})

print('\n=== A3 逐位转移概率（前区汇总）===')
t11 = t10 = t01 = t00 = 0
for i in range(len(F) - 1):
    for n in range(35):
        a, b = F[i][n], F[i + 1][n]
        if a and b: t11 += 1
        elif a: t10 += 1
        elif b: t01 += 1
        else: t00 += 1
p11 = t11 / (t11 + t10)
p01 = t01 / (t01 + t00)
print(f'P(下期开|本期开) = {p11:.4f}   P(下期开|本期没开) = {p01:.4f}   无条件 P = {5/35:.4f}')
print('→ 两者几乎相等则位面无记忆（直落无加成）')

print('\n=== A4 号码二进制各位频率（前区 500 个开奖号）===')
# 号码 n 的 6 位二进制：bit0=LSB(奇偶) ... bit5=32
import math
cnt = [0] * 6
tot = 0
for dr in N100:
    for n in dr['front']:
        for k in range(6):
            if n >> k & 1:
                cnt[k] += 1
        tot += 1
# 均匀理论：号码均匀抽自 1..35，bit k 置 1 的理论概率
theo = []
for k in range(6):
    c = sum(1 for n in range(1, 36) if n >> k & 1)
    theo.append(c / 35)
for k in range(6):
    obs = cnt[k] / tot
    se = math.sqrt(theo[k] * (1 - theo[k]) / tot)
    z = (obs - theo[k]) / se
    print(f'  bit{k}（权 {1 << k}）: 实际 {obs:.3f} vs 理论 {theo[k]:.3f}  z={z:+.2f} {"← 显著" if abs(z) > 2 else ""}')

print('\n=== B 二进制马尔可夫算法 walk-forward 回测 ===')
def markov_predict(fbits, bbits):
    """按每位 P(下期=1 | 本期状态) 打分（拉普拉斯平滑），返回前区 top5、后区 top2"""
    def scores(seq, m):
        sc = []
        for n in range(m):
            c11 = c10 = c01 = c00 = 0
            for i in range(len(seq) - 1):
                a, b = seq[i][n], seq[i + 1][n]
                if a and b: c11 += 1
                elif a: c10 += 1
                elif b: c01 += 1
                else: c00 += 1
            cur = seq[-1][n]
            p = (c11 + 1) / (c11 + c10 + 2) if cur else (c01 + 1) / (c01 + c00 + 2)
            sc.append(p)
        return sc
    fs = scores(fbits, 35)
    bs = scores(bbits, 12)
    top5 = sorted(range(35), key=lambda n: -fs[n])[:5]
    top2 = sorted(range(12), key=lambda n: -bs[n])[:2]
    return {n + 1 for n in top5}, {n + 1 for n in top2}

hits_f, hits_b, tot_pred = 0, 0, 0
WARM = 30
for t in range(WARM, len(N100)):
    pf, pb = markov_predict(F[:t], B[:t])
    act_f, act_b = set(N100[t]['front']), set(N100[t]['back'])
    hits_f += len(pf & act_f)
    hits_b += len(pb & act_b)
    tot_pred += 1
exp_f = 5 * 5 / 35
exp_b = 2 * 2 / 12
print(f'预测 {tot_pred} 期：前区总命中 {hits_f}（随机期望 {exp_f * tot_pred:.1f}），均值 {hits_f / tot_pred:.3f}/期 vs 期望 {exp_f:.3f}')
print(f'              后区总命中 {hits_b}（随机期望 {exp_b * tot_pred:.1f}），均值 {hits_b / tot_pred:.3f}/期 vs 期望 {exp_b:.3f}')

print('\n=== C 下一期预测（用全部 2927 期训练）===')
Fall = [bits(dr['front'], 35) for dr in draws]
Ball_ = [bits(dr['back'], 12) for dr in draws]
pf, pb = markov_predict(Fall, Ball_)
print('马尔可夫位模型 → 26111 预测：前区', sorted(pf), '+ 后区', sorted(pb))
