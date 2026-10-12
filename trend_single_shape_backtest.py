#!/usr/bin/env python3
"""Walk-forward metrics for trend_single_shape.py (single 5+2 ticket)."""
import json, math, numpy as np
from pathlib import Path
from trend_single_shape import load_draws, predict
D=load_draws('/Users/mac/dream/dlt-analyzer/.agents/skills/dlt-analyzer/data/draws.json'); T=len(D)
R={'calibration':(50,min(550,T)),'transfer':(min(550,T),min(650,T)),'holdout':(min(650,T),T)}
def ev(lo,hi):
 hs=[]; fronts=[];backs=[]; falls=[]
 for k in range(lo,hi):
  p=predict(D[:k]); f,b=p['ticket']['front'],p['ticket']['back']; af=set(D[k]['front']);ab=set(D[k]['back']);hf=len(set(f)&af);hb=len(set(b)&ab);hs.append(hf+hb);fronts.append(hf);backs.append(hb);falls.append(bool(p['fallbackReason']))
 return {'periods':len(hs),'ge4':sum(x>=4 for x in hs),'ge5':sum(x>=5 for x in hs),'ge4Rate':sum(x>=4 for x in hs)/len(hs),'ge5Rate':sum(x>=5 for x in hs)/len(hs),'avgFront':float(np.mean(fronts)),'avgBack':float(np.mean(backs)),'avgTotal':float(np.mean(hs)),'fallbackRate':sum(falls)/len(falls)}
# Exact unconstrained random single ticket ge4 and average.
# P>=4 is calculated by enumerating front/back hit counts.
from math import comb
C35=comb(35,5);C12=comb(12,2); p=sum(comb(5,f)*comb(30,5-f)/C35*comb(2,b)*comb(10,2-b)/C12 for f in range(6) for b in range(3) if f+b>=4)
out={'strategy':'trend_single_shape','version':'round-39','window':50,'splits':{k:ev(*v) for k,v in R.items()},'randomUnconstrained':{'ge4Rate':p,'expectedAvgTotal':5*5/35+2*2/12},'disclaimer':'Single-ticket shape constraints are entertainment; no probability or profit improvement is claimed.'}
Path('/Users/mac/dream/dlt-analyzer/trend_single_shape_result.json').write_text(json.dumps(out,ensure_ascii=False,indent=1))
print(json.dumps(out,ensure_ascii=False,indent=1))
