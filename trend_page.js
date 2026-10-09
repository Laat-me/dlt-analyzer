/* 走势版预测页生成器（round-33）—— 从静态快照升级为全自动重建
   输入: dlt draws.json（升序） + ssq data.json（倒序）
   输出: /Users/mac/dream/走势版预测-手机版.html
   规则: 直落+3 / 斜连+2 / 回补+2（遗漏≥1.5×期望间隔）打分 → 前区 top15 池
         → 三注 5+2 完全不重号（wide15，15 个覆盖位打满；978 期 2.86% vs 同结构随机 2.00%）
         后区 top3 → 三对组合
   对账: 上期对账卡由同一确定性函数回放生成（无需存储，重放=开奖前口径）
   诚实: 四规则无预测力；15号池只减少三注间重复，不改变单注概率；本页仅供娱乐 */
'use strict';
const fs = require('fs');

const DLT_DRAWS = '/Users/mac/dream/dlt-analyzer/.agents/skills/dlt-analyzer/data/draws.json';
const SSQ_DATA = '/Users/mac/dream/ssq-analyzer/data.json';
const OUT = '/Users/mac/dream/走势版预测-手机版.html';
const NOW = new Date();
const ts = `${NOW.getFullYear()}/${NOW.getMonth()+1}/${NOW.getDate()} ${String(NOW.getHours()).padStart(2,'0')}:${String(NOW.getMinutes()).padStart(2,'0')}:${String(NOW.getSeconds()).padStart(2,'0')}`;

/* ---------- 通用走势内核 ---------- */
function trendCore(hist, cfg){
  // hist: 升序 [{code, date, front:[], back:[]}]；cfg: {nF,nB,pF,pB,expF,expB}
  const last = hist[hist.length-1];
  const nextCode = String(Number(last.code) + 1);
  const win = hist.slice(-50);
  const prev = win[win.length-1];

  // 遗漏矩阵 + 统计（窗口内）
  const lastHitF = Array(cfg.nF+1).fill(-1), lastHitB = Array(cfg.nB+1).fill(-1);
  const cntF = Array(cfg.nF+1).fill(0), cntB = Array(cfg.nB+1).fill(0);
  const rows = win.map((d, i) => {
    const cells = [];
    for (let n = 1; n <= cfg.nF; n++){
      if (d.front.includes(n)){ cells.push({hit:true, n}); lastHitF[n] = i; cntF[n]++; }
      else cells.push({hit:false, miss: i - lastHitF[n]});
    }
    for (let n = 1; n <= cfg.nB; n++){
      if (d.back.includes(n)){ cells.push({hit:true, n, blue:true}); lastHitB[n] = i; cntB[n]++; }
      else cells.push({hit:false, miss: i - lastHitB[n], blue:true});
    }
    return {d, cells};
  });
  const missNowF = n => lastHitF[n] >= 0 ? win.length-1 - lastHitF[n] : win.length;
  const missNowB = n => lastHitB[n] >= 0 ? win.length-1 - lastHitB[n] : win.length;

  // 打分 → 池
  const score = (n, prevSet, neiSet, missNow, expMiss) =>
    (prevSet.has(n) ? 3 : 0) + (neiSet.has(n) ? 2 : 0) + (missNow(n) >= 1.5*expMiss ? 2 : 0);
  const neiOf = (set, max) => {
    const s = new Set();
    for (const p of set){ if (p-1 >= 1) s.add(p-1); if (p+1 <= max) s.add(p+1); }
    for (const p of set) s.delete(p);
    return s;
  };
  const prevF = new Set(prev.front), prevB = new Set(prev.back);
  const neiF = neiOf(prevF, cfg.nF), neiB = neiOf(prevB, cfg.nB);
  const poolF = Array.from({length:cfg.nF}, (_,i)=>i+1)
    .sort((a,b) => score(b,prevF,neiF,missNowF,cfg.expF) - score(a,prevF,neiF,missNowF,cfg.expF) || a - b).slice(0, 15);
  const poolB = Array.from({length:cfg.nB}, (_,i)=>i+1)
    .sort((a,b) => score(b,prevB,neiB,missNowB,cfg.expB) - score(a,prevB,neiB,missNowB,cfg.expB) || a - b).slice(0, 3);

  // 三注：前区 15 池切三段（完全不重号），后区 top3 三对
  const tickets = [0,5,10].map((s,i) => ({
    front: poolF.slice(s, s+5),
    back: [poolB[[0,2,1][i]], poolB[[1,0,2][i]]].sort((x,y)=>x-y),
  }));
  for (const t of tickets) t.front.sort((a,b)=>a-b);

  // 上期对账：同一函数回放（用 hist[:-1] 预测 last.code）
  const rc = hist.length > 3 ? trendCore(hist.slice(0, -1), cfg) : null;
  const recon = rc ? {
    code: last.code, actual: last,
    tickets: rc.tickets.map(t => ({
      front: t.front, back: t.back,
      hf: t.front.filter(n => last.front.includes(n)).length,
      hb: t.back.filter(n => last.back.includes(n)).length,
    })),
  } : null;

  // 跨度（近15）
  const spans = win.slice(-15).map(d => Math.max(...d.front) - Math.min(...d.front));
  const spanMean = spans.slice(-10).reduce((a,b)=>a+b,0) / 10;
  const allSpans = win.map(d => Math.max(...d.front) - Math.min(...d.front));

  return { nextCode, win, rows, cntF, cntB, missNowF, missNowB, poolF, poolB,
           tickets, recon, spans, spanMean, spanMin: Math.min(...allSpans), spanMax: Math.max(...allSpans),
           prevF, neiF, cfg, dateRange: `${win[0].date.slice(0,10)} ~ ${win[win.length-1].date.slice(0,10)}` };
}

const tagOf = (n, prevSet, neiSet, missNow, expMiss) =>
  prevSet.has(n) ? ['t-zl','直落'] : neiSet.has(n) ? ['t-xl','斜连']
  : missNow(n) >= 1.5*expMiss ? ['t-hb','回补'] : ['t-wh','散'];

function p2(n){ return String(n).padStart(2,'0'); }

/* ---------- HTML 渲染 ---------- */
function renderGame(core, meta){
  const { cfg } = core;
  const heads = [...Array(cfg.nF)].map((_,i)=>`<th class="fh">${p2(i+1)}</th>`).join('')
              + [...Array(cfg.nB)].map((_,i)=>`<th class="bh">${p2(i+1)}</th>`).join('');
  const bodyRows = core.rows.map(r => {
    const cls = r.d.code === core.win[core.win.length-1].code ? '' : '';
    const cells = r.cells.map(c => c.hit
      ? `<td class="hit"><span class="ball ${c.blue?'b':'r'}">${p2(c.n)}</span></td>`
      : `<td class="miss">${c.miss}</td>`).join('');
    return `<tr${cls}><td class="issue mono">${r.d.code}<span class="dim">${r.d.date.slice(5,10)}</span></td>${cells}</tr>`;
  }).join('');

  // 预测行：池号画圈
  const poolSetF = new Set(core.poolF), poolSetB = new Set(core.poolB);
  const predCells = [];
  for (let n = 1; n <= cfg.nF; n++)
    predCells.push(poolSetF.has(n) ? `<td class="hit"><span class="ring r">${p2(n)}</span></td>` : `<td class="white"></td>`);
  for (let n = 1; n <= cfg.nB; n++)
    predCells.push(poolSetB.has(n) ? `<td class="hit"><span class="ring b">${p2(n)}</span></td>` : `<td class="white"></td>`);
  const predRow = `<tr class="pred"><td class="issue mono">${core.nextCode}<span class="dim">预测</span></td>${predCells.join('')}</tr>`;

  // 统计行
  const gapsF = n => { // 平均/最大遗漏（窗口内相邻命中间隔 + 尾部）
    const idx = core.win.map((d,i)=>d.front.includes(n)?i:-1).filter(i=>i>=0);
    if (!idx.length) return [50, 50];
    const g = idx.slice(1).map((v,i)=>v-idx[i]);
    g.push(core.win.length-1 - idx[idx.length-1]);
    return [g.reduce((a,b)=>a+b,0)/g.length, Math.max(...g)];
  };
  const gapsB = n => {
    const idx = core.win.map((d,i)=>d.back.includes(n)?i:-1).filter(i=>i>=0);
    if (!idx.length) return [50, 50];
    const g = idx.slice(1).map((v,i)=>v-idx[i]);
    g.push(core.win.length-1 - idx[idx.length-1]);
    return [g.reduce((a,b)=>a+b,0)/g.length, Math.max(...g)];
  };
  const statRows =
    `<tr class="stat"><td class="issue">出现次数</td>${Array.from({length:cfg.nF},(_,i)=>`<td class="statv">${core.cntF[i+1]}</td>`).join('')}${Array.from({length:cfg.nB},(_,i)=>`<td class="statv">${core.cntB[i+1]}</td>`).join('')}</tr>` +
    `<tr class="stat"><td class="issue">平均遗漏</td>${Array.from({length:cfg.nF},(_,i)=>`<td class="statv">${gapsF(i+1)[0].toFixed(1)}</td>`).join('')}${Array.from({length:cfg.nB},(_,i)=>`<td class="statv">${gapsB(i+1)[0].toFixed(1)}</td>`).join('')}</tr>` +
    `<tr class="stat"><td class="issue">最大遗漏</td>${Array.from({length:cfg.nF},(_,i)=>`<td class="statv">${gapsF(i+1)[1]}</td>`).join('')}${Array.from({length:cfg.nB},(_,i)=>`<td class="statv">${gapsB(i+1)[1]}</td>`).join('')}</tr>` +
    `<tr class="stat"><td class="issue">当前遗漏</td>${Array.from({length:cfg.nF},(_,i)=>`<td class="statv${core.missNowF(i+1) >= 1.5*cfg.expF ? ' hot':''}">${core.missNowF(i+1)}</td>`).join('')}${Array.from({length:cfg.nB},(_,i)=>`<td class="statv${core.missNowB(i+1) >= 1.5*cfg.expB ? ' hot':''}">${core.missNowB(i+1)}</td>`).join('')}</tr>`;

  // 跨度条
  const maxSpan = Math.max(...core.spans);
  const bars = core.spans.map(s => `<div class="barw"><span class="barv">${s}</span><div class="bar on" style="height:${Math.max(6, s/maxSpan*44)}px"></div></div>`).join('');

  // 三注推荐
  const tixHtml = core.tickets.map((t, i) => {
    const cells = t.front.map(n => { const [tc, tn] = tagOf(n, core.prevF, core.neiF, core.missNowF, cfg.expF);
      return `<div class="ncell"><span class="ball r">${p2(n)}</span><span class="tag ${tc}">${tn}</span></div>`; }).join('');
    const bcells = t.back.map(n => `<div class="ncell"><span class="ball b">${p2(n)}</span></div>`).join('');
    const odd = t.front.filter(n=>n%2===1).length;
    return `<div class="ticket"><div class="ttitle">推荐 ${i+1}</div><div class="nums">${cells}<div class="nsep"></div>${bcells}</div>
      <div class="meta">跨度 <b>${Math.max(...t.front)-Math.min(...t.front)}</b> ｜ 和值 <b>${t.front.reduce((a,b)=>a+b,0)}</b> ｜ 奇偶 <b>${odd}:${5-odd}</b></div></div>`;
  }).join('');

  // 上期对账
  let reconHtml = '';
  if (core.recon){
    const r = core.recon;
    const lines = r.tickets.map((t,i)=>`<p class="rule">推荐${i+1}：<b>${t.front.map(p2).join(' ')}</b> + <b class="fh">${t.back.map(p2).join(' ')}</b> → 前中 <b>${t.hf}</b> 后中 <b>${t.hb}</b>（合计 ${t.hf+t.hb}${t.hf+t.hb>=4?'，达标':''}）</p>`).join('');
    reconHtml = `<div class="card"><h2>上期对账（${r.code}，自动回放开奖前口径）</h2>
      <p class="sub">实际：${r.actual.front.map(p2).join(' ')} + ${r.actual.back.map(p2).join(' ')}</p>${lines}</div>`;
  }

  return `
<section id="${meta.id}" style="display:${meta.display}">
  <div class="card">
    <h1>${meta.title}</h1>
    <p class="sub">最近 50 期：${core.win[0].code} ~ ${core.win[core.win.length-1].code}（${core.dateRange}）<br>预测期：<b class="red">${core.nextCode}</b></p>
    <p class="legend"><span class="ball r">08</span> ${meta.hitF}　<span class="ball b">06</span> ${meta.hitB}　<span class="ring r">01</span> 预测号　<span class="misscell">3</span> 遗漏期数</p>
  </div>
  <div class="card scroll"><table><thead><tr><th class="issue">期号</th>${heads}</tr></thead>
    <tbody>${bodyRows}${predRow}${statRows}</tbody></table></div>
  <div class="card">
    <h2>${meta.fName}跨度走势（近 15 期）</h2>
    <p class="sub">近10期平均跨度 <b class="red">${core.spanMean.toFixed(1)}</b>，推荐跨度带 <b class="red">${Math.max(1,Math.round(core.spanMean-6))}~${Math.round(core.spanMean+6)}</b>（50期范围 ${core.spanMin}~${core.spanMax}）</p>
    <div class="bars">${bars}</div>
  </div>
  ${reconHtml}
  <div class="card">
    <h2>${core.nextCode} 期推荐（直落 / 斜连 / 回补 打分 · 15 号池三注不重号）</h2>
    ${tixHtml}
    <p class="sub" style="margin-top:8px">${meta.fName}候选池（top15）：${core.poolF.map(p2).join(' ')}<br>${meta.bName} top3：${core.poolB.map(p2).join(' ')}</p>
  </div>
  <div class="card">
    <h2>看号规则（经典走势图玩法）</h2>
    <p class="rule"><b class="c-zl">直落</b>：上期号码本期重复出现。</p>
    <p class="rule"><b class="c-xl">斜连</b>：上期号码 ±1 的邻号，走势图上呈对角连线。</p>
    <p class="rule"><b class="c-hb">回补</b>：当前遗漏明显超过期望遗漏（${meta.expText}）的号。</p>
    <p class="rule"><b class="c-rh">跨度带</b>：首尾号码差落在近 10 期平均跨度 ±6 内。</p>
    <p class="sub">候选池按上述规则加权打分取 top15，三注前区完全不重号（15 个覆盖位打满）；round-33 回测：走势规则 978 期达标率 2.86%，同结构随机基线 2.00%，差异不作预测力宣称；结构只负责不浪费 6 元覆盖。</p>
  </div>
  <div class="note"><b>理性提示</b><br>本页四规则已做过 978 期 walk-forward：原始共享池 1.64%，15 号池不重号 2.86%，同结构随机基线 2.00%；短窗口差异不证明走势规则有预测力。每期开奖独立随机，任何一注中奖概率完全相同，长期期望为负。<br>本页推荐仅供娱乐，请勿据此加大投注。</div>
  <p class="foot">数据：${meta.src}（50 期）｜生成：${ts}｜生成器：dlt-analyzer/trend_page.js（update.js 自动重建）</p>
</section>`;
}

/* ---------- 主入口 ---------- */
function build(){
  const dltHist = JSON.parse(fs.readFileSync(DLT_DRAWS)).draws
    .map(d => ({code: d.num, date: d.date, front: d.front, back: d.back}));
  const ssqHist = JSON.parse(fs.readFileSync(SSQ_DATA)).slice().reverse()
    .map(d => ({code: d.c, date: d.d, front: d.r, back: [d.b]}));

  const dltCore = trendCore(dltHist, {nF:35, nB:12, pF:5, pB:2, expF:7, expB:6});
  // SSQ 后区只取 1 蓝，池子单独处理：top3 蓝球直接展示，票面各带 1 蓝
  const ssqCore = trendCore(ssqHist, {nF:33, nB:16, pF:6, pB:1, expF:5.5, expB:16});
  // SSQ 票面修正：红 6 个（池 18 取三段 6/6/6），蓝 1 个（top3 各配一注）
  ssqCore.poolF = Array.from({length:33},(_,i)=>i+1)
    .sort((a,b)=> scoreSsq(a) - scoreSsq(b)).slice(0,18);
  function scoreSsq(n){
    const prev = ssqHist[ssqHist.length-1];
    const pf = new Set(prev.front);
    const nei = new Set(); for (const p of pf){ if(p-1>=1) nei.add(p-1); if(p+1<=33) nei.add(p+1); }
    for (const p of pf) nei.delete(p);
    const lastIdx = ssqHist.map((d,i)=>d.front.includes(n)?i:-1).filter(i=>i>=0).pop();
    const miss = ssqHist.length-1 - (lastIdx ?? -1) - 1;
    return -((pf.has(n)?3:0) + (nei.has(n)?2:0) + (miss >= 1.5*5.5 ? 2 : 0));
  }
  ssqCore.tickets = [0,6,12].map((s,i)=>({ front: ssqCore.poolF.slice(s,s+6).sort((a,b)=>a-b), back: [ssqCore.poolB[i]] }));
  // SSQ 对账回放同样修正
  if (ssqHist.length > 3){
    const sub = ssqHist.slice(0,-1);
    const rc = trendCore(sub, {nF:33, nB:16, pF:6, pB:1, expF:5.5, expB:16});
    const score2 = n => { const prev = sub[sub.length-1]; const pf = new Set(prev.front);
      const nei = new Set(); for (const p of pf){ if(p-1>=1) nei.add(p-1); if(p+1<=33) nei.add(p+1); } for (const p of pf) nei.delete(p);
      const lastIdx = sub.map((d,i)=>d.front.includes(n)?i:-1).filter(i=>i>=0).pop();
      const miss = sub.length-1 - (lastIdx ?? -1) - 1;
      return -((pf.has(n)?3:0) + (nei.has(n)?2:0) + (miss >= 1.5*5.5 ? 2 : 0)); };
    const pool18 = Array.from({length:33},(_,i)=>i+1).sort((a,b)=>score2(a)-score2(b)).slice(0,18);
    rc.tickets = [0,6,12].map((s,i)=>({front: pool18.slice(s,s+6).sort((a,b)=>a-b), back:[rc.poolB[i]]}));
    const act = ssqHist[ssqHist.length-1];
    ssqCore.recon = { code: act.code, actual: act,
      tickets: rc.tickets.map(t=>({ front:t.front, back:t.back,
        hf: t.front.filter(n=>act.front.includes(n)).length,
        hb: t.back.filter(n=>act.back.includes(n)).length })) };
  }

  const html = `<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<title>彩票走势版预测（手机版）</title>
<style>
*{box-sizing:border-box}
body{margin:0;background:rgba(226,232,240,.7);font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Helvetica Neue",sans-serif;color:#1e293b}
.tabs{display:flex;gap:10px;justify-content:center;padding:12px 8px 2px}
.tab{padding:7px 22px;border-radius:999px;font-weight:700;font-size:14px;background:#fff;color:#475569;border:1px solid #e2e8f0}
.tab.on{background:#dc2626;color:#fff;border-color:#dc2626}
.card{background:#fff;border-radius:12px;margin:10px 8px;padding:12px;box-shadow:0 1px 2px rgba(0,0,0,.05)}
h1{font-size:18px;margin:0 0 4px}
h2{font-size:13px;margin:0 0 8px;color:#334155}
.sub{font-size:11px;color:#64748b;margin:4px 0;line-height:1.6}
.red{color:#dc2626}.dim{color:#94a3b8;font-size:9px;margin-left:3px}
.mono{font-family:ui-monospace,Menlo,monospace}
.legend{font-size:10px;color:#64748b;display:flex;align-items:center;gap:4px;flex-wrap:wrap;margin:8px 0 0}
.misscell{display:inline-flex;width:20px;height:20px;align-items:center;justify-content:center;border-radius:3px;background:#f1f5f9;color:#94a3b8;font-size:10px;border:1px solid #e2e8f0}
.scroll{overflow-x:auto;-webkit-overflow-scrolling:touch;padding:6px}
table{border-collapse:collapse;width:max-content;min-width:100%}
th,td{border:1px solid #e2e8f0;font-size:10px;text-align:center;min-width:23px;height:23px;padding:0 1px;font-weight:400}
th{background:#f8fafc;color:#64748b;font-weight:500;position:sticky;top:0;z-index:3}
td.issue,th.issue{position:sticky;left:0;background:#fff;z-index:2;min-width:66px;text-align:left;padding:0 2px;font-size:10px;white-space:nowrap}
th.issue{z-index:4;background:#f8fafc}
.fh{color:#ef4444}.bh{color:#3b82f6}
td.miss{background:#f1f5f9;color:#94a3b8}
td.hit{background:#fff}td.white{background:#fff}
td.statv.hot{color:#7e22ce;font-weight:700}
.ball{display:inline-flex;width:20px;height:20px;border-radius:50%;color:#fff;font-weight:700;font-size:10px;align-items:center;justify-content:center;box-shadow:0 1px 2px rgba(0,0,0,.15)}
.ball.r{background:linear-gradient(135deg,#ef4444,#b91c1c)}.ball.b{background:linear-gradient(135deg,#3b82f6,#1d4ed8)}
.ring{display:inline-flex;width:20px;height:20px;border-radius:50%;border:2px dashed;font-weight:700;font-size:10px;align-items:center;justify-content:center;background:#fff}
.ring.r{border-color:#ef4444;color:#dc2626}.ring.b{border-color:#3b82f6;color:#2563eb}
tr.pred td.issue{background:#fef2f2;color:#dc2626;font-weight:700}
tr.stat td.issue{background:#fffbeb;font-size:10px;color:#475569}
td.statv{background:rgba(255,251,235,.6);font-family:ui-monospace,Menlo,monospace;color:#475569}
.bars{display:flex;align-items:flex-end;gap:4px;height:58px;margin-top:6px}
.barw{display:flex;flex-direction:column;align-items:center;gap:2px}
.barv{font-size:9px;color:#64748b}
.bar{width:15px;border-radius:2px}.bar.on{background:#fb7185}
.ticket{border:1px solid #e2e8f0;border-radius:8px;padding:10px;margin-top:8px}
.ttitle{font-size:11px;font-weight:700;color:#64748b;margin-bottom:6px}
.nums{display:flex;flex-wrap:wrap;gap:8px 10px;align-items:flex-start}
.ncell{display:flex;flex-direction:column;align-items:center;gap:2px}
.nsep{border-left:1px solid #e2e8f0;align-self:stretch;margin-left:2px}
.tag{font-size:9px;padding:0 4px;border-radius:4px}
.t-zl{background:#ffedd5;color:#c2410c}.t-xl{background:#dcfce7;color:#15803d}.t-hb{background:#f3e8ff;color:#7e22ce}.t-rh{background:#fee2e2;color:#b91c1c}.t-wh{background:#f1f5f9;color:#64748b}
.meta{font-size:10px;color:#64748b;margin-top:8px}
.rule{font-size:12px;color:#475569;margin:4px 0}
.c-zl{color:#ea580c}.c-xl{color:#16a34a}.c-hb{color:#9333ea}.c-rh{color:#dc2626}
.note{background:#fffbeb;border:1px solid #fde68a;color:#92400e;font-size:12px;border-radius:12px;padding:12px;margin:10px 8px;line-height:1.7}
.foot{text-align:center;font-size:10px;color:#94a3b8;padding:4px 8px 16px}
</style>
</head>
<body>
<div class="tabs">
  <button id="tab-ssq" class="tab on" onclick="show('ssq')">双色球</button>
  <button id="tab-dlt" class="tab" onclick="show('dlt')">大乐透</button>
</div>
${renderGame(ssqCore, {id:'ssq', display:'', title:'双色球走势版预测', hitF:'红球命中', hitB:'蓝球命中', fName:'红球', bName:'蓝球', expText:'红球 5.5 期、蓝球 16 期', src:'ssq-analyzer/data.json'})}
${renderGame(dltCore, {id:'dlt', display:'none', title:'大乐透走势版预测', hitF:'前区命中', hitB:'后区命中', fName:'前区', bName:'后区', expText:'前区 7 期、后区 6 期', src:'dlt-analyzer/draws.json'})}
<script>
function show(g){
  document.getElementById('ssq').style.display = g==='ssq' ? '' : 'none';
  document.getElementById('dlt').style.display = g==='dlt' ? '' : 'none';
  document.getElementById('tab-ssq').className = 'tab' + (g==='ssq' ? ' on' : '');
  document.getElementById('tab-dlt').className = 'tab' + (g==='dlt' ? ' on' : '');
}
</script>
</body>
</html>`;
  fs.writeFileSync(OUT, html);
  return { out: OUT, size: html.length, dlt: {nextCode: dltCore.nextCode, pool: dltCore.poolF, back: dltCore.poolB},
           ssq: {nextCode: ssqCore.nextCode, pool: ssqCore.poolF, back: ssqCore.poolB},
           recon: {dlt: dltCore.recon && dltCore.recon.code, ssq: ssqCore.recon && ssqCore.recon.code} };
}
module.exports = { build, trendCore };
if (require.main === module) console.log(JSON.stringify(build(), null, 1));
