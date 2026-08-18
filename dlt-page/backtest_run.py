# -*- coding: utf-8 -*-
"""大乐透页面数据预计算：31算法双窗口回测 + 理论/蒙特卡洛基线 + 下期预测 → bt.json
数据源: dlt-analyzer 项目 draws.json（时间升序）"""
import json, sys
from math import comb
from itertools import combinations
sys.path.insert(0, 'D:/dream/dlt-analyzer/.agents/skills/dlt-analyzer')
import numpy as np
from algorithms import build_registry, backtest, cum_freq, repeat_flags, neighbor_counts, gap_map

DATA = 'D:/dream/dlt-analyzer/.agents/skills/dlt-analyzer/data/draws.json'
OUT  = 'D:/dream/dlt-page/bt.json'

data = json.load(open(DATA, encoding='utf-8'))
draws = data['draws'] if isinstance(data, dict) else data
N = len(draws)
front = np.array([d['front'] for d in draws])
back  = np.array([d['back']  for d in draws])
reg = build_registry()

def run(name, hs):
    r = backtest(name, draws, holdout_start=hs, reg=reg)
    return {'ge4': round(r['ge4'], 4), 'ge5': round(r['ge5'], 4),
            'avg': round(r['avg'], 4), 'dist': r['dist'], 'draws': r['draws']}

algos = []
for name in reg:
    algos.append({'name': name, 'hold100': run(name, N-100), 'hold1000': run(name, max(N-1000, 60))})
print(f'回测完成: {len(algos)} 算法 × 2 窗口')

# 理论基线 6+3（前6选35中5 + 后3选12中2，合计命中≥4）
pf = [comb(5,k)*comb(30,6-k)/comb(35,6) for k in range(6)]
pb = [comb(2,j)*comb(10,3-j)/comb(12,3) for j in range(3)]
theo_ge4 = sum(pf[k]*pb[j] for k in range(6) for j in range(3) if k+j >= 4)
theo_avg = sum(k*pf[k] for k in range(6)) + sum(j*pb[j] for j in range(3))

# 蒙特卡洛基线（同一留出段随机 6+3，40 轮）
rng = np.random.default_rng(26092)
holdout = draws[N-100:]
mc_ge4, mc_avg = [], []
for _ in range(40):
    s = 0; ge4n = 0
    for d in holdout:
        f6 = rng.choice(35, 6, replace=False) + 1
        b3 = rng.choice(12, 3, replace=False) + 1
        h = int(np.isin(f6, d['front']).sum()) + int(np.isin(b3, d['back']).sum())
        s += h; ge4n += (h >= 4)
    mc_ge4.append(ge4n/len(holdout)); mc_avg.append(s/len(holdout))

# 下一期预测（k=N：特征扩展一行，公式与 cum_freq/repeat/neighbor/gap 一致）
F = {'f_all_f': cum_freq(front,35,None), 'f30_f': cum_freq(front,35,30),
     'f5_f': cum_freq(front,35,5), 'f10_f': cum_freq(front,35,10),
     'b_all_b': cum_freq(back,12,None), 'b30_b': cum_freq(back,12,30),
     'b5_b': cum_freq(back,12,5), 'b10_b': cum_freq(back,12,10)}
R  = {'f': repeat_flags(front,35), 'b': repeat_flags(back,12)}
NC = {'f': np.stack([neighbor_counts(front,35,r) for r in range(1,4)],axis=2),
      'b': np.stack([neighbor_counts(back,12,r)  for r in range(1,4)],axis=2)}
G  = {'f': gap_map(front,35), 'b': gap_map(back,12)}
def bc(arr, maxn): return np.bincount(arr-1, minlength=maxn)[:maxn]
for key, arr, maxn, win in [('f_all_f',front,35,None),('f30_f',front,35,30),('f5_f',front,35,5),('f10_f',front,35,10),
                            ('b_all_b',back,12,None),('b30_b',back,12,30),('b5_b',back,12,5),('b10_b',back,12,10)]:
    row = F[key][N-1] + bc(arr[N-1], maxn)
    if win is not None and N-1-win >= 0: row = row - bc(arr[N-1-win], maxn)
    F[key] = np.vstack([F[key], row])
for key, arr, maxn in [('f',front,35),('b',back,12)]:
    row = np.zeros((1,maxn),dtype=np.int8); row[0, arr[N-1]-1] = 1
    R[key] = np.vstack([R[key], row])
    rows = []
    for ri in range(3):
        r = ri+1; cur = np.zeros(maxn, dtype=np.int8)
        for x in arr[N-1]:
            lo, hi = max(1,x-r), min(maxn,x+r); cur[lo-1:hi] += 1
        cur[arr[N-1]-1] -= 1; rows.append(cur)
    NC[key] = np.concatenate([NC[key], np.array(rows).T[np.newaxis]], axis=0)
for key, arr, maxn in [('f',front,35),('b',back,12)]:
    row = G[key][N-1] + 1; row[arr[N-1]-1] = 0
    G[key] = np.vstack([G[key], row])

pred = {}
for nm in ['AI_U_wide', 'K_prob_ensemble']:          # 主推/参考保持 6+3 复式
    f6, b3 = reg[nm](N, F, R, NC, G, front, back)
    pred[nm] = {'front6': [int(x) for x in f6], 'back3': [int(x) for x in b3]}

# v1/v2/v3 单式 5+2（大乐透标准一注，不用复式）
def v_scores(name, k):
    if name == 'v1_cold':
        sf = 0.5*G['f'][k] + (5 - F['f30_f'][k])*2.5 + (k/7.0 - F['f_all_f'][k])*0.3
        sb = 0.6*G['b'][k] + (3 - F['b30_b'][k])*2.0
    else:  # v2_hot
        sf = F['f5_f'][k]*3 + F['f10_f'][k]*1.5 + NC['f'][k,:,0]*4 + (F['f5_f'][k] >= 2)*4
        sb = F['b5_b'][k]*3 + F['b10_b'][k]*1.5
    return sf, sb
def pick_top5_constrained(scores, topk=12):
    """5 码单式约束：奇偶 2:3 或 3:2、三区间(1-12/13-24/25-35)各 1-2、和值 65-115、跨度>=15"""
    pool = (np.argsort(-scores)[:topk] + 1).tolist()
    best, bests = None, -1e18
    for combo in combinations(pool, 5):
        oe = sum(1 for n in combo if n % 2 == 1)
        z1 = sum(1 for n in combo if n <= 12); z2 = sum(1 for n in combo if 13 <= n <= 24); z3 = 5 - z1 - z2
        s5 = sum(combo); span = max(combo) - min(combo)
        if oe in (2, 3) and all(1 <= z <= 2 for z in (z1, z2, z3)) and 65 <= s5 <= 115 and span >= 15:
            sc = sum(scores[n-1] for n in combo)
            if sc > bests: bests, best = sc, combo
    return sorted(best) if best else sorted((np.argsort(-scores)[:5] + 1).tolist())
sf1, sb1 = v_scores('v1_cold', N)
sf2, sb2 = v_scores('v2_hot', N)
pred['v1_cold'] = {'front5': pick_top5_constrained(sf1), 'back2': [int(x) for x in (np.argsort(-sb1)[:2] + 1)]}
pred['v2_hot']  = {'front5': pick_top5_constrained(sf2), 'back2': [int(x) for x in (np.argsort(-sb2)[:2] + 1)]}
cold3 = [int(x) for x in (np.argsort(-sf1)[:3] + 1)]     # v3 = 冷号3 + 热号2（单式 5 码）
hot2  = [int(x) for x in (np.argsort(-sf2)[:2] + 1)]
pred['v3'] = {'front5': sorted(set(cold3 + hot2))[:5], 'back2': [int(x) for x in (np.argsort(-sb2)[:2] + 1)]}

out = {'N': N, 'algos': algos,
       'baseline': {'theo': {'ge4': theo_ge4, 'avg': theo_avg},
                    'mc': {'ge4m': float(np.mean(mc_ge4)), 'ge4s': float(np.std(mc_ge4)),
                           'avgm': float(np.mean(mc_avg)), 'avgs': float(np.std(mc_avg))}},
       'pred': pred}
json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False)
print(f'bt.json 完成: theo ge4={theo_ge4:.4f} avg={theo_avg:.4f} | mc ge4={np.mean(mc_ge4):.4f}±{np.std(mc_ge4):.4f}')
