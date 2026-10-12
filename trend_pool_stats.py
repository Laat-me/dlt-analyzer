#!/usr/bin/env python3
"""Persist per-period trend-pool forecasts and separate pool/ticket hit metrics."""
from __future__ import annotations
import argparse, hashlib, json
from datetime import datetime, timezone
from pathlib import Path

STRATEGY_ID = "trend_wide15"
STRATEGY_VERSION = "round-34"
WINDOW = 50

def load_draws(path):
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return raw["draws"] if isinstance(raw, dict) else raw

def fingerprint(draws):
    body = json.dumps(draws, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return "sha256:" + hashlib.sha256(body.encode("utf-8")).hexdigest()

def score_pool(history):
    """Use only history supplied here; caller passes draws strictly before target."""
    if not history: raise ValueError("history cannot be empty")
    win = history[-WINDOW:]
    prev = win[-1]
    last_f = {n: -1 for n in range(1, 36)}
    last_b = {n: -1 for n in range(1, 13)}
    for i, draw in enumerate(win):
        for n in draw["front"]: last_f[n] = i
        for n in draw["back"]: last_b[n] = i
    prev_f, prev_b = set(prev["front"]), set(prev["back"])
    near_f = {q for p in prev_f for q in (p - 1, p + 1) if 1 <= q <= 35} - prev_f
    near_b = {q for p in prev_b for q in (p - 1, p + 1) if 1 <= q <= 12} - prev_b
    def omission(last, n): return len(win) - 1 - last[n] if last[n] >= 0 else len(win)
    front = []
    for n in range(1, 36):
        om = omission(last_f, n); front.append({"number": n, "score": (3 if n in prev_f else 0) + (2 if n in near_f else 0) + (2 if om >= 10.5 else 0), "omission": om, "repeat": n in prev_f, "neighbor": n in near_f, "overdue": om >= 10.5})
    back = []
    for n in range(1, 13):
        om = omission(last_b, n); back.append({"number": n, "score": (3 if n in prev_b else 0) + (2 if n in near_b else 0) + (2 if om >= 9 else 0), "omission": om, "repeat": n in prev_b, "neighbor": n in near_b, "overdue": om >= 9})
    front.sort(key=lambda x: (-x["score"], x["number"])); back.sort(key=lambda x: (-x["score"], x["number"]))
    pool_f = [x["number"] for x in front[:15]]; pool_b = [x["number"] for x in back[:3]]
    tickets = []
    for i, start in enumerate((0, 5, 10), 1):
        b = [(pool_b[0], pool_b[1]), (pool_b[2], pool_b[0]), (pool_b[1], pool_b[2])][i - 1]
        tickets.append({"index": i, "front": sorted(pool_f[start:start + 5]), "back": sorted(b)})
    return {"pool": {"front": pool_f, "back": pool_b}, "tickets": tickets, "frontNumbers": front, "backNumbers": back}

def make_key(target, asof): return f"dlt|{STRATEGY_ID}|{STRATEGY_VERSION}|target-{target}|asof-{asof}"

def evaluate(item, actual):
    af, ab = set(actual["front"]), set(actual["back"])
    pf, pb = item["pool"]["front"], item["pool"]["back"]
    results = []
    for t in item["tickets"]:
        hf, hb = len(set(t["front"]) & af), len(set(t["back"]) & ab)
        results.append({"index": t["index"], "frontHits": hf, "backHits": hb, "totalHits": hf + hb})
    best = max((x["totalHits"] for x in results), default=0)
    item["evaluation"] = {"status": "verified", "actualDrawNum": actual["num"], "actualFront": actual["front"], "actualBack": actual["back"], "poolFrontHits": len(set(pf) & af), "poolBackHits": len(set(pb) & ab), "poolTotalHits": len(set(pf) & af) + len(set(pb) & ab), "ticketResults": results, "bestTicketTotalHits": best, "bestTicketGe4": best >= 4, "verifiedAt": datetime.now(timezone.utc).isoformat()}

def build_snapshot(draws, index):
    target = draws[index]["num"] if index < len(draws) else str(int(draws[-1]["num"]) + 1)
    asof = draws[index - 1]["num"] if index > 0 else None
    if index < WINDOW or not asof: return None
    hist = draws[:index]
    calc = score_pool(hist)
    entry = {"key": make_key(target, asof), "recordType": "trend_pool_snapshot", "game": "dlt", "strategyId": STRATEGY_ID, "strategyVersion": STRATEGY_VERSION, "targetDrawNum": target, "asOfDrawNum": asof, "windowSize": WINDOW, "windowStartDrawNum": hist[-WINDOW]["num"], "windowEndDrawNum": asof, "sourceFingerprint": fingerprint(hist[-WINDOW:]), "generatedAt": datetime.now(timezone.utc).isoformat(), "pool": calc["pool"], "tickets": calc["tickets"], "numberStats": {"front": calc["frontNumbers"], "back": calc["backNumbers"]}, "evaluation": {"status": "pending", "actualDrawNum": None, "actualFront": None, "actualBack": None, "poolFrontHits": None, "poolBackHits": None, "poolTotalHits": None, "ticketResults": [], "bestTicketTotalHits": None, "bestTicketGe4": None, "verifiedAt": None}}
    if index < len(draws): evaluate(entry, draws[index])
    return entry

def upsert(draws, existing=None):
    existing = existing or {"schemaVersion": 1, "strategyId": STRATEGY_ID, "strategyVersion": STRATEGY_VERSION, "items": []}
    by_key = {x["key"]: x for x in existing.get("items", [])}
    for index in range(WINDOW, len(draws) + 1):
        entry = build_snapshot(draws, index)
        if not entry: continue
        old = by_key.get(entry["key"])
        if old and old.get("sourceFingerprint") == entry["sourceFingerprint"]:
            if old.get("evaluation", {}).get("status") == "pending" and entry["evaluation"]["status"] == "verified": old["evaluation"] = entry["evaluation"]
            continue
        by_key[entry["key"]] = entry
    items = sorted(by_key.values(), key=lambda x: x["key"])
    unchanged = bool(existing.get("items")) and existing.get("items") == items
    return {"schemaVersion": 1, "strategyId": STRATEGY_ID, "strategyVersion": STRATEGY_VERSION, "updatedAt": existing.get("updatedAt") if unchanged else datetime.now(timezone.utc).isoformat(), "items": items, "summary": summarize(items)}

def summarize(items):
    verified = [x for x in items if x.get("evaluation", {}).get("status") == "verified" and not x.get("invalidated")]
    def avg(key): return round(sum(x["evaluation"].get(key, 0) for x in verified) / len(verified), 4) if verified else None
    ge4 = sum(bool(x["evaluation"].get("bestTicketGe4")) for x in verified)
    return {"verifiedPeriods": len(verified), "poolFrontAvg": avg("poolFrontHits"), "poolBackAvg": avg("poolBackHits"), "poolTotalAvg": avg("poolTotalHits"), "bestTicketAvg": avg("bestTicketTotalHits"), "bestTicketGe4Count": ge4, "bestTicketGe4Rate": round(ge4 / len(verified), 6) if verified else None, "range": [verified[0]["targetDrawNum"], verified[-1]["targetDrawNum"]] if verified else None}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--draws", required=True); ap.add_argument("--output", required=True); args = ap.parse_args()
    draws = load_draws(args.draws); path = Path(args.output); old = json.loads(path.read_text()) if path.exists() else None
    result = upsert(draws, old); tmp = path.with_suffix(path.suffix + ".tmp"); tmp.write_text(json.dumps(result, ensure_ascii=False, indent=1)); tmp.replace(path)
    print(json.dumps(result["summary"], ensure_ascii=False))

if __name__ == "__main__": main()
