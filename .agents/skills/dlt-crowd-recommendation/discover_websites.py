#!/usr/bin/env python3
"""Discover public lottery-recommendation websites from Bing HTML, saving domain list only."""
from __future__ import annotations
import argparse, json, re, sys, time, html
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, unquote
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from site_schema import site_from_url, dedupe_sites

QUERIES = ('"大乐透 26116期" 预测', '"大乐透第26116期" 推荐', '"大乐透26116期" 胆码', '"26116期 大乐透" 前区 后区', '"大乐透26116期" 大底号')
HREF_RE = re.compile(r'href=["\'](https?://[^"\']+)["\']', re.I)
BING_REDIRECT_RE = re.compile(r"[?&]u=a1([^&]+)")

def build_queries(target):
    return tuple(q.replace("26116", str(target)) for q in QUERIES)

def decode_href(url):
    # Bing HTML may expose direct links or /ck/a redirect links.
    m = BING_REDIRECT_RE.search(url)
    if m:
        try:
            import base64
            raw = base64.urlsafe_b64decode(m.group(1) + "=" * (-len(m.group(1)) % 4)).decode("utf-8", "ignore")
            if raw.startswith("http"): return raw
        except Exception: return url
    return unquote(url)

def fetch_search(query, page, timeout=20):
    first = page * 10 + 1
    url = "https://www.bing.com/search?q=" + quote(query) + f"&first={first}"
    req = Request(url, headers={"User-Agent":"Mozilla/5.0", "Accept":"text/html"})
    with urlopen(req, timeout=timeout) as r:
        body = html.unescape(r.read().decode("utf-8", "ignore"))
        result_chunks = re.findall(r'<li[^>]*class=["\'][^"\']*b_algo[^"\']*["\'][\s\S]*?</li>', body, re.I)
        target_match = re.search(r'(26\d{3})', query)
        target = target_match.group(1) if target_match else ''
        urls = []
        for chunk in result_chunks:
            plain = re.sub(r'<[^>]+>', ' ', chunk)
            if ('大乐透' not in plain and 'dlt' not in plain.lower()) or (target and target not in plain):
                continue
            urls.extend(decode_href(x) for x in HREF_RE.findall(chunk))
        return urls, r.status

def discover(target, output, pages=2, per_page=10, max_sites=50, delay=0.5, retries=2):
    found=[]; stats={"targetDrawNum":str(target),"queries":0,"rawResults":0,"filtered":0,"sites":0,"failedQueries":[]}
    now=datetime.now(timezone.utc).isoformat()
    for query in build_queries(target):
        stats["queries"] += 1
        for page in range(pages):
            ok=False
            for attempt in range(retries+1):
                try:
                    urls,status=fetch_search(query,page); ok=True; break
                except (HTTPError, URLError, TimeoutError, OSError) as e:
                    if attempt >= retries: stats["failedQueries"].append({"query":query,"page":page,"error":type(e).__name__}); urls=[]
                    else: time.sleep(min(2.0, delay*(attempt+1)))
            stats["rawResults"] += len(urls)
            for url in urls[:per_page]:
                site=site_from_url(url,query,str(target),now)
                if site: found.append(site)
                else: stats["filtered"] += 1
            time.sleep(delay)
    sites=dedupe_sites(found,max_sites); stats["sites"]=len(sites)
    payload={"generatedAt":now,"targetDrawNum":str(target),"sites":sites,"stats":stats,"note":"Domain list only; no webpage text, author, numbers or recommendation records are saved."}
    path=Path(output); path.parent.mkdir(parents=True,exist_ok=True); tmp=path.with_suffix(path.suffix+".tmp"); tmp.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8"); tmp.replace(path)
    return payload

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("target"); ap.add_argument("--output",default="data/sites.json"); ap.add_argument("--pages",type=int,default=2); ap.add_argument("--per-page",type=int,default=10); ap.add_argument("--max-sites",type=int,default=50); ap.add_argument("--delay",type=float,default=.5); args=ap.parse_args()
    print(json.dumps(discover(args.target,args.output,args.pages,args.per_page,args.max_sites,args.delay),ensure_ascii=False,indent=2))
if __name__=="__main__": main()
