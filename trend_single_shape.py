#!/usr/bin/env python3
"""Independent one-ticket trend/shape predictor: odd-even, zones and sum band."""
from __future__ import annotations
import argparse, hashlib, itertools, json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

VERSION='round-39'; WINDOW=50

def load_draws(path):
 x=json.loads(Path(path).read_text()); return x['draws'] if isinstance(x,dict) else x

def fp(ds): return 'sha256:'+hashlib.sha256(json.dumps(ds,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def odd(n): return n%2
def zones(nums): return (sum(n<=12 for n in nums),sum(13<=n<=24 for n in nums),sum(n>=25 for n in nums))
def sum_bin(s): return (s//10)*10

def mode_or(seq, allowed=None):
 c=Counter(seq); choices=[x for x in c if allowed is None or x in allowed]
 if not choices:return None,0
 return sorted(choices,key=lambda x:(-c[x],str(x)))[0],c[sorted(choices,key=lambda x:(-c[x],str(x)))[0]]

def target_shape(hist):
 win=hist[-WINDOW:]; shapes=[(sum(odd(n) for n in d['front']),zones(d['front']),sum(d['front'])) for d in win]
 allowed={2,3}; global_odd,_=mode_or([x[0] for x in shapes],allowed)
 global_zone,_=mode_or([x[1] for x in shapes])
 bins=[sum_bin(x[2]) for x in shapes]; global_sum,_=mode_or(bins)
 prev=shapes[-1]
 trans=[shapes[i][0:2]+(sum_bin(shapes[i][2]),) for i in range(1,len(shapes)) if shapes[i-1][0:2]==prev[0:2]]
 fallback=[]
 if len(trans)<3: fallback.append('conditional_shape_sample<3'); trans=shapes
 odd_target,_=mode_or([x[0] for x in trans],allowed) or global_odd
 zone_target,_=mode_or([x[1] for x in trans]) or global_zone
 sum_target,_=mode_or([x[2] for x in trans]) or global_sum
 sums=[x[2] for x in shapes]; lo=sorted(sums)[max(0,int(len(sums)*.1)-1)]; hi=sorted(sums)[min(len(sums)-1,int(len(sums)*.9))]
 return {'oddCount':odd_target,'zoneCounts':list(zone_target),'sumBin':sum_target,'sumBand':[max(lo,sum_target-9),min(hi,sum_target+19)],'fallback':fallback,'windowShapeCount':len(shapes)}

def predict(history):
 win=history[-WINDOW:]; prev=win[-1]; pf=set(prev['front']); nf={q for p in pf for q in(p-1,p+1) if 1<=q<=35}-pf
 last={n:-1 for n in range(1,36)}
 for i,d in enumerate(win):
  for n in d['front']:last[n]=i
 freq=Counter(n for d in win[-10:] for n in d['front']); target=target_shape(history)
 scores=[]
 for n in range(1,36):
  om=len(win)-1-last[n] if last[n]>=0 else len(win)
  base=(3 if n in pf else 0)+(2 if n in nf else 0)+(2 if om>=10.5 else 0)
  scores.append((n,base,freq[n]))
 scores.sort(key=lambda x:(-x[1],-x[2],x[0])); top=[x[0] for x in scores[:18]]
 candidates=[]
 for c in itertools.combinations(top,5):
  oddc=sum(odd(n) for n in c); z=zones(c); sm=sum(c); span=max(c)-min(c)
  if oddc==target['oddCount'] and tuple(z)==tuple(target['zoneCounts']) and target['sumBand'][0]<=sm<=target['sumBand'][1] and span>=15:
   candidates.append((sum(next(x[1] for x in scores if x[0]==n) for n in c),sum(next(x[2] for x in scores if x[0]==n) for n in c),c))
 relaxed=[]; reason=None
 if not candidates:
  reason='no_exact_shape_candidate'; relaxed.append('sumBand')
  for c in itertools.combinations(top,5):
   if sum(odd(n) for n in c)==target['oddCount'] and tuple(zones(c))==tuple(target['zoneCounts']) and max(c)-min(c)>=15: candidates.append((sum(x[1] for x in scores if x[0] in c),sum(x[2] for x in scores if x[0] in c),c))
 if not candidates:
  reason='zone_relaxed'; relaxed.append('zoneCounts')
  for c in itertools.combinations(top,5):
   if sum(odd(n) for n in c)==target['oddCount'] and sum(c)>=target['sumBand'][0] and sum(c)<=target['sumBand'][1] and max(c)-min(c)>=15: candidates.append((sum(x[1] for x in scores if x[0] in c),sum(x[2] for x in scores if x[0] in c),c))
 if not candidates:
  reason='top5_fallback'; relaxed.extend(['oddCount','zoneCounts','sumBand']); candidates=[(sum(x[1] for x in scores[:5]),sum(x[2] for x in scores[:5]),tuple(top[:5]))]
 candidates.sort(key=lambda x:(-x[0],-x[1],x[2])); front=sorted(candidates[0][2])
 # back ranking, separate 50-period causal features
 pb=set(prev['back']); nb={q for p in pb for q in(p-1,p+1) if 1<=q<=12}-pb; lb={n:-1 for n in range(1,13)}
 for i,d in enumerate(win):
  for n in d['back']:lb[n]=i
 bs=[]
 for n in range(1,13):
  om=len(win)-1-lb[n] if lb[n]>=0 else len(win); bs.append((n,(3 if n in pb else 0)+(2 if n in nb else 0)+(2 if om>=9 else 0), n in pb, n in nb))
 bs.sort(key=lambda x:(-x[1],x[0])); back=sorted([bs[0][0],bs[1][0]])
 return {'ticket':{'front':front,'back':back},'shapeSpec':target,'candidateCount':len(candidates),'fallbackReason':reason,'relaxedConstraints':relaxed,'numberStats':scores,'backStats':bs}

def evaluate(ticket,actual):
 hf=len(set(ticket['front'])&set(actual['front'])); hb=len(set(ticket['back'])&set(actual['back']))
 return {'status':'verified','actualDrawNum':actual['num'],'actualFront':actual['front'],'actualBack':actual['back'],'frontHits':hf,'backHits':hb,'totalHits':hf+hb,'ge4':hf+hb>=4,'verifiedAt':datetime.now(timezone.utc).isoformat()}

def make_entry(draws,index):
 if index<WINDOW:return None
 target=draws[index]['num'] if index<len(draws) else str(int(draws[-1]['num'])+1); asof=draws[index-1]['num']; hist=draws[:index]; p=predict(hist)
 e={'key':f'trend_single_shape|{VERSION}|target-{target}|asof-{asof}','recordType':'trend_single_shape_snapshot','strategyId':'trend_single_shape','strategyVersion':VERSION,'targetDrawNum':target,'asOfDrawNum':asof,'windowSize':WINDOW,'windowStartDrawNum':hist[-WINDOW]['num'],'windowEndDrawNum':asof,'sourceFingerprint':fp(hist[-WINDOW:]),'generatedAt':datetime.now(timezone.utc).isoformat(),**p,'evaluation':{'status':'pending'}}
 if index<len(draws):e['evaluation']=evaluate(e['ticket'],draws[index])
 return e

def run(draw_path,out):
 ds=load_draws(draw_path); old=json.loads(Path(out).read_text()) if Path(out).exists() else {'schemaVersion':1,'strategyId':'trend_single_shape','strategyVersion':VERSION,'items':[]}; by={x['key']:x for x in old.get('items',[])}
 for i in range(WINDOW,len(ds)+1):
  e=make_entry(ds,i)
  if e:
   if e['key'] in by and by[e['key']]['sourceFingerprint']==e['sourceFingerprint']:
    if by[e['key']].get('evaluation',{}).get('status')=='pending' and e['evaluation']['status']=='verified':by[e['key']]['evaluation']=e['evaluation']
   else:by[e['key']]=e
 items=sorted(by.values(),key=lambda x:x['key']); result={'schemaVersion':1,'strategyId':'trend_single_shape','strategyVersion':VERSION,'updatedAt':datetime.now(timezone.utc).isoformat(),'items':items}; Path(out).write_text(json.dumps(result,ensure_ascii=False,indent=1)); print(json.dumps({'items':len(items),'verified':sum(x['evaluation']['status']=='verified' for x in items),'pending':sum(x['evaluation']['status']=='pending' for x in items)},ensure_ascii=False))
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--draws',required=True);ap.add_argument('--output',required=True);a=ap.parse_args();run(a.draws,a.output)
