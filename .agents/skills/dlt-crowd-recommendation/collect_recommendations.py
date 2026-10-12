#!/usr/bin/env python3
"""Normalize collected public-source JSONL into auditable source/recommendation JSONL."""
import argparse, json
from pathlib import Path
from schemas import parse_source

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("input"); ap.add_argument("--out-dir",default="data"); args=ap.parse_args()
    out=Path(args.out_dir); out.mkdir(parents=True,exist_ok=True)
    srcf=open(out/"sources.jsonl","a",encoding="utf-8"); recf=open(out/"recommendations.jsonl","a",encoding="utf-8")
    counts={"sources":0,"parsed":0,"rejected":0,"recommendations":0}
    seen=set()
    recpath=out/"recommendations.jsonl"
    if recpath.exists():
        for line in recpath.open(encoding="utf-8"):
            try: seen.add(json.loads(line).get("recommendationId"))
            except json.JSONDecodeError: continue
    for line in open(args.input,encoding="utf-8"):
        if not line.strip(): continue
        source=json.loads(line); normalized, rec=parse_source(source); counts["sources"]+=1
        srcf.write(json.dumps(normalized,ensure_ascii=False)+"\n")
        if normalized.get("parseStatus")=="parsed": counts["parsed"]+=1
        else: counts["rejected"]+=1
        if rec and rec["recommendationId"] not in seen:
            recf.write(json.dumps(rec,ensure_ascii=False)+"\n"); seen.add(rec["recommendationId"]); counts["recommendations"]+=1
    srcf.close(); recf.close(); print(json.dumps(counts,ensure_ascii=False))
if __name__ == "__main__": main()
