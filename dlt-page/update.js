// 大乐透页面一键更新：拉开奖 → 追加 draws.json → 验证预测 → Python 回测 → 组装 HTML
// 用法: node update.js [--no-python]（--no-python 复用现有 bt.json，数据未变时提速）
const fs = require('fs');
const { execSync } = require('child_process');
const DLT = 'D:/dream/dlt-analyzer/.agents/skills/dlt-analyzer';
const PAGE = 'D:/dream/dlt-page';
const PY = 'C:/Users/Admin/AppData/Local/Programs/Python/Python312/python.exe';
const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36';

async function main(){
  // 1) 拉取最新开奖
  const dj = JSON.parse(fs.readFileSync(`${DLT}/data/draws.json`, 'utf8'));
  const latest = dj.draws[dj.draws.length - 1];
  const r = await fetch(`https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry?gameNo=85&provinceId=0&pageSize=30&termNum=${latest.num}&isSpecial=0`,
    { headers: { 'user-agent': UA, 'referer': 'https://www.lottery.gov.cn/', 'accept': 'application/json' } });
  const j = await r.json();
  if(!j.success || !j.value || !j.value.list) throw new Error('接口返回异常: ' + (j.errorMessage || ''));

  // 2) 追加新期（只补新期号，不动旧记录）
  const known = new Set(dj.draws.map(d => d.num));
  let added = 0;
  for(const it of j.value.list){
    if(known.has(it.lotteryDrawNum)) continue;
    const nums = it.lotteryDrawResult.trim().split(/\s+/).map(Number);
    dj.draws.push({ num: it.lotteryDrawNum, date: it.lotteryDrawTime, front: nums.slice(0,5), back: nums.slice(5,7) });
    added++;
    console.log(`新增开奖: ${it.lotteryDrawNum}（${it.lotteryDrawTime}）前区 ${nums.slice(0,5).join(' ')} 后区 ${nums.slice(5,7).join(' ')}`);
  }
  if(added){
    dj.draws.sort((a,b) => a.num.localeCompare(b.num));
    const N = dj.draws.length, L = dj.draws[N-1];
    dj.updatedAt = new Date().toISOString().slice(0,10);
    dj.sampleSize = N; dj.totalDraws = N;
    dj.dataRange = `${dj.draws[0].num} - ${L.num}`;
    dj.dateRange = `${dj.draws[0].date} ~ ${L.date}`;
    dj.latest = { num: L.num, date: L.date, front: L.front, back: L.back };
    const fT = Array.from({length:35},(_,i)=>({number:i+1,count:0})), bT = Array.from({length:12},(_,i)=>({number:i+1,count:0}));
    dj.draws.forEach(d => d.front.forEach(n => fT[n-1].count++));
    dj.draws.forEach(d => d.back.forEach(n => bT[n-1].count++));
    dj.stats = { frontFrequencyTop10: fT.sort((a,b)=>b.count-a.count||a.number-b.number).slice(0,10),
                 backFrequencyTop5: bT.sort((a,b)=>b.count-a.count||a.number-b.number).slice(0,5) };
    fs.writeFileSync(`${DLT}/data/draws.json`, JSON.stringify(dj));
  }
  console.log(`draws.json: ${dj.draws.length} 期（最新 ${dj.draws[dj.draws.length-1].num}）新增 ${added} 期`);

  // 3) 验证待验证预测
  const pj = JSON.parse(fs.readFileSync(`${DLT}/data/predictions.json`, 'utf8'));
  const byNum = Object.fromEntries(dj.draws.map(d => [d.num, d]));
  let verified = 0;
  for(const rec of pj.records){
    if(rec.verified) continue;
    const act = byNum[rec.targetDrawNum];
    if(!act) continue;
    const pf = rec.predictedFront || rec.front6 || [], pb = rec.predictedBack || rec.back3 || [];
    rec.actualFront = act.front; rec.actualBack = act.back;
    rec.frontHits = pf.filter(n => act.front.includes(n)).length;
    rec.backHits = pb.filter(n => act.back.includes(n)).length;
    rec.verified = true;
    if(rec.mode === '6+3') rec.hitGe4 = (rec.frontHits + rec.backHits) >= 4;
    verified++;
    console.log(`验证 #${rec.id} ${rec.targetDrawNum} ${rec.model}: 前中${rec.frontHits} 后中${rec.backHits} 合计${rec.frontHits+rec.backHits}${rec.mode==='6+3'?(rec.hitGe4?' ✓达标':' ✗未达标'):''}`);
  }
  if(verified){ pj.updatedAt = new Date().toISOString().slice(0,10); fs.writeFileSync(`${DLT}/data/predictions.json`, JSON.stringify(pj, null, 1)); }

  // 4) Python 回测（数据或参数变化时需要重跑；--no-python 复用旧 bt.json）
  if(!process.argv.includes('--no-python')){
    console.log('运行 Python 回测（31 算法 × 2 窗口，约 1-2 分钟）…');
    execSync(`"${PY}" ${PAGE}/backtest_run.py`, { stdio: 'inherit' });
  }

  // 5) 下一期预测入库（若缺）
  const nextCode = String(Number(dj.draws[dj.draws.length-1].num) + 1);
  const bt = JSON.parse(fs.readFileSync(`${PAGE}/bt.json`, 'utf8'));
  if(!pj.records.some(r => r.targetDrawNum === nextCode)){
    let id = Math.max(...pj.records.map(r => r.id || 0));
    const today = new Date().toISOString().slice(0,10);
    pj.records.push({ id: ++id, predictedAt: today, targetDrawNum: nextCode, model: 'AI_U_wide', mode: '6+3',
      predictedFront: bt.pred.AI_U_wide.front6, predictedBack: bt.pred.AI_U_wide.back3,
      verified: false, hitGe4: null, algorithm: 'AI_U_wide', note: '6+3主推: AI_U_wide(还原版)' });
    pj.records.push({ id: ++id, predictedAt: today, targetDrawNum: nextCode, model: 'K_prob_ensemble', mode: '6+3',
      predictedFront: bt.pred.K_prob_ensemble.front6, predictedBack: bt.pred.K_prob_ensemble.back3,
      verified: false, hitGe4: null, algorithm: 'K_prob_ensemble', note: '6+3参考组: H+I+J集成' });
    pj.updatedAt = today;
    fs.writeFileSync(`${DLT}/data/predictions.json`, JSON.stringify(pj, null, 1));
    console.log(`已生成下一期（${nextCode}）预测并追加 predictions.json`);
  } else {
    console.log(`下一期（${nextCode}）预测已存在`);
  }
  // 六爻占卜记录（确定性玄学娱乐）：前九期起卦 + 下期开奖时间起始卦；未开奖前刷新为最新卦象
  {
    const lastDate = new Date(dj.draws[dj.draws.length-1].date);
    let add2 = 1;
    while (![1,3,6].includes(new Date(lastDate.getTime() + add2*864e5).getDay())) add2++;
    const nd = new Date(lastDate.getTime() + add2*864e5);
    const timeInfo = { y: nd.getFullYear(), m: nd.getMonth()+1, d: nd.getDate(), hour: 21 };   // 21:25 开奖
    const LiuYao = require('D:/dream/ssq/liuyao.js');
    const g = LiuYao.divine(dj.draws.slice(-9), d => [d.front.reduce((a,b)=>a+b,0) % 2 === 1, d.back.reduce((a,b)=>a+b,0) % 2 === 1],
                            nextCode, {frontMax:35, frontN:5, backMax:12, backN:2}, timeInfo);
    const before = pj.records.length;
    pj.records = pj.records.filter(r => !(r.targetDrawNum === nextCode && r.model === '六爻占卜' && !r.verified));
    let id = Math.max(...pj.records.map(r => r.id || 0));
    pj.records.push({ id: ++id, predictedAt: new Date().toISOString().slice(0,10), targetDrawNum: nextCode,
      model: '六爻占卜', mode: '5+2', predictedFront: g.front, predictedBack: g.back, verified: false,
      note: `六爻起卦: 起始卦${g.timeGua ? g.timeGua.name : '—'} + 本卦${g.benGua}${g.bianGua ? '变' + g.bianGua : ''} seed=${g.seed}（玄学娱乐）` });
    if(pj.records.length !== before || true){
      pj.updatedAt = new Date().toISOString().slice(0,10);
      console.log(`六爻占卜记录已更新到 ${nextCode}（起始卦${g.timeGua ? g.timeGua.name : '—'}，本卦${g.benGua}${g.bianGua?'变'+g.bianGua:''}）`);
    }
    fs.writeFileSync(`${DLT}/data/predictions.json`, JSON.stringify(pj, null, 1));
  }

  // 6) 组装 HTML
  const tpl = fs.readFileSync(`${PAGE}/template.html`, 'utf8');
  const ec = fs.readFileSync('D:/dream/ssq/echarts.min.js', 'utf8');
  const html = tpl
    .replace('__ECHARTS_JS__', () => ec)
    .replace('__LIUYAO_JS__', () => fs.readFileSync('D:/dream/ssq/liuyao.js', 'utf8'))
    .replace('__DATA_JSON__', () => JSON.stringify(dj.draws))
    .replace('__PRED_JSON__', () => fs.readFileSync(`${DLT}/data/predictions.json`, 'utf8'))
    .replace('__BT_JSON__', () => fs.readFileSync(`${PAGE}/bt.json`, 'utf8'));
  const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
  scripts.forEach((s, i) => { try { new Function(s); } catch(e){ console.error(`脚本块 ${i} 语法错误:`, e.message); process.exit(1); } });
  fs.writeFileSync(`${PAGE}/大乐透分析.html`, html);
  fs.writeFileSync(`${PAGE}/index.html`, html);
  console.log(`已生成 大乐透分析.html / index.html（${(html.length/1024).toFixed(0)} KB）`);
}
main().catch(e => { console.error('更新失败：', e.message); process.exit(1); });
