#!/usr/bin/env python3
"""Aggregate independent public exact 5+2 recommendations into two diversified picks."""
import argparse, json, itertools
from collections import defaultdict
from pathlib import Path

def aggregate(recs, target):
    rows=[r for r in recs if str(r.get('targetDrawNum'))==str(target) and r.get('kind')=='exact_5_plus_2']
    clusters=defaultdict(list)
    for r in rows: clusters[r.get('duplicateCluster') or r['recommendationId']].append(r)
    fs=defaultdict(float); bs=defaultdict(float)
    for cluster, members in clusters.items():
        weight=min(1.0, max(float(x.get('parseConfidence',1)) for x in members))
        # Cluster earns one contribution; cap cluster weight independent of repost count.
        weight=min(1.0, weight)
        r=members[0]
        for n in r['front']: fs[n]+=weight
        for n in r['back']: bs[n]+=weight
    def valid(f):
        return len(f)==5 and len(set(f))==5 and 1<=min(f) and max(f)<=35
    fscore=lambda f: sum(fs[n] for n in f)
    bscore=lambda b: sum(bs[n] for n in b)
    combos=[(fscore(f)+bscore(b),f,b) for f in itertools.combinations(range(1,36),5) for b in itertools.combinations(range(1,13),2)]
    # Search only candidates containing supported numbers to keep this bounded.
    topf=sorted(fs,key=lambda n:(-fs[n],n))[:15] or list(range(1,36))
    topb=sorted(bs,key=lambda n:(-bs[n],n))[:6] or list(range(1,13))
    combos=[(fscore(f)+bscore(b),f,b) for f in itertools.combinations(topf,5) for b in itertools.combinations(topb,2) if valid(f)]
    combos.sort(reverse=True)
    if not combos: raise ValueError('no valid recommendations')
    first=combos[0]
    def diversified(x):
        overlap=len(set(x[1])&set(first[1]))+len(set(x[2])&set(first[2]))
        return x[0]-0.35*overlap
    alternatives=[x for x in combos[1:] if len(set(x[1])&set(first[1])) <= 3 and len(set(x[2])&set(first[2])) <= 1]
    second=max(alternatives or combos[1:], key=diversified) if len(combos)>1 else first
    return {'targetDrawNum':str(target),'sourceCount':len(rows),'clusterCount':len(clusters),'frontScores':dict(sorted(fs.items())), 'backScores':dict(sorted(bs.items())), 'picks':[{'front':list(first[1]),'back':list(first[2]),'score':first[0]},{'front':list(second[1]),'back':list(second[2]),'score':second[0]}], 'disclaimer':'Public recommendation aggregation is entertainment only; reposts are cluster-deduplicated and no odds improvement is claimed.'}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('target'); ap.add_argument('--input',default='data/recommendations.jsonl'); ap.add_argument('--out-dir',default='data/runs'); args=ap.parse_args()
    recs=[json.loads(x) for x in open(args.input,encoding='utf-8') if x.strip()]
    out=aggregate(recs,args.target); Path(args.out_dir).mkdir(parents=True,exist_ok=True)
    path=Path(args.out_dir)/f"{args.target}.json"; path.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8'); print(json.dumps(out,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
