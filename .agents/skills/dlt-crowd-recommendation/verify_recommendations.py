#!/usr/bin/env python3
"""Verify recommendation records against official draws.json, idempotently."""
import argparse,json
from pathlib import Path

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--recommendations',default='data/recommendations.jsonl'); ap.add_argument('--draws',default='/Users/mac/dream/dlt-analyzer/.agents/skills/dlt-analyzer/data/draws.json'); args=ap.parse_args()
 draws={str(x['num']):x for x in json.load(open(args.draws))['draws']}; out=[]
 for line in open(args.recommendations,encoding='utf-8'):
  if not line.strip():continue
  r=json.loads(line); d=draws.get(str(r.get('targetDrawNum')))
  if not d: out.append(r); continue
  r['actualFront']=d['front']; r['actualBack']=d['back']; r['frontHits']=len(set(r['front'])&set(d['front'])); r['backHits']=len(set(r['back'])&set(d['back'])); r['totalHits']=r['frontHits']+r['backHits']; r['verified']=True
  out.append(r)
 Path(args.recommendations).write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in out),encoding='utf-8')
 print(json.dumps({'verified':sum(1 for x in out if x.get('verified')),'total':len(out)},ensure_ascii=False))
if __name__=='__main__':main()
