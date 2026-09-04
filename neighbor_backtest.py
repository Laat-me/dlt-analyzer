# -*- coding: utf-8 -*-
"""round-27/28 独立回测：跨期邻号特征是否优于不含它的基线
口径：6+3 命中≥4（ge4）/avg；数据：draws.json 19123-26096 共 N 期
窗口：A) 900/100 = 热身 len-100、留出最近100
      B) 长窗口  = 热身 len-500、留出最近500（本地无 2909 全量，无法复现官方 1900/1000，如实标注）
说明：prev_neighbor(1)=上期±1且集合排除重号；repeat=上期原号"""
import json, sys
sys.path.insert(0, '.agents/skills/dlt-analyzer')
import numpy as np
from algorithms import build_registry, cum_freq, norm, repeat_flags, prev_neighbor_flags, backtest
from itertools import combinations

data = json.load(open('.agents/skills/dlt-analyzer/data/draws.json', encoding='utf-8'))
draws = data['draws'] if isinstance(data, dict) else data
N = len(draws)
front = np.array([d['front'] for d in draws])
back = np.array([d['back'] for d in draws])
Ff = cum_freq(front, 35, None); Bb = cum_freq(back, 12, None)
Rf = repeat_flags(front, 35);  Rb = repeat_flags(back, 12)
PNf = prev_neighbor_flags(front, 35, 1)
PNb = prev_neighbor_flags(back, 12, 1)

def top6(s): return sorted((np.argsort(-s)[:6] + 1).tolist())
def top3(s): return sorted((np.argsort(-s)[:3] + 1).tolist())

def run_window(warm):
    models = {}
    for k in range(warm, N):
        nf = norm(Ff)[k]; nb_ = norm(Bb)[k]
        base = (nf, nb_)
        bR = (nf + 0.18 * Rf[k], nb_ + 0.18 * Rb[k])
        bRN = (nf + 0.5 * Rf[k] + 0.2 * PNf[k].astype(np.float32),
               nb_ + 0.5 * Rb[k] + 0.2 * PNb[k].astype(np.float32))
        # 去重号后叠加：只加跨期邻号（不含重号项）
        bN = (nf + 0.2 * PNf[k].astype(np.float32), nb_ + 0.2 * PNb[k].astype(np.float32))
        af, ab = front[k], back[k]
        for name, (sf, sb) in [('base', base), ('base+repeat', bR),
                               ('base+repeat+prevN1', bRN), ('base+prevN1', bN)]:
            f6, b3 = top6(sf), top3(sb)
            hit = int(np.isin(f6, af).sum()) + int(np.isin(b3, ab).sum())
            m = models.setdefault(name, {'s': 0, 'n': 0, 'ge4': 0})
            m['s'] += hit; m['n'] += 1; m['ge4'] += hit >= 4
    return {n: (v['ge4'] / v['n'], v['s'] / v['n']) for n, v in models.items()}

for label, warm in [('900/100(留出最近100)', N - 100), ('长窗口(留出最近500)', N - 500)]:
    print(f'=== {label} === (训练到第{warm}期)')
    for name, (ge4, avg) in run_window(warm).items():
        print(f'  {name:<22} ge4={ge4*100:.2f}%  avg={avg:.3f}')
    print()
print('随机基线(理论,6+3): ge4≈2.04%  avg≈1.36')
