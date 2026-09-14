# -*- coding: utf-8 -*-
"""排列三历史开奖数据拉取（体彩官网 webapi）。

用法:
    python fetch_history.py                 # 首次/全量刷新，目标 1000 期
    python fetch_history.py --target 1500   # 指定期数

接口: https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry
  - gameNo=35 为排列三专属编号
  - pageNo=1 从最新一期开始，每页最多 100 期
  - termNum 参数对该接口不生效，必须用 pageNo 翻页
"""
import argparse
import json
import os
import ssl
import time
import urllib.request

API = "https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry"
GAME_NO = "35"

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.normpath(os.path.join(HERE, "..", "data"))
DRAWS_PATH = os.path.join(DATA_DIR, "draws.json")

_CTX = ssl.create_default_context()
_CTX.check_hostname = False
_CTX.verify_mode = ssl.CERT_NONE

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Referer": "https://static.sporttery.cn/",
    "Accept": "application/json, text/plain, */*",
}


def fetch_page(page_no, page_size=100, retries=4):
    url = (
        f"{API}?gameNo={GAME_NO}&provinceId=0&pageSize={page_size}"
        f"&isVerify=1&pageNo={page_no}"
    )
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=_HEADERS)
            with urllib.request.urlopen(req, timeout=25, context=_CTX) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            if not payload.get("success"):
                raise RuntimeError(payload.get("errorMessage") or "api returned success=false")
            return payload.get("value") or {}
        except Exception as exc:  # noqa: BLE001 - 网络抖动统一重试
            last_err = exc
            time.sleep(1.2 * (attempt + 1))
    raise RuntimeError(f"page {page_no} failed after {retries} tries: {last_err}")


def normalize(item):
    raw = (item.get("lotteryDrawResult") or "").split()
    digits = [int(x) for x in raw if x.isdigit()]
    if len(digits) != 3:
        raise ValueError(f"unexpected draw result: {item.get('lotteryDrawResult')!r}")
    return {
        "num": str(item.get("lotteryDrawNum") or "").strip(),
        "date": str(item.get("lotteryDrawTime") or "").strip(),
        "digits": digits,
    }


def fetch_history(target=1000, stop_at_num=None):
    """按 pageNo 翻页拉取，返回按期号升序的列表。

    stop_at_num 给定时（增量追加模式），一旦本页出现 <= 该期号的记录就停止翻页，
    避免每次运行都往前回填更老的期号。
    """
    by_num = {}
    page_no = 1
    total = None
    while True:
        value = fetch_page(page_no)
        if total is None:
            total = value.get("total")
            print(f"[fetch] 官方总期数 total={total}")
        batch = value.get("list") or []
        if not batch:
            break
        reached_local = False
        for item in batch:
            rec = normalize(item)
            if not rec["num"]:
                continue
            by_num[rec["num"]] = rec
            if stop_at_num is not None and rec["num"] <= stop_at_num:
                reached_local = True
        print(f"[fetch] page {page_no} -> 本批 {len(batch)} 期，累计 {len(by_num)} 期")
        page_no += 1
        # 增量模式：已触达本地最新期号，或已攒够目标期数，即可停止
        if reached_local or len(by_num) >= target or page_no > 400:
            break
        time.sleep(0.45)

    draws = sorted(by_num.values(), key=lambda r: r["num"])
    return draws[-target:] if len(draws) > target else draws


def merge(existing, incoming):
    """累计追加：按 num 去重合并，保持升序，绝不裁剪旧记录。"""
    by_num = {r["num"]: r for r in existing}
    added = 0
    for rec in incoming:
        if rec["num"] not in by_num:
            added += 1
        by_num[rec["num"]] = rec
    return sorted(by_num.values(), key=lambda r: r["num"]), added


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=int, default=1000, help="目标拉取期数（首次初始化）")
    args = parser.parse_args()

    os.makedirs(DATA_DIR, exist_ok=True)
    existing = []
    if os.path.exists(DRAWS_PATH):
        with open(DRAWS_PATH, encoding="utf-8") as fh:
            existing = json.load(fh)

    if existing:
        # 增量模式：从最新页往回翻，直到触达本地已有的最新期号即止
        local_latest = existing[-1]["num"]
        print(f"[追加] 本地最新 {local_latest}，共 {len(existing)} 期，只向前补新期号")
        incoming = fetch_history(target=args.target, stop_at_num=local_latest)
    else:
        incoming = fetch_history(target=args.target)

    mode = "追加" if existing else "初始化"
    merged, added = merge(existing, incoming)

    with open(DRAWS_PATH, "w", encoding="utf-8") as fh:
        json.dump(merged, fh, ensure_ascii=False, indent=1)

    print(
        f"[{mode}] 新增 {added} 期，本地共 {len(merged)} 期 "
        f"({merged[0]['num']} ~ {merged[-1]['num']}) -> {DRAWS_PATH}"
    )


if __name__ == "__main__":
    main()
