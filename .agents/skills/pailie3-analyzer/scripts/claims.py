# -*- coding: utf-8 -*-
"""民间公式真伪验证器。

网上流传的排列三「杀号/定胆」公式大多带有明确的准确率宣称（「准确率98%以上」、
「成功率80%以上」）。这些是可证伪的断言，直接在 1000 期真实数据上验证。

三类断言：
  A. 杀号类：预测「某位不会出现数字 k」。成功 = 实际该位 != k
     基线 = 1 - 该位该数字的经验频率（用全样本估计，即「什么都不做」的期望）
  B. 定胆类：预测「这几个数字里至少出一个」。成功 = 与实际 3 位有交集
     基线 = 1 - ((10-k)/10)^3
  C. 结构性：如「每期至少一个 0 路号码」

另加 D 段：用户提出的具体假设（10 期重号 / 邻码 / 连号 / 遗漏回归）。
"""
import json
import os

import numpy as np
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.normpath(os.path.join(HERE, "..", "data"))
DRAWS_PATH = os.path.join(DATA_DIR, "draws.json")


def load():
    with open(DRAWS_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def fmt_p(p):
    return f"{p:.2e}" if p < 1e-4 else f"{p:.4f}"


def pct(x):
    return f"{x * 100:.2f}%"


def as_num(digits):
    return int("".join(str(d) for d in digits))


def verdict(pval, alpha=0.05):
    return "显著偏离随机" if pval < alpha else "无显著偏离（与随机一致）"


def verdict_better(pval, alpha=0.05):
    return "显著优于基线" if pval < alpha else "与瞎猜无差别"


# ------------------------------------------------------------------ A 杀号类
# 每个函数: (draws, i) -> (位置, 被杀数字)

def kill_123_bai(draws, i):
    """123百位杀号法：上期开奖号 ×123，取第一位数字杀下期百位。"""
    prod = as_num(draws[i - 1]["digits"]) * 123
    return 0, int(str(prod)[0])


def kill_sumtail_plus4_ge(draws, i):
    """和值尾 +4，杀个位。"""
    return 2, (sum(draws[i - 1]["digits"]) + 4) % 10


def kill_prev_shi_ge(draws, i):
    """上期十位杀本期个位。"""
    return 2, draws[i - 1]["digits"][1]


def kill_prev_sumtail_bai(draws, i):
    """上期和值尾杀本期百位。"""
    return 0, sum(draws[i - 1]["digits"]) % 10


def kill_prev_bai_shi(draws, i):
    """上期百位杀本期十位。"""
    return 1, draws[i - 1]["digits"][0]


KILL_CLAIMS = {
    "123百位杀号法": kill_123_bai,
    "和值尾+4杀个位": kill_sumtail_plus4_ge,
    "上期十位杀本期个位": kill_prev_shi_ge,
    "上期和值尾杀本期百位": kill_prev_sumtail_bai,
    "上期百位杀本期十位": kill_prev_bai_shi,
}


# ------------------------------------------------------------------ B 定胆类
# 每个函数: (draws, i) -> 候选数字列表（宣称其中至少一个会开出）

def dart_golden(draws, i):
    """黄金定胆：上期开奖号 ×0.618，取前三位数字作胆。"""
    n = int(as_num(draws[i - 1]["digits"]) * 0.618)
    return [int(c) for c in str(n)[:3]]


def dart_pi(draws, i):
    """圆周率测胆：上期开奖号 ×3.14，取前三位。"""
    n = int(as_num(draws[i - 1]["digits"]) * 3.14)
    return [int(c) for c in str(n)[:3]]


def dart_sub10(draws, i):
    """减法定胆：10 减上期各位。"""
    return [(10 - d) % 10 for d in draws[i - 1]["digits"]]


def dart_plus3(draws, i):
    """上期号码加 3 定胆。"""
    return [(d + 3) % 10 for d in draws[i - 1]["digits"]]


def dart_sumtail_neighbor(draws, i):
    """和值尾邻码法：上期和值尾 ±1 作胆。"""
    t = sum(draws[i - 1]["digits"]) % 10
    return [(t - 1) % 10, (t + 1) % 10]


def dart_prev_repeat(draws, i):
    """直落号：上期三个数字原样作胆。"""
    return list(set(draws[i - 1]["digits"]))


DART_CLAIMS = {
    "黄金定胆 ×0.618": (dart_golden, "98%+"),
    "圆周率测胆 ×3.14": (dart_pi, "—"),
    "减法定胆 10-上期各位": (dart_sub10, "—"),
    "上期号码+3 定胆": (dart_plus3, "65%"),
    "和值尾邻码 和尾±1": (dart_sumtail_neighbor, "—"),
    "直落号 上期三码": (dart_prev_repeat, "—"),
}


def run_kill_claims(draws):
    print(A_SECTION)
    print(f"  {'公式':<26}{'实际':>9}{'基线':>9}{'p值':>11}  结论")
    print("  " + "-" * 68)

    empirical = np.array([r["digits"] for r in draws])
    n = len(draws)
    for label, fn in KILL_CLAIMS.items():
        hits, base_hits, trials = 0, 0.0, 0
        for i in range(1, n):
            pos, k = fn(draws, i)
            hits += int(draws[i]["digits"][pos] != k)
            freq = float((empirical[:, pos] == k).mean())
            base_hits += 1 - freq
            trials += 1
        rate, base = hits / trials, base_hits / trials
        pval = stats.binomtest(hits, trials, base, alternative="greater").pvalue
        print(f"  {label:<26}{pct(rate):>9}{pct(base):>9}{fmt_p(pval):>11}  {verdict_better(pval)}")

    print("  说明：杀一位数字的理论正确率本来就是 90%（10 个数字杀 1 个）。")
    print("        所以宣称「准确率80%以上」「连续命中」在这类公式上没有任何信息量。")


def run_dart_claims(draws):
    print(B_SECTION)
    print(f"  {'公式':<26}{'宣称':>8}{'实际':>9}{'基线':>9}{'p值':>11}  结论")
    print("  " + "-" * 76)

    n = len(draws)
    for label, (fn, claimed) in DART_CLAIMS.items():
        hits, base_hits, trials = 0, 0.0, 0
        for i in range(1, n):
            cand = set(fn(draws, i))
            if not cand:
                continue
            hits += int(len(cand & set(draws[i]["digits"])) > 0)
            base_hits += 1 - ((10 - len(cand)) / 10) ** 3
            trials += 1
        rate, base = hits / trials, base_hits / trials
        pval = stats.binomtest(hits, trials, base, alternative="greater").pvalue
        print(f"  {label:<26}{claimed:>8}{pct(rate):>9}{pct(base):>9}{fmt_p(pval):>11}  {verdict_better(pval)}")

    print("  说明：取 3 个数字、宣称「至少出一个」，理论基线本来就接近 66%。")
    print("        听上去很高的准确率，其实是白送的。")


def run_structural(draws):
    print(C_SECTION)
    digits = np.array([r["digits"] for r in draws])
    n = len(digits)
    all_t = np.array(np.meshgrid(range(10), range(10), range(10))).reshape(3, -1).T

    # 012 路：0路={0,3,6,9} 1路={1,4,7} 2路={2,5,8}
    both = np.array([any(d % 3 == 0 for d in row) and any(d % 3 != 0 for d in row) for row in digits])
    theo = 1 - (4 / 10) ** 3 - (6 / 10) ** 3
    pval = stats.binomtest(int(both.sum()), n, theo).pvalue
    print(f"  012路「至少一个0路且至少一个非0路」")
    print(f"    观测 {pct(both.mean())}  理论 {pct(theo)}  p={fmt_p(pval)}  -> {verdict(pval)}")
    print("    （宣称「成功率80%以上」，但这个组合本来就占 {0}，是统计必然）".format(pct(theo)))

    # 跨度
    spans = digits.max(axis=1) - digits.min(axis=1)
    sp_all = all_t.max(axis=1) - all_t.min(axis=1)
    theo_range = float(((sp_all >= 3) & (sp_all <= 8)).mean())
    in_range = (spans >= 3) & (spans <= 8)
    pval = stats.binomtest(int(in_range.sum()), n, theo_range).pvalue
    print(f"  跨度「高概率落在 3~8」")
    print(f"    观测 {pct(in_range.mean())}  理论 {pct(theo_range)}  p={fmt_p(pval)}  -> {verdict(pval)}")
    print(f"    （理论值本身就是 {pct(theo_range)}）")
    # 跨度本身不是均匀分布（跨度0只占1%，跨度9占6%），必须跟理论跨度分布比
    theo_cnt = np.bincount(sp_all, minlength=10) / len(sp_all) * n
    keep = theo_cnt > 0
    chi2, pv = stats.chisquare(np.bincount(spans, minlength=10)[keep], theo_cnt[keep])
    print(f"    跨度分布 vs 理论分布: chi2={chi2:.2f}  df={int(keep.sum()) - 1}  p={fmt_p(pv)}"
          f"  -> {verdict(pv)}")
    print("    （注意：不能跟均匀分布比，跨度天然不是均匀的）")

    # 形态
    forms = np.array([len(set(r)) for r in digits])
    bao, zu3, zu6 = int((forms == 1).sum()), int((forms == 2).sum()), int((forms == 3).sum())
    print(f"  形态分布")
    print(f"    豹子 {bao} ({pct(bao / n)}，理论1.00%)  "
          f"组三 {zu3} ({pct(zu3 / n)}，理论27.00%)  组六 {zu6} ({pct(zu6 / n)}，理论72.00%)")
    pv = stats.chisquare([bao, zu3, zu6], [n * 0.01, n * 0.27, n * 0.72]).pvalue
    print(f"    形态卡方 p={fmt_p(pv)}  -> {verdict(pv)}")


def run_user_hypotheses(draws):
    print(D_SECTION)
    digits = np.array([r["digits"] for r in draws])
    n = len(digits)

    def pooled(label, cand_fn, window):
        hits, exp, var, trials = 0, 0.0, 0.0, 0
        for i in range(window, n):
            cand = cand_fn(digits[max(0, i - window):i])
            k = len(cand)
            if k == 0:
                continue
            for d in digits[i]:
                hits += int(d in cand)
                exp += k / 10
                var += (k / 10) * (1 - k / 10)
            trials += 3
        z = (hits - exp) / np.sqrt(var)
        pval = 2 * (1 - stats.norm.cdf(abs(z)))
        print(f"  {label}")
        print(f"    落入 {hits} 次 / 期望 {exp:.1f} 次   比例 {pct(hits / trials)} vs 基线 {pct(exp / trials)}")
        print(f"    z={z:+.2f}  p={fmt_p(pval)}  -> {verdict(pval)}")

    pooled("假设1：近10期出现过的数字（热号/重号）更容易开出",
           lambda h: {int(d) for row in h for d in row}, 10)
    pooled("假设1b：近20期出现过的数字（对照组）",
           lambda h: {int(d) for row in h for d in row}, 20)
    pooled("假设2：上期数字的邻码（±1）更容易开出",
           lambda h: {(int(d) + 1) % 10 for d in h[-1]} | {(int(d) - 1) % 10 for d in h[-1]}, 1)
    pooled("假设3：近10期未出现的冷号更容易开出（遗漏回归）",
           lambda h: set(range(10)) - {int(d) for row in h for d in row}, 10)
    pooled("假设4：上期同位数字直接延续（同位重号）",
           lambda h: {int(d) for d in h[-1]}, 1)

    has_consec = np.array([any((a + 1) in set(row) for a in set(row)) for row in digits])
    all_t = np.array(np.meshgrid(range(10), range(10), range(10))).reshape(3, -1).T
    theo_c = float(np.mean([any((a + 1) in set(row) for a in set(row)) for row in all_t]))
    pv = stats.binomtest(int(has_consec.sum()), n, theo_c).pvalue
    print("  假设5：本期包含连号（相邻数字对）")
    print(f"    观测 {pct(has_consec.mean())}  理论 {pct(theo_c)}  p={fmt_p(pv)}  -> {verdict(pv)}")


A_SECTION = ('【A】杀号类公式验证（成功 = 预测「该位不会出现此数字」，'
             '碰巧正确率基线约 90%）')
B_SECTION = '【B】定胆类公式验证（成功 = 这几个数字里至少开出一个）'
C_SECTION = '【C】结构性断言验证'
D_SECTION = '【D】具体假设检验（用户提出的重号 / 邻码 / 连号 / 遗漏回归）'


def main():
    draws = load()
    print("=" * 92)
    print(f"民间公式真伪验证  |  样本 {len(draws)} 期  {draws[0]['num']} ~ {draws[-1]['num']}")
    print("=" * 92)
    run_kill_claims(draws)
    print()
    run_dart_claims(draws)
    print()
    run_structural(draws)
    print()
    run_user_hypotheses(draws)


if __name__ == "__main__":
    main()
