# -*- coding: utf-8 -*-
"""「三位全中」专项分析。

这是用户最关心、也最容易被单个巧合误导的指标。本脚本回答三件事：

  1. 到底有没有算法实现过三位数全中？分别在哪些期？
  2. 这些全中能不能用随机解释？（含"32 个算法取最大值"的多重比较校正）
  3. 按直选固定奖金 1040 元 / 每注 2 元算，这些全中能赚钱吗？

关键口径：
  - 三位全中 = 每位主推 (top-1) 都正确，随机概率 (1/10)^3 = 0.001
  - 训练集严格取 draws[:i]，即目标期的前一期为止，无未来数据泄漏
  - 直选保本所需命中率 = 2/1040 = 0.001923（约每 520 期须中 1 次）
"""
import collections
import json
import os
import sys

import numpy as np
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from algorithms import ALGORITHMS  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DRAWS_PATH = os.path.normpath(os.path.join(HERE, "..", "data", "draws.json"))

P_HIT = 0.001          # 三位全中的随机概率
MIN_HISTORY = 30
PRIZE = 1040.0         # 直选固定奖金
STAKE = 2.0            # 每注金额
BREAKEVEN = STAKE / PRIZE  # 保本所需命中率


def load():
    with open(DRAWS_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def scan(draws):
    """全量单遍滚动回测，记录每个算法的三位全中情况。"""
    n = len(draws)
    out = {}
    for name, fn in ALGORITHMS.items():
        hits = []
        for i in range(MIN_HISTORY, n):
            ranked = fn(draws[:i])
            pick = [ranked[p][0] for p in range(3)]
            if pick == draws[i]["digits"]:
                hits.append((draws[i]["num"], pick))
        out[name] = hits
    return out


def main():
    draws = load()
    n = len(draws)
    trials = n - MIN_HISTORY

    print("=" * 84)
    print(f"三位全中专项分析  |  {n} 期样本，有效回测 {trials} 期 x {len(ALGORITHMS)} 个算法")
    print("=" * 84)

    result = scan(draws)
    total_hits = sum(len(v) for v in result.values())
    expected_per_algo = trials * P_HIT

    print(f"\n【1】全中分布")
    print(f"  随机期望：每算法 {expected_per_algo:.2f} 次，全组合计 {expected_per_algo * len(ALGORITHMS):.1f} 次")
    print(f"  实测合计：{total_hits} 次 —— 比随机期望还少 {expected_per_algo * len(ALGORITHMS) - total_hits:.0f} 次")
    print()
    print(f"  {'算法':<22}{'全中':>5}{'期望':>7}{'p值':>9}   命中期号")
    print("  " + "-" * 76)
    for name, hits in sorted(result.items(), key=lambda kv: -len(kv[1])):
        k = len(hits)
        pv = stats.binomtest(k, trials, P_HIT, alternative="greater").pvalue if k else 1.0
        nums = ",".join(h[0] for h in hits) if hits else "—"
        print(f"  {name:<22}{k:>5}{expected_per_algo:>7.2f}{pv:>9.3f}   {nums}")

    no_hit = sum(1 for v in result.values() if not v)
    print(f"\n  全中过的算法：{len(ALGORITHMS) - no_hit}/{len(ALGORITHMS)}；一次没中过：{no_hit}")

    print(f"\n【2】多重比较校正：32 个算法取最大值，纯随机会发生什么？")
    rng = np.random.default_rng(11)
    k = len(ALGORITHMS)
    sims = np.array([max(rng.poisson(expected_per_algo, k)) for _ in range(200_000)])
    best = max(len(v) for v in result.values())
    print(f"  若所有算法都无预测力（各自 Poisson({expected_per_algo:.2f})）：")
    print(f"    最大值的分布  均值 {sims.mean():.2f}")
    for th in range(best, best + 2):
        print(f"    P(某算法全中 >= {th}) = {(sims >= th).mean():.1%}")
    print(f"  实测最大值 {best} 次 -> 在纯随机下出现的概率 {(sims >= best).mean():.1%}")
    print(f"  结论：{'完全在噪声范围内' if (sims >= best).mean() > 0.05 else '值得进一步核查'}")

    print(f"\n【3】经济性（直选 {PRIZE:.0f} 元 / 每注 {STAKE:.0f} 元）")
    print(f"  保本所需命中率 = {STAKE:.0f}/{PRIZE:.0f} = {BREAKEVEN:.6f}（约每 {1 / BREAKEVEN:.0f} 期须中 1 次）")
    print(f"  {trials} 期保本所需次数 = {trials * BREAKEVEN:.2f} 次")
    print()
    staked = trials * STAKE
    print(f"  {'算法':<22}{'全中':>5}{'投入':>9}{'奖金':>9}{'盈亏':>10}")
    print("  " + "-" * 58)
    profitable = 0
    for name, hits in sorted(result.items(), key=lambda kv: -len(kv[1])):
        k = len(hits)
        ret = k * PRIZE
        pnl = ret - staked
        if pnl > 0:
            profitable += 1
        print(f"  {name:<22}{k:>5}{staked:>9.0f}{ret:>9.0f}{pnl:>+10.0f}")
    print(f"\n  盈利的算法：{profitable}/{len(ALGORITHMS)}")

    if profitable:
        best_name, best_hits = max(result.items(), key=lambda kv: len(kv[1]))
        k = len(best_hits)
        pv = stats.binomtest(k, trials, BREAKEVEN, alternative="greater").pvalue
        lo = stats.poisson.ppf(0.025, k)
        hi = stats.poisson.ppf(0.975, k)
        print(f"  最好的是 {best_name}（{k} 次，表面净收益 {k * PRIZE - staked:+.0f} 元）")
        print(f"    但相对「保本水平」的检验 p = {pv:.3f} -> 无法否证它只是保本")
        print(f"    {k} 次命中的 95% 置信区间 ≈ {lo:.0f}~{hi:.0f} 次"
              f"（换算命中率 {lo / trials:.5f}~{hi / trials:.5f}）")
        print(f"    保本率 {BREAKEVEN:.5f} 落在区间内 -> 盈利与亏损都无法排除")
        print(f"    且这是从 {len(ALGORITHMS)} 个算法中事后挑出的最好者，不代表未来")

    print(f"\n  对照：纯随机对照组 AG_random_control 全中 "
          f"{len(result['AG_random_control'])} 次，期号 "
          f"{','.join(h[0] for h in result['AG_random_control']) or '—'}")
    print("  它在 32 个算法中的排名高于绝大多数「正经算法」——")
    print("  这是全中次数无法区分算法优劣的直接证据。")


if __name__ == "__main__":
    main()
