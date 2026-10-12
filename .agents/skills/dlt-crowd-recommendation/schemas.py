"""Schemas and parser for public DLT recommendations."""
from __future__ import annotations
import hashlib, re
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import Optional

NUM_RE = re.compile(r"(?<!\d)(\d{1,2})(?!\d)")
ISSUE_RE = re.compile(r"(?<!\d)(26\d{3})(?!\d)")

def norm_url(url: str) -> str:
    return url.strip().split("#", 1)[0].rstrip("/")

def sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", "ignore")).hexdigest()[:20]

def extract_numbers(text: str):
    text = text.replace("＋", "+").replace("，", ",").replace("、", ",").replace("；", ";")
    # Prefer explicit front/back labels; accept common 5+2 notation.
    m = re.search(r"(?:前区|前区号码|前五|红球)\s*[:：]?\s*([0-9\s,，、]{4,})\s*(?:\+|加|[;；]\s*后区|后区|蓝球)", text)
    b = re.search(r"(?:后区|后区号码|后二区|蓝球)\s*[:：]?\s*([0-9\s,，、]{1,})", text)
    if m and b:
        f = [int(x) for x in NUM_RE.findall(m.group(1))]
        back = [int(x) for x in NUM_RE.findall(b.group(1))]
    else:
        pairs = re.findall(r"(?<!\d)((?:0?[1-9]|[12]\d|3[0-5])(?:\s+|[,，、])+(?:0?[1-9]|[12]\d|3[0-5])(?:\s+|[,，、])+(?:0?[1-9]|[12]\d|3[0-5])(?:\s+|[,，、])+(?:0?[1-9]|[12]\d|3[0-5])(?:\s+|[,，、])+(?:0?[1-9]|[12]\d|3[0-5]))\s*(?:\+|加)\s*((?:0?[1-9]|1[0-2])(?:\s+|[,，、])+(?:0?[1-9]|1[0-2]))", text)
        if not pairs: return None, None
        f = [int(x) for x in NUM_RE.findall(pairs[0][0])]
        back = [int(x) for x in NUM_RE.findall(pairs[0][1])]
    return sorted(f), sorted(back)

def validate(front, back):
    if len(front) != 5 or len(set(front)) != 5 or not all(1 <= x <= 35 for x in front):
        return False, "front must contain five unique numbers in 1..35"
    if len(back) != 2 or len(set(back)) != 2 or not all(1 <= x <= 12 for x in back):
        return False, "back must contain two unique numbers in 1..12"
    return True, None

def source_id(source):
    return sha("|".join([source.get("platform", ""), source.get("author", ""), norm_url(source.get("url", ""))]))

def parse_source(source):
    text = source.get("rawText", "")
    issues = ISSUE_RE.findall(" ".join([source.get("title", ""), text]))
    target = str(source.get("targetDrawNum") or (issues[0] if len(set(issues)) == 1 else ""))
    front, back = extract_numbers(text)
    out = dict(source)
    out["url"] = norm_url(out.get("url", "")); out["sourceId"] = source_id(out)
    out.setdefault("fetchedAt", datetime.now(timezone.utc).isoformat())
    out["contentHash"] = sha(re.sub(r"\s+", " ", text).strip())
    out["targetDrawNum"] = target
    published = str(out.get("publishedAt") or "")
    cutoff = str(out.get("cutoffAt") or "")
    if not published:
        out["timeConfidence"] = 0.0
    else:
        out["timeConfidence"] = 1.0
    if cutoff and published and published > cutoff:
        out.update(parseStatus="rejected", rejectReason="published after frozen cutoff")
        return out, None
    if not target or not front or not back:
        out.update(parseStatus="rejected", rejectReason="missing target or complete 5+2 numbers")
        return out, None
    ok, reason = validate(front, back)
    if not ok:
        out.update(parseStatus="rejected", rejectReason=reason)
        return out, None
    out.update(parseStatus="parsed", rejectReason=None)
    # The same exact ticket is one recommendation cluster even when reposted at a different URL.
    rec = {"recommendationId": sha(f"{out['sourceId']}|{target}|{front}|{back}"), "sourceId": out["sourceId"], "targetDrawNum": target, "front": front, "back": back, "kind": "exact_5_plus_2", "rawQuote": text, "parseConfidence": 0.98 * out["timeConfidence"], "isSyndicated": False, "duplicateCluster": sha(f"{target}|{front}|{back}")}
    return out, rec

__all__ = ["parse_source", "validate", "extract_numbers", "asdict"]
