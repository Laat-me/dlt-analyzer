# -*- coding: utf-8 -*-
"""
EVO-20 回测：1023 期 walk-forward 资金曲线 + 长视野蒙特卡洛 + 盈亏平衡分析
奖金口径：固定奖现行规则（精确结算），一等奖 500 万 / 二等奖 20 万（用户简化口径）。
诚实原则：不挑选窗口、不偷看未来、结果如实记录（结论预期为负 EV，见报告）。
"""
import json
import numpy as np
from evo20_model import (load_draws, build_portfolio, build_random_portfolio,
                         build_popular_portfolio, build_same_portfolio,
                         settle_draw, paijiang_boost, exact_portfolio_stats,
                         single_ticket_ev, EV_NORMAL, EV_PAIJIANG,
                         NTICKETS, BUDGET, PAIJIANG_BOOST)

WARMUP = 30
RESULT_FILE = "/Users/mac/dream/dlt-analyzer/evo20_result.json"

# ---------------------------------------------------------------- v1_cold 对照
def v1cold_tickets(draws, k):
    """SKILL.md 的 v1_cold 评分（追冷），生成 10 注（前区 top10 × 后区 top2）"""
    hist = draws[:k]
    T = len(hist)
    freq30F = np.zeros(35); freq30B = np.zeros(12)
    freqAllF = np.zeros(35); freqAllB = np.zeros(12)
    gapF = np.full(35, T); gapB = np.full(12, T)
    for i, d in enumerate(hist):
        for x in d["front"]:
            j = x - 1; freqAllF[j] += 1
            if i >= T - 30: freq30F[j] += 1
            gapF[j] = T - 1 - i
        for x in d["back"]:
            j = x - 1; freqAllB[j] += 1
            if i >= T - 30: freq30B[j] += 1
            gapB[j] = T - 1 - i
    sF = gapF * 0.5 + (5 - freq30F) * 2.5 + (T / 7 - freqAllF) * 0.3
    sB = gapB * 0.6 + (3 - freq30B) * 2.0
    topF = [tuple(sorted((np.argsort(-sF)[:5] + 1).tolist())) for _ in range(1)]
    # 取前 10 个不同的前区组合：贪心从高分往低分换入
    tickets, used = [], set()
    order = np.argsort(-sF)
    base = list(order[:5])
    for extra in range(10):
        f = base.copy()
        if extra > 0:                       # 逐个替换为第 6..15 名，制造 10 注不同组合
            f[extra % 5] = order[5 + extra - 1]
        ft = tuple(sorted(int(x) + 1 for x in f))
        bt = tuple(sorted((np.argsort(-sB)[:2] + 1).tolist()))
        if ft not in used:
            used.add(ft); tickets.append((ft, bt))
    while len(tickets) < NTICKETS:          # 兜底
        tickets.append((topF[0], tuple(sorted((np.argsort(-sB)[:2] + 1).tolist()))))
    return tickets[:NTICKETS]

# ---------------------------------------------------------------- 主回测
def run_backtest():
    draws = load_draws()
    n = len(draws)
    designs = ["EVO-20", "random10", "same10", "popular10", "v1cold10"]
    curves = {d: [0.0] for d in designs}
    stats = {d: {"staked": 0, "fixed": 0.0, "floating": 0.0, "win_periods": 0,
                 "breakeven_periods": 0, "max_single": 0.0, "zero_streak": 0,
                 "max_zero_streak": 0, "tiers": {}, "paijiang_return": [],
                 "normal_return": []} for d in designs}
    fixed_rng = np.random.default_rng(42)
    same_tickets = build_same_portfolio(fixed_rng)

    for k in range(WARMUP, n):
        d = draws[k]
        boost = paijiang_boost(d["num"])
        rng = np.random.default_rng(k)
        portfolios = {
            "EVO-20": build_portfolio(draws, k, rng),
            "random10": build_random_portfolio(rng),
            "same10": same_tickets,
            "popular10": build_popular_portfolio(rng),
            "v1cold10": v1cold_tickets(draws, k),
        }
        for name, tks in portfolios.items():
            fixed, floating, events = settle_draw(d, tks, boost)
            st = stats[name]
            st["staked"] += BUDGET
            st["fixed"] += fixed
            st["floating"] += floating
            ret = fixed + floating
            if ret > 0: st["win_periods"] += 1; st["zero_streak"] = 0
            else: st["zero_streak"] += 1; st["max_zero_streak"] = max(st["max_zero_streak"], st["zero_streak"])
            if ret >= BUDGET: st["breakeven_periods"] += 1
            st["max_single"] = max(st["max_single"], ret)
            for e in events:
                st["tiers"][e["tier"]] = st["tiers"].get(e["tier"], 0) + 1
            (st["paijiang_return"] if boost else st["normal_return"]).append(ret)
            curves[name].append(curves[name][-1] + ret - BUDGET)

    summary = {}
    for name in designs:
        st = stats[name]
        curve = np.array(curves[name])
        peak = np.maximum.accumulate(curve)
        dd = peak - curve
        summary[name] = {
            "staked": st["staked"],
            "fixed_return": round(st["fixed"], 2),
            "floating_return": round(st["floating"], 2),
            "total_return": round(st["fixed"] + st["floating"], 2),
            "net": round(curve[-1], 2),
            "roi_pct": round(curve[-1] / st["staked"] * 100, 2),
            "win_periods": st["win_periods"],
            "breakeven_periods": st["breakeven_periods"],
            "n_periods": n - WARMUP,
            "max_single_win": st["max_single"],
            "max_zero_streak": st["max_zero_streak"],
            "max_drawdown": round(float(dd.max()), 2),
            "tier_hits": st["tiers"],
            "avg_return_paijiang": round(float(np.mean(st["paijiang_return"])), 2) if st["paijiang_return"] else None,
            "avg_return_normal": round(float(np.mean(st["normal_return"])), 2),
            "n_paijiang_periods": len(st["paijiang_return"]),
        }
    return summary, {d: curves[d] for d in designs}, n

# ---------------------------------------------------------------- 精确分布（用于蒙特卡洛）
def exact_value_counts(tickets, boost=None):
    """返回 {奖金额: 开奖组合数} —— 21,425,712 种开奖的精确奖金分布"""
    from evo20_model import prize_matrix, _ticket_hits, C35_5, C12_2
    P = prize_matrix(boost)
    total = np.zeros((C35_5, C12_2), dtype=np.float64)
    for ti in tickets:
        hF, hB = _ticket_hits(ti)
        total += P[np.ix_(hF.astype(np.int64), hB.astype(np.int64))]
    vals, counts = np.unique(total, return_counts=True)
    return {float(v): int(c) for v, c in zip(vals, counts)}

def monte_carlo(dist_normal, dist_boost, p_boost, horizons, n_paths=100_000, seed=0, chunk=5000):
    """长视野模拟：每期奖金从精确分布抽样，统计长期盈利概率（分块防内存爆炸）"""
    rng = np.random.default_rng(seed)
    def make_sampler(dist):
        vals = np.array(list(dist.keys()), dtype=np.float64)
        probs = np.array(list(dist.values()), dtype=np.float64)
        probs /= probs.sum()
        return vals, probs
    vn, pn = make_sampler(dist_normal)
    vb, pb = make_sampler(dist_boost)
    out = {}
    for H in horizons:
        nets_all, ever_all, done = [], [], 0
        while done < n_paths:
            m = min(chunk, n_paths - done)
            is_boost = rng.random((m, H)) < p_boost
            dn = vn[rng.choice(len(vn), (m, H), p=pn)]
            db = vb[rng.choice(len(vb), (m, H), p=pb)]
            prizes = np.where(is_boost, db, dn)
            cum_net = np.cumsum(prizes, axis=1) - BUDGET * np.arange(1, H + 1)
            nets_all.append(cum_net[:, -1])
            ever_all.append(cum_net.max(axis=1) > 0)
            done += m
        nets = np.concatenate(nets_all)
        ever = np.concatenate(ever_all)
        out[H] = {
            "p_final_profit": round(float((nets > 0).mean()), 5),
            "p_ever_profit": round(float(ever.mean()), 5),
            "net_median": round(float(np.median(nets)), 0),
            "net_p5": round(float(np.percentile(nets, 5)), 0),
            "net_p95": round(float(np.percentile(nets, 95)), 0),
        }
    return out

def breakeven_analysis():
    """在 500万/20万 简化口径下，达到 EV=2.0 元/票（保本）所需的条件"""
    p1 = 1 / 21425712
    p2 = 20 / 21425712
    ev_fixed = EV_NORMAL - p1 * 5_000_000 - p2 * 200_000     # 固定奖 EV 部分
    need = 2.0 - ev_fixed                                     # 浮动奖需要贡献的 EV
    jp_need = need - p2 * 200_000                             # 全部压给一等奖
    return {
        "fixed_ev": round(ev_fixed, 4),
        "floating_ev_now": round(p1 * 5_000_000 + p2 * 200_000, 4),
        "ev_now": round(EV_NORMAL, 4),
        "return_rate_now_pct": round(EV_NORMAL / 2 * 100, 1),
        "jackpot_needed_yuan": round(jp_need / p1, 0),        # 仅提一等奖所需的单注奖金
        "jackpot_needed_vs_assumed": round(jp_need / p1 / 5_000_000, 2),
        "fixed_boost_needed": round(2.0 / ev_fixed, 2),        # 仅提固定奖所需的倍数
        "paijiang_always_ev": round(EV_PAIJIANG, 4),           # 派奖常开的回报率
        "paijiang_always_rate_pct": round(EV_PAIJIANG / 2 * 100, 1),
    }

if __name__ == "__main__":
    print("=== EVO-20 回测（1023 期 walk-forward，奖金口径: 一等500万/二等20万）===")
    summary, curves, n = run_backtest()
    for name, s in summary.items():
        print(f"\n[{name}]")
        for k, v in s.items():
            print(f"  {k}: {v}")

    # 精确分布 + 蒙特卡洛（用 EVO-20 与 same10 两个代表）
    draws = load_draws()
    rng = np.random.default_rng(int(draws[-1]["num"]) + 1)
    evo_tk = build_portfolio(draws, len(draws), rng)
    same_tk = build_same_portfolio(np.random.default_rng(42))
    n_paijiang = sum(1 for d in draws if paijiang_boost(d["num"]) is not None)
    p_boost = n_paijiang / len(draws)
    print(f"\n派奖期占比（历史 1023 期）: {p_boost:.1%}")

    mc = {}
    for label, tks in [("EVO-20", evo_tk), ("same10", same_tk)]:
        dn = exact_value_counts(tks, None)
        db = exact_value_counts(tks, PAIJIANG_BOOST)
        mc[label] = monte_carlo(dn, db, p_boost, horizons=[156, 780, 1560])
        print(f"\n[{label}] 长视野蒙特卡洛（10 万路径）:")
        for H, r in mc[label].items():
            print(f"  {H}期({H/156:.0f}年): {r}")

    be = breakeven_analysis()
    print("\n[盈亏平衡分析]")
    for k, v in be.items():
        print(f"  {k}: {v}")

    json.dump({
        "prize_assumption": {"jackpot": 5_000_000, "second": 200_000,
                             "fixed": {3: 10000, 4: 3000, 5: 300, 6: 200, 7: 100, 8: 15, 9: 5}},
        "ev_single": {"normal": round(EV_NORMAL, 4), "paijiang": round(EV_PAIJIANG, 4)},
        "p_paijiang_hist": round(p_boost, 4),
        "backtest": summary,
        "monte_carlo": mc,
        "breakeven": be,
    }, open(RESULT_FILE, "w"), ensure_ascii=False, indent=1)
    print(f"\nsaved -> {RESULT_FILE}")
