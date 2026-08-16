# -*- coding: utf-8 -*-
"""复盘步骤B：31算法对26092期的事后前向验证 + 26093期预测生成"""
import json, sys
sys.path.insert(0, '.agents/skills/dlt-analyzer')
import numpy as np
from algorithms import build_registry, cum_freq, repeat_flags, neighbor_counts, gap_map

data = json.load(open('.agents/skills/dlt-analyzer/data/draws.json', encoding='utf-8'))
draws = data['draws'] if isinstance(data, dict) else data
N = len(draws)
front = np.array([d['front'] for d in draws])
back  = np.array([d['back']  for d in draws])

# 标准特征（行 0..N-1）
F = {
    'f_all_f': cum_freq(front,35,None), 'f30_f': cum_freq(front,35,30),
    'f5_f':  cum_freq(front,35,5),      'f10_f': cum_freq(front,35,10),
    'b_all_b': cum_freq(back,12,None),  'b30_b': cum_freq(back,12,30),
    'b5_b':  cum_freq(back,12,5),       'b10_b': cum_freq(back,12,10),
}
R  = {'f': repeat_flags(front,35), 'b': repeat_flags(back,12)}
NC = {'f': np.stack([neighbor_counts(front,35,r) for r in range(1,4)],axis=2),
      'b': np.stack([neighbor_counts(back,12,r)  for r in range(1,4)],axis=2)}
G  = {'f': gap_map(front,35), 'b': gap_map(back,12)}

# 扩展一行 k=N（供预测下一期使用），公式与 cum_freq/repeat/neighbor/gap 完全一致
def bc(arr, maxn):
    return np.bincount(arr - 1, minlength=maxn)[:maxn]
for key, arr, maxn, win in [('f_all_f',front,35,None),('f30_f',front,35,30),('f5_f',front,35,5),('f10_f',front,35,10),
                            ('b_all_b',back,12,None),('b30_b',back,12,30),('b5_b',back,12,5),('b10_b',back,12,10)]:
    row = F[key][N-1] + bc(arr[N-1], maxn)
    if win is not None and N-1-win >= 0:
        row = row - bc(arr[N-1-win], maxn)
    F[key] = np.vstack([F[key], row])
for key, arr, maxn in [('f',front,35),('b',back,12)]:
    row = np.zeros((1,maxn),dtype=np.int8); row[0, arr[N-1]-1] = 1
    R[key] = np.vstack([R[key], row])
    rows = []
    for ri in range(3):
        r = ri + 1
        cur = np.zeros(maxn, dtype=np.int8)
        for x in arr[N-1]:
            lo, hi = max(1,x-r), min(maxn,x+r)
            cur[lo-1:hi] += 1
        cur[arr[N-1]-1] -= 1
        rows.append(cur)
    NC[key] = np.concatenate([NC[key], np.array(rows).T[np.newaxis]], axis=0)
for key, arr, maxn in [('f',front,35),('b',back,12)]:
    row = G[key][N-1] + 1
    row[arr[N-1]-1] = 0
    G[key] = np.vstack([G[key], row])

reg = build_registry()

# ---- 26092 事后复盘：k=N-1 只用 26091 及之前数据 ----
k = N - 1
af, ab = draws[k]['front'], draws[k]['back']
print(f'复盘目标: 第 {draws[k]["num"]} 期  实际 前区 {af}  后区 {ab}')
print(f'{"算法":<20}{"前区6":<24}{"后区3":<12}{"前中":>3}{"后中":>3}{"合计":>3}  达标')
ge4 = 0
results = []
for name, fn in reg.items():
    f6, b3 = fn(k, F, R, NC, G, front, back)
    hf = int(np.isin(f6, af).sum()); hb = int(np.isin(b3, ab).sum())
    ok = (hf + hb) >= 4
    ge4 += ok
    results.append({'name': name, 'front6': [int(x) for x in f6], 'back3': [int(x) for x in b3],
                    'frontHits': hf, 'backHits': hb, 'ge4': bool(ok)})
    print(f'{name:<20}{str([int(x) for x in f6]):<24}{str([int(x) for x in b3]):<12}{hf:>3}{hb:>3}{hf+hb:>3}  {"✓" if ok else ""}')
print(f'\n31 算法中达标(≥4) {ge4} 个; 随机基线约 2% (期望 ~0.6 个)')

# ---- 26093 预测（AI_U_wide 主 + K_prob_ensemble 参考） ----
k2 = N
pred = {}
for nm in ['AI_U_wide', 'K_prob_ensemble', 'v1_cold']:
    f6, b3 = reg[nm](k2, F, R, NC, G, front, back)
    pred[nm] = {'front6': [int(x) for x in f6], 'back3': [int(x) for x in b3]}
print(f'\n26093 期预测(6+3):')
for nm, p in pred.items():
    print(f'  {nm:<18} 前区 {p["front6"]}  后区 {p["back3"]}')
json.dump({'review26092': results, 'pred26093': pred},
          open('review_out.json','w',encoding='utf-8'), ensure_ascii=False, indent=1)
print('已写入 review_out.json')
