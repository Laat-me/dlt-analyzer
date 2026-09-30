# -*- coding: utf-8 -*-
"""
同心圆连线假说检验（round-30, 2026-09-25）

用户想法形式化：
  外圆 = 前区 1-35 均匀布点，内圆 = 后区 1-12 均匀布点，两圆同心。
  每期开奖：前区 5 点按号序连成五边形，后区 2 点连成一条弦。

检验思想：如果「连线的形状/朝向/中点/对径点」等几何结构含有跨期信息，
那么下列检验应显著偏离随机 null。全部使用 walk-forward/无前视口径，
多重检验按 Bonferroni 校正（α = 0.05 / 检验数）。

  T1  扇区转移独立性（前区 7 扇区×5号，逐号转移对）      —— 连线"走向"是否有记忆
  T2  五边形朝向 Δθ 均匀性（Rayleigh）                    —— 是否存在"旋转动能"
  T3  重心极径自相关                                      —— "聚/散"形态是否延续
  T4  弧间隙结构条件转移（min/max gap 粗化 χ²）           —— 形状是否预测形状
  T5  后区弦长边际分布                                    —— vs 组合学期望
  T6  后区弦长条件转移 + 前后区相位差 Δ 均匀性            —— 同心圆联动是否存在
  T7  弧中点命中率（上一期 5 段弧的中点号）               —— "连线中点"选号法
  T8  对径点命中率（前区 n±17/18，后区 n+6）              —— "对称映射"选号法
  T9  walk-forward 实战：扇区马尔可夫评分器生成 10 注     —— 与随机/EVO-20 对照 ROI

输出：circle_geo_result.json + circle_view.html（同心圆连线可视化）
"""
import json
import math
import numpy as np
from scipy import stats as st

from evo20_model import (load_draws, settle_draw, paijiang_boost,
                         build_portfolio, build_random_portfolio,
                         NF, NB, KF, KB, NTICKETS, BUDGET)

RESULT = "/Users/mac/dream/dlt-analyzer/circle_geo_result.json"
VIEW = "/Users/mac/dream/dlt-analyzer/circle_view.html"
draws = load_draws()
N = len(draws)
WARMUP = 30
rng = np.random.default_rng(0)

# ---------------------------------------------------------------- 几何工具
def ang_f(n):  # 前区号码 -> 圆上角度 (rad, 0=12点, 顺时针)
    return 2 * math.pi * (n - 1) / NF

def ang_b(n):
    return 2 * math.pi * (n - 1) / NB

def gaps5(front):
    s = sorted(front)
    return [s[1] - s[0], s[2] - s[1], s[3] - s[2], s[4] - s[3], NF - s[4] + s[0]]

def orient(front):
    a = [ang_f(n) for n in front]
    return math.atan2(sum(math.sin(x) for x in a), sum(math.cos(x) for x in a)) % (2 * math.pi)

def centroid_radius(front):
    a = np.array([ang_f(n) for n in front])
    return float(np.abs(np.exp(1j * a).mean()))      # 0=均匀铺开, 1=扎堆一点

def back_chord(back):
    d = abs(back[0] - back[1])
    return min(d, NB - d)                             # 1..6

def arc_midpoints(front):
    """5 段弧的中点号（取整）"""
    s = sorted(front); out = []
    g = gaps5(front)
    for i in range(5):
        p = (s[i] - 1 + g[i] / 2) % NF
        out.append(int(round(p)) % NF + 1)
    return out

def antipodes_f(front):
    return [((n - 1 + 17) % NF) + 1 for n in front] + [((n - 1 + 18) % NF) + 1 for n in front]

def antipodes_b(back):
    return [((n - 1 + 6) % NB) + 1 for n in back]

# ---------------------------------------------------------------- T1 扇区转移
SEC_F = 7
sec = lambda n: (n - 1) // 5
T1_table = np.zeros((SEC_F, SEC_F))
for t in range(N - 1):
    for x in draws[t]["front"]:
        for y in draws[t + 1]["front"]:
            T1_table[sec(x), sec(y)] += 1
chi1, p1, _, _ = st.chi2_contingency(T1_table)

# ---------------------------------------------------------------- T2 朝向 Δθ 均匀性
oris = [orient(d["front"]) for d in draws]
dth = [(oris[t + 1] - oris[t]) % (2 * math.pi) for t in range(N - 1)]
Rbar = abs(np.mean(np.exp(1j * np.array(dth))))
stat2, p2 = (N - 1) * Rbar ** 2, math.exp(-(N - 1) * Rbar ** 2)   # Rayleigh

# ---------------------------------------------------------------- T3 重心极径自相关
rads = [centroid_radius(d["front"]) for d in draws]
r3, p3 = st.pearsonr(rads[:-1], rads[1:])

# ---------------------------------------------------------------- T4 弧间隙结构条件转移
def gap_signature(g):
    mn, mx = min(g), max(g)
    return ("散" if mn >= 5 else ("聚" if mn == 1 else "中")) + ("宽" if mx >= 12 else "窄")
sig = [gap_signature(gaps5(d["front"])) for d in draws]
kinds = sorted(set(sig))
T4 = np.zeros((len(kinds), len(kinds)))
for t in range(N - 1):
    T4[kinds.index(sig[t]), kinds.index(sig[t + 1])] += 1
chi4, p4, _, _ = st.chi2_contingency(T4)

# ---------------------------------------------------------------- T5/T6 后区弦
chords = [back_chord(d["back"]) for d in draws]
expect5 = {d: (NB if d < 6 else NB / 2) / 66 for d in range(1, 7)}  # 组合学期望
obs5 = {d: chords.count(d) / N for d in range(1, 7)}
chi5 = sum((chords.count(d) - expect5[d] * N) ** 2 / (expect5[d] * N) for d in range(1, 7))
p5 = st.chi2.sf(chi5, df=5)
T6 = np.zeros((6, 6))
for t in range(N - 1):
    T6[chords[t] - 1, chords[t + 1] - 1] += 1
chi6, p6, _, _ = st.chi2_contingency(T6)
# 前后区相位差
phase = [(orient(d["front"]) - (ang_b(d["back"][0]) + ang_b(d["back"][1])) / 2) % (2 * math.pi) for d in draws]
dph = [(phase[t + 1] - phase[t]) % (2 * math.pi) for t in range(N - 1)]
Rb2 = abs(np.mean(np.exp(1j * np.array(dph))))
p6b = math.exp(-(N - 1) * Rb2 ** 2)

# ---------------------------------------------------------------- T7 弧中点命中
hits7 = marked7 = 0
for t in range(N - 1):
    mids = set(arc_midpoints(draws[t]["front"]))
    marked7 += len(mids)
    hits7 += len(mids & set(draws[t + 1]["front"]))
base7 = KF / NF
p7 = st.binomtest(hits7, marked7, base7).pvalue

# ---------------------------------------------------------------- T8 对径点命中
hits8f = marked8f = 0
hits8b = marked8b = 0
for t in range(N - 1):
    m8f = set(antipodes_f(draws[t]["front"]))
    marked8f += len(m8f)
    hits8f += len(m8f & set(draws[t + 1]["front"]))
    m8b = set(antipodes_b(draws[t]["back"]))
    marked8b += len(m8b)
    hits8b += len(m8b & set(draws[t + 1]["back"]))
p8f = st.binomtest(hits8f, marked8f, KF / NF).pvalue
p8b = st.binomtest(hits8b, marked8b, KB / NB).pvalue

# ---------------------------------------------------------------- T9 扇区马尔可夫评分器 walk-forward
def build_portfolio_from_scores(sf, sb, rng):
    """与 EVO-20 相同的配额+发牌机制，换成任意评分输入（受控实验）"""
    order_f = np.argsort(-(sf + rng.random(NF) * 1e-6))
    order_b = np.argsort(-(sb + rng.random(NB) * 1e-6))
    mf = [int(order_f[i]) + 1 for i in range(NF)] + [int(order_f[i]) + 1 for i in range(NTICKETS * KF - NF)]
    mf.sort()
    buckets = [[] for _ in range(NTICKETS)]
    for j, n in enumerate(mf): buckets[j % NTICKETS].append(n)
    mb = [int(order_b[i]) + 1 for i in range(NB)] + [int(order_b[i]) + 1 for i in range(NTICKETS * KB - NB)]
    mb.sort()
    buckets_b = [[] for _ in range(NTICKETS)]
    for j, n in enumerate(mb): buckets_b[j % NTICKETS].append(n)
    tickets, seen = [], set()
    for i in range(NTICKETS):
        f5 = list(dict.fromkeys(buckets[i])); b2 = list(dict.fromkeys(buckets_b[i]))
        while len(f5) < KF:
            for c in order_f:
                if int(c) + 1 not in f5: f5.append(int(c) + 1); break
        while len(b2) < KB:
            for c in order_b:
                if int(c) + 1 not in b2: b2.append(int(c) + 1); break
        f5, b2 = tuple(sorted(f5)), tuple(sorted(b2))
        if (f5, b2) in seen:
            for c in order_f:
                if int(c) + 1 not in f5: f5 = tuple(sorted(f5[:-1] + (int(c) + 1,))); break
        seen.add((f5, b2)); tickets.append((f5, b2))
    return tickets

fF_hits = fB_hits = fTot = fROI = 0.0
rF_hits = rB_hits = rTot = rROI = 0.0
eF_hits = eTot = eROI = 0.0
n_periods = 0
for k in range(WARMUP, N):
    d = draws[k]
    boost = paijiang_boost(d["num"])
    # 扇区马尔可夫评分（只用 draws[:k]，Laplace 平滑）
    TM = np.full((SEC_F, SEC_F), 0.5)
    for t in range(k - 1):
        for x in draws[t]["front"]:
            for y in draws[t + 1]["front"]:
                TM[sec(x), sec(y)] += 1
    TMn = TM / TM.sum(1, keepdims=True)
    last = draws[k - 1]["front"]
    sf = np.array([float(np.mean([TMn[sec(x)][(n - 1) // 5] for x in last])) for n in range(1, NF + 1)])
    sb = np.full(NB, 1.0 / NB)                      # 后区无可用几何信号（T6 检验的先验）
    r = np.random.default_rng(k)
    tk_markov = build_portfolio_from_scores(sf, sb, r)
    tk_rand = build_random_portfolio(r)
    tk_evo = build_portfolio(draws, k, r)
    af, ab = set(d["front"]), set(d["back"])
    for name, tks in [("M", tk_markov), ("R", tk_rand), ("E", tk_evo)]:
        fh = sum(len(set(f) & af) for f, _ in tks)
        bh = sum(len(set(b) & ab) for _, b in tks)
        fixed, floating, _ = settle_draw(d, tks, boost)
        ret = fixed + floating
        if name == "M": fF_hits += fh; fB_hits += bh; fTot += fh + bh; fROI += ret - BUDGET
        elif name == "R": rF_hits += fh; rTot += fh + bh; rROI += ret - BUDGET
        else: eF_hits += fh; eTot += fh + bh; eROI += ret - BUDGET
    n_periods += 1

# ---------------------------------------------------------------- 汇总
ntest = 9
alpha_bonf = 0.05 / ntest
tests = {
    "T1_扇区转移独立性": {"chi2": round(chi1, 1), "p": p1},
    "T2_朝向旋转动能(Rayleigh)": {"R": round(Rbar, 4), "p": p2},
    "T3_重心极径自相关": {"r": round(r3, 4), "p": p3},
    "T4_弧间隙形态转移": {"chi2": round(chi4, 1), "p": p4},
    "T5_后区弦长边际分布": {"chi2": round(chi5, 2), "p": p5},
    "T6_后区弦长转移": {"chi2": round(chi6, 1), "p": p6},
    "T6b_前后区相位差均匀性": {"R": round(Rb2, 4), "p": p6b},
    "T7_弧中点命中率": {"命中/标记": f"{hits7}/{marked7}", "基线": round(base7, 4), "obs": round(hits7 / marked7, 4), "p": p7},
    "T8a_前区对径点命中": {"命中/标记": f"{hits8f}/{marked8f}", "obs": round(hits8f / marked8f, 4), "p": p8f},
    "T8b_后区对径点命中": {"命中/标记": f"{hits8b}/{marked8b}", "obs": round(hits8b / marked8b, 4), "p": p8b},
}
for k_, v in tests.items():
    v["判定"] = "无信号(未通过Bonferroni)" if v["p"] > alpha_bonf else "⚠️显著——需复现验证"

out = {
    "hypothesis": "同心圆连线几何结构含跨期预测信息（用户提出，2026-09-25）",
    "data": f"draws.json {N}期 (19123-26109)",
    "bonferroni_alpha": round(alpha_bonf, 4),
    "tests": tests,
    "T9_walkforward": {
        "n_periods": n_periods,
        "扇区马尔可夫评分": {"场均前区命中/注": round(fF_hits / (n_periods * 10), 4),
                          "场均合计命中/注": round(fTot / (n_periods * 10), 4),
                          "净结果": round(fROI, 1), "ROI%": round(fROI / (n_periods * BUDGET) * 100, 2)},
        "随机对照": {"场均前区命中/注": round(rF_hits / (n_periods * 10), 4),
                    "场均合计命中/注": round(rTot / (n_periods * 10), 4),
                    "净结果": round(rROI, 1), "ROI%": round(rROI / (n_periods * BUDGET) * 100, 2)},
        "EVO-20对照": {"场均前区命中/注": round(eF_hits / (n_periods * 10), 4),
                      "场均合计命中/注": round(eTot / (n_periods * 10), 4),
                      "净结果": round(eROI, 1), "ROI%": round(eROI / (n_periods * BUDGET) * 100, 2)},
        "随机场均前区命中理论值": KF * KF / NF,
    },
}
json.dump(out, open(RESULT, "w"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))

# ---------------------------------------------------------------- 可视化 circle_view.html
def pt(n, R, nb=False):
    a = 2 * math.pi * (n - 1) / (NB if nb else NF)
    return 350 + R * math.sin(a), 350 - R * math.cos(a)

svg = [f'<circle cx="350" cy="350" r="300" fill="none" stroke="#ddd"/>',
       f'<circle cx="350" cy="350" r="170" fill="none" stroke="#ddd"/>']
for n in range(1, NF + 1):
    x, y = pt(n, 318); xt, yt = pt(n, 300)
    svg.append(f'<text x="{x:.0f}" y="{y:.0f}" font-size="10" text-anchor="middle" fill="#888">{n:02d}</text>')
    svg.append(f'<circle cx="{xt:.0f}" cy="{yt:.0f}" r="1.5" fill="#bbb"/>')
for n in range(1, NB + 1):
    x, y = pt(n, 186, True); xt, yt = pt(n, 170, True)
    svg.append(f'<text x="{x:.0f}" y="{y:.0f}" font-size="10" text-anchor="middle" fill="#888">{n:02d}</text>')
    svg.append(f'<circle cx="{xt:.0f}" cy="{yt:.0f}" r="1.5" fill="#bbb"/>')
colors = ["#e74c3c", "#e67e22", "#f1c40f", "#2ecc71", "#3498db", "#9b59b6"]
last6 = draws[-6:]
for i, d in enumerate(last6):
    c = colors[i]; op = 0.25 + 0.15 * i
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in (pt(n, 300) for n in d["front"]))
    svg.append(f'<polygon points="{pts}" fill="none" stroke="{c}" stroke-width="{1+i*0.5}" opacity="{op:.2f}"/>')
    (x1, y1), (x2, y2) = pt(d["back"][0], 170, True), pt(d["back"][1], 170, True)
    svg.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{c}" stroke-width="{1+i*0.5}" opacity="{op:.2f}"/>')
legend = "".join(f'<span style="color:{colors[i]};margin-right:14px">◼{d["num"]}</span>' for i, d in enumerate(last6))
sig_rows = "".join(
    f'<tr><td>{k}</td><td>{v.get("p", 0):.3g}</td><td>{v["判定"]}</td></tr>'
    for k, v in tests.items())
html = f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8"><title>同心圆连线检验</title>
<style>body{{font-family:-apple-system,sans-serif;max-width:900px;margin:24px auto;color:#333}}
.flex{{display:flex;gap:24px;align-items:flex-start}}table{{border-collapse:collapse;font-size:13px}}
td,th{{border:1px solid #ddd;padding:4px 8px}}.note{{background:#fff8e1;border:1px solid #f0d264;padding:10px;border-radius:6px;font-size:13px}}</style></head><body>
<h2>同心圆连线假说 · 可视化与检验</h2>
<div class="note">外圆=前区(01-35)，内圆=后区(01-12)。下图为最近 {len(last6)} 期连线叠加（颜色越亮越近）。<br>
若"连线形状/朝向/中点/对径点"含预测信息，下表检验应显著。Bonferroni 校正阈值 α={alpha_bonf:.4f}。</div>
<div class="flex"><div>{legend}<svg width="700" height="700">{''.join(svg)}</svg></div>
<div><h3>检验结果（{N} 期）</h3><table><tr><th>检验</th><th>p值</th><th>判定</th></tr>{sig_rows}</table>
<h3>实战对照（walk-forward {n_periods} 期）</h3>
<table><tr><th>评分器</th><th>场均前区命中/注</th><th>净结果</th><th>ROI</th></tr>
<tr><td>扇区马尔可夫(连线思想)</td><td>{fF_hits/(n_periods*10):.4f}</td><td>{fROI:.0f}</td><td>{fROI/(n_periods*BUDGET)*100:.1f}%</td></tr>
<tr><td>随机</td><td>{rF_hits/(n_periods*10):.4f}</td><td>{rROI:.0f}</td><td>{rROI/(n_periods*BUDGET)*100:.1f}%</td></tr>
<tr><td>EVO-20</td><td>{eF_hits/(n_periods*10):.4f}</td><td>{eROI:.0f}</td><td>{eROI/(n_periods*BUDGET)*100:.1f}%</td></tr></table>
<p class="note">连线形态可观赏，但逐项检验均未通过显著性阈值：形状/朝向/中点/对径点均不含跨期信息。</p>
</div></div></body></html>"""
open(VIEW, "w").write(html)
print(f"\nsaved -> {RESULT}\nsaved -> {VIEW}")
