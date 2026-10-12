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

def validate_pool(nums, maxn, min_count=1):
    if len(nums) < min_count or len(set(nums)) != len(nums) or not all(1 <= x <= maxn for x in nums):
        return False, f"pool must contain unique numbers in 1..{maxn}"
    return True, None

def extract_recommendation(text: str):
    """Return (kind, front, back) for exact tickets or partial public tips."""
    f, b = extract_numbers(text)
    if f and b:
        return "exact_5_plus_2", f, b
    def group(pattern, maxn):
        m = re.search(pattern, text)
        if not m: return None
        nums = sorted({int(x) for x in NUM_RE.findall(m.group(1))})
        return nums if validate_pool(nums, maxn)[0] else None
    front = group(r"(?:前区|前区号码)?\s*(?:五胆|胆码|大底号|推荐号码|号码池)\s*[:：]?\s*([0-9\s,，、]+)", 35)
    back = group(r"(?:后区|后区号码)?\s*(?:三胆|胆码|四码|五码|号码池)\s*[:：]?\s*([0-9\s,，、]+)", 12)
    if front and back: return "front_pool_back_pool", front, back
    if front: return "front_pool", front, None
    if back: return "back_pool", None, back
    return None, None, None

def source_id(source):
    return sha("|".join([source.get("platform", ""), source.get("author", ""), norm_url(source.get("url", ""))]))

def parse_source(source):
    text = source.get("rawText", "")
    issues = ISSUE_RE.findall(" ".join([source.get("title", ""), text]))
    target = str(source.get("targetDrawNum") or (issues[0] if len(set(issues)) == 1 else ""))
    kind, parsed_front, parsed_back = extract_recommendation(text)
    front, back = parsed_front, parsed_back
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
    if not target or not kind:
        out.update(parseStatus="rejected", rejectReason="missing target or recognizable recommendation")
        return out, None
    if kind == "exact_5_plus_2":
        ok, reason = validate(front, back)
        if not ok:
            out.update(parseStatus="rejected", rejectReason=reason)
            return out, None
    elif kind == "front_pool_back_pool":
        ok, reason = validate_pool(front, 35, 5)
        if not ok: out.update(parseStatus="rejected", rejectReason=reason); return out, None
        ok, reason = validate_pool(back, 12, 2)
        if not ok: out.update(parseStatus="rejected", rejectReason=reason); return out, None
    elif kind == "front_pool":
        ok, reason = validate_pool(front, 35, 1)
        if not ok: out.update(parseStatus="rejected", rejectReason=reason); return out, None
    elif kind == "back_pool":
        ok, reason = validate_pool(back, 12, 1)
        if not ok: out.update(parseStatus="rejected", rejectReason=reason); return out, None
    out.update(parseStatus="parsed", rejectReason=None)
    # The same exact ticket or pool is one recommendation cluster when reposted.
    payload = f"{target}|{kind}|{front}|{back}"
    rec = {"recommendationId": sha(f"{out['sourceId']}|{payload}"), "sourceId": out["sourceId"], "targetDrawNum": target, "front": front or [], "back": back or [], "kind": kind, "rawQuote": text, "parseConfidence": 0.98 * out["timeConfidence"], "isSyndicated": False, "duplicateCluster": sha(payload)}
    return out, rec

__all__ = ["parse_source", "validate", "extract_numbers", "asdict"]
