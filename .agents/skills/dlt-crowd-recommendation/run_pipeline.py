#!/usr/bin/env python3
"""Search, fetch, extract and aggregate public DLT recommendations in one run."""
from __future__ import annotations
import argparse, json, tempfile, re
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from discover_websites import discover
from page_extract import visible_text, parse_segments
from site_schema import canonicalize_url
from collections import defaultdict

def fetch_page(url, timeout=15):
    req=Request(url,headers={'User-Agent':'Mozilla/5.0','Accept':'text/html'})
    with urlopen(req,timeout=timeout) as r:
        body=r.read(2_000_000).decode('utf-8','ignore'); return body,r.status,r.headers.get('content-type','')

def aggregate(target, records):
    clusters={}
    for r in records:
        payload=f"{target}|{r['kind']}|{r.get('front',[])}|{r.get('back',[])}"
        clusters.setdefault(payload,r)
    fs=defaultdict(float); bs=defaultdict(float); kinds=defaultdict(int)
    for r in clusters.values():
        factor={'exact_5_plus_2':1.0,'front_pool_back_pool':.7,'front_pool':.45,'back_pool':.45}.get(r['kind'],0)
        kinds[r['kind']]+=1
        for n in r.get('front',[]): fs[n]+=factor*r.get('confidence',.5)
        for n in r.get('back',[]): bs[n]+=factor*r.get('confidence',.5)
    topf=sorted(fs,key=lambda n:(-fs[n],n)); topb=sorted(bs,key=lambda n:(-bs[n],n))
    if len(topf)<5 or len(topb)<2: return {'status':'insufficient_evidence','reason':'fewer than five supported front or two supported back numbers','sourceTypes':dict(kinds)}
    first={'front':sorted(topf[:5]),'back':sorted(topb[:2]),'score':sum(fs[n] for n in topf[:5])+sum(bs[n] for n in topb[:2])}
    candidates=[]
    for f in [topf[:15]]:
      for b in [topb[:6]]:
       import itertools
       for cf in itertools.combinations(f,5):
        for cb in itertools.combinations(b,2): candidates.append({'front':list(cf),'back':list(cb),'score':sum(fs[n] for n in cf)+sum(bs[n] for n in cb)})
    alternatives=[x for x in candidates if len(set(x['front'])&set(first['front']))<=3 and len(set(x['back'])&set(first['back']))<=1]
    second=max(alternatives or candidates,key=lambda x:x['score'])
    return {'status':'ok','sourceTypes':dict(kinds),'clusterCount':len(clusters),'frontScores':dict(fs),'backScores':dict(bs),'picks':[first,second],'disclaimer':'Public web recommendations are entertainment only; no odds or profit improvement is claimed.'}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('target'); ap.add_argument('--output',default='data/runs'); ap.add_argument('--pages',type=int,default=1); ap.add_argument('--per-page',type=int,default=10); ap.add_argument('--max-sites',type=int,default=30); args=ap.parse_args()
    with tempfile.TemporaryDirectory() as td:
        sites_path=Path(td)/'sites.json'; discovery=discover(args.target,str(sites_path),args.pages,args.per_page,args.max_sites,.3,1); sites=discovery['sites']; records=[]; stats={'pages':0,'parsedPages':0,'blocked':0,'parseRecords':0}
        for site in sites:
            try:
                raw,status,ctype=fetch_page(site['representativeUrl']); stats['pages']+=1
                text=visible_text(raw); recs,err=parse_segments(text,args.target)
                if recs: stats['parsedPages']+=1; records.extend(recs)
            except (HTTPError,URLError,TimeoutError,OSError): stats['blocked']+=1
        result=aggregate(args.target,records); result.update({'targetDrawNum':str(args.target),'generatedAt':datetime.now(timezone.utc).isoformat(),'websites':[s['domain'] for s in sites],'discoveryStats':discovery['stats'],'pageStats':stats,'recordCount':len(records)})
    out=Path(args.output); out.mkdir(parents=True,exist_ok=True); path=out/f'{args.target}.json'; tmp=path.with_suffix('.tmp'); tmp.write_text(json.dumps(result,ensure_ascii=False,indent=2)); tmp.replace(path); print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
