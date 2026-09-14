# -*- coding: utf-8 -*-
"""排列三随机性诊断：在谈"预测"之前，先判断历史数据里到底有没有可利用的信号。

包含：
  1. 每位数字分布均匀性（卡方，9 自由度）
  2. 前后期独立性：同位转移矩阵卡方（81 自由度）+ 同位重号率二项检验
  3. 和值分布 vs 理论分布（卡方）
  4. 和值一阶自相关 + 游程检验
  5. 三位之间是否独立（列联表卡方）
  6. 分段稳定性：把样本切成 5 段做齐性检验，看"热号"是否漂移
  7. 最优算法的 Top-2 覆盖率是否显著优于随机基线（含多重比较校正）
"""
import json
import os

import numpy as np
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.normpath(os.path.join(HERE, "..", "data"))
DRAWS_PATH = os.path.join(DATA_DIR, "draws.json")

RNG = np.random.default_rng(20260910)


def load():
    with open(DRAWS_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def fmt_p(p):
    if p < 1e-4:
        return f"{p:.2e}"
    return f"{p:.4f}"


def verdict(p, alpha=0.05):
    return "显著偏离随机" if p < alpha else "无显著偏离（与随机一致）"


def test_positional_uniformity(digits):
    """digits: (n,3) 数组。每位对 0-9 做均匀性卡方检验。"""
    print("【1】每位数字分布均匀性（H0: 每位 0-9 等概率）")
    for p in range(3):
        counts = np.bincount(digits[:, p], minlength=10)
        chi2, pval = stats.chisquare(counts)
        print(f"  位置{p + 1}: chi2={chi2:6.2f}  df=9  p={fmt_p(pval)}  -> {verdict(pval)}")
        print(f"            频次 {counts.tolist()}")


def test_independence(digits):
    print("\n【2】前后期独立性")
    for p in range(3):
        prev, cur = digits[:-1, p], digits[1:, p]
        table = np.zeros((10, 10), dtype=int)
        np.add.at(table, (prev, cur), 1)
        chi2, pval, dof, _ = stats.chi2_contingency(table)
        print(f"  位置{p + 1} 转移矩阵: chi2={chi2:6.2f}  df={dof}  p={fmt_p(pval)}  -> {verdict(pval)}")

    n = len(digits) - 1
    # (a) 同位重号：至少一位与上期同一位置相同。独立均匀下 = 1 - 0.9^3
    same_pos = np.array([(digits[i] == digits[i - 1]) for i in range(1, len(digits))])
    hit = int((same_pos.sum(axis=1) > 0).sum())
    p_any = 1 - 0.9 ** 3
    pval = stats.binomtest(hit, n, p_any).pvalue
    print(f"  同位重号(至少一位同位置重复)：观测 {hit}/{n} = {hit / n:.2%}，"
          f"理论 {p_any:.2%}，p={fmt_p(pval)} -> {verdict(pval)}")
    for p in range(3):
        h = int(same_pos[:, p].sum())
        pv = stats.binomtest(h, n, 0.10).pvalue
        print(f"    位置{p + 1} 单列同位重号率 {h / n:6.2%} (理论 10%)  p={fmt_p(pv)}  -> {verdict(pv)}")

    # (b) 号码重号：本期数字集合与上期数字集合有交集。
    #     理论值需对"上期有几个不同数字"求期望，直接用样本解析计算，避免口径错位。
    theo_no_overlap = 0.0
    for k, prob in ((1, 0.01), (2, 0.27), (3, 0.72)):
        theo_no_overlap += prob * ((1 - k / 10) ** 3)
    overlap = np.array([
        len(set(digits[i]) & set(digits[i - 1])) > 0 for i in range(1, len(digits))
    ])
    hit = int(overlap.sum())
    p_any = 1 - theo_no_overlap
    pval = stats.binomtest(hit, n, p_any).pvalue
    print(f"  号码重号(本期数字集合与上期有交集)：观测 {hit}/{n} = {hit / n:.2%}，"
          f"理论 {p_any:.2%}，p={fmt_p(pval)} -> {verdict(pval)}")


def test_sum_distribution(digits):
    print("\n【3】和值分布")
    sums = digits.sum(axis=1)
    counts = np.bincount(sums, minlength=28)[:28]
    # 三位独立均匀的和值理论分布：卷积三重均匀分布
    theo = np.convolve(np.convolve(np.ones(10), np.ones(10)), np.ones(10)) / 1000.0
    theo = theo * len(sums)
    chi2, pval = stats.chisquare(counts[counts + theo > 0], theo[counts + theo > 0])
    print(f"  和值卡方: chi2={chi2:6.2f}  df={len(counts[theo > 0]) - 1}  p={fmt_p(pval)}  -> {verdict(pval)}")
    print(f"  观测均值 {sums.mean():.2f}（理论 13.50）标准差 {sums.std():.2f}（理论 {np.sqrt(3 * 8.25):.2f}）")

    print("\n【4】和值序列自相关")
    for lag in (1, 2, 3):
        r = np.corrcoef(sums[:-lag], sums[lag:])[0, 1]
        # Fisher z 检验近似
        z = np.arctanh(r) * np.sqrt(len(sums) - lag - 3)
        pval = 2 * (1 - stats.norm.cdf(abs(z)))
        print(f"  lag={lag}: r={r:+.4f}  p={fmt_p(pval)}  -> {verdict(pval)}")

    median = np.median(sums)
    runs = 1 + int((np.diff((sums > median).astype(int)) != 0).sum())
    n1 = int((sums > median).sum())
    n2 = int((sums <= median).sum())
    mu = 2 * n1 * n2 / (n1 + n2) + 1
    sd = np.sqrt(2 * n1 * n2 * (2 * n1 * n2 - n1 - n2) / ((n1 + n2) ** 2 * (n1 + n2 - 1)))
    z = (runs - mu) / sd
    pval = 2 * (1 - stats.norm.cdf(abs(z)))
    print(f"  游程检验(和值中位数上下): runs={runs} 期望{mu:.1f}  z={z:+.2f}  p={fmt_p(pval)}  -> {verdict(pval)}")


def test_between_positions(digits):
    print("\n【5】三位之间独立性（列联表卡方，H0: 位置间独立）")
    for a, b in ((0, 1), (0, 2), (1, 2)):
        table = np.zeros((10, 10), dtype=int)
        np.add.at(table, (digits[:, a], digits[:, b]), 1)
        chi2, pval, dof, _ = stats.chi2_contingency(table)
        print(f"  位置{a + 1} vs 位置{b + 1}: chi2={chi2:6.2f}  df={dof}  p={fmt_p(pval)}  -> {verdict(pval)}")


def test_segment_stability(digits, segments=5):
    print(f"\n【6】分段稳定性（切成 {segments} 段，检验热号是否漂移）")
    chunks = np.array_split(np.arange(len(digits)), segments)
    for p in range(3):
        table = np.stack([np.bincount(digits[c][:, p], minlength=10) for c in chunks])
        chi2, pval, dof, _ = stats.chi2_contingency(table)
        print(f"  位置{p + 1}: chi2={chi2:6.2f}  df={dof}  p={fmt_p(pval)}  -> {verdict(pval)}")
    # 全样本"最热数字"在每段中的排名漂移
    for p in range(3):
        hot_all = int(np.argmax(np.bincount(digits[:, p], minlength=10)))
        ranks = []
        for c in chunks:
            cnt = np.bincount(digits[c][:, p], minlength=10)
            order = sorted(range(10), key=lambda d: (-cnt[d], d))
            ranks.append(order.index(hot_all) + 1)
        print(f"  位置{p + 1} 全样本最热数字 {hot_all} 在 5 段中的排名: {ranks}")


def test_algorithm_significance(results, holdout, n_algo, alpha=0.05):
    print("\n【7】最优算法 vs 随机基线（Top-2 位置覆盖率）")
    baseline = 0.20
    n_trials = holdout * 3
    ranked = sorted(results.items(), key=lambda kv: kv[1]["top2PosRate"], reverse=True)
    print(f"  留出 {holdout} 期 -> {n_trials} 个位置样本；单算法 5% 显著性门槛约 "
          f"{baseline + 1.645 * np.sqrt(baseline * 0.8 / n_trials):.2%}")
    bonf = alpha / n_algo
    gate = baseline + stats.norm.ppf(1 - bonf) * np.sqrt(baseline * 0.8 / n_trials)
    print(f"  {n_algo} 个算法多重比较校正后门槛（Bonferroni, alpha={bonf:.4f}）：{gate:.2%}")
    for name, m in ranked[:4]:
        k = round(m["top2PosRate"] * n_trials)
        pval = stats.binomtest(k, n_trials, baseline, alternative="greater").pvalue
        mark = "  <= 通过校正门槛" if m["top2PosRate"] > gate else ""
        print(f"  {name:<22} {m['top2PosRate']:>6.2%}  p(单侧)={fmt_p(pval)}{mark}")

    print(f"  单期 Top-2 覆盖率的 95% 置信区间宽度约 ±2.3 个百分点，"
          f"意味着 22% 与 20% 的差距完全在抽样噪声内。")


def main():
    draws = load()
    digits = np.array([r["digits"] for r in draws], dtype=int)
    print(f"样本 {len(draws)} 期  {draws[0]['num']} ~ {draws[-1]['num']}\n")
    print("=" * 78)
    print("排列三随机性诊断（H0 = 开奖独立均匀，任何算法都无预测力）")
    print("=" * 78)

    test_positional_uniformity(digits)
    test_independence(digits)
    test_sum_distribution(digits)
    test_between_positions(digits)
    test_segment_stability(digits)

    model_path = os.path.join(DATA_DIR, "model.json")
    if os.path.exists(model_path):
        with open(model_path, encoding="utf-8") as fh:
            model = json.load(fh)
        results = {b["name"]: b for b in model["algorithmBenchmarks"]}
        test_algorithm_significance(results, model["backtest"]["holdoutSize"], len(results))


if __name__ == "__main__":
    main()
