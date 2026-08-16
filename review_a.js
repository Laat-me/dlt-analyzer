// 复盘步骤A：追加 26092 开奖 → 验证全部待验证预测记录 → 更新元数据
const fs = require('fs');
const BASE = 'D:/dream/dlt-analyzer/.agents/skills/dlt-analyzer/data/';

const dj = JSON.parse(fs.readFileSync(BASE + 'draws.json', 'utf8'));
const fetched = JSON.parse(fs.readFileSync('D:/dream/ssq/dlt_fetch.json', 'utf8'));

// 1) 追加新开奖（只补新期号，不动旧记录）
const known = new Set(dj.draws.map(d => d.num));
let added = 0;
for(const it of fetched.value.list){
  if(known.has(it.lotteryDrawNum)) continue;
  const nums = it.lotteryDrawResult.trim().split(/\s+/).map(Number);
  const front = nums.slice(0,5), back = nums.slice(5,7);
  dj.draws.push({ num: it.lotteryDrawNum, date: it.lotteryDrawTime, front, back });
  added++;
  console.log(`新增开奖: ${it.lotteryDrawNum}（${it.lotteryDrawTime}）前区 ${front.join(' ')} 后区 ${back.join(' ')}`);
}
dj.draws.sort((a,b) => a.num.localeCompare(b.num));
const N = dj.draws.length, L = dj.draws[N-1];

// 2) 元数据与频次统计
dj.updatedAt = new Date().toISOString().slice(0,10);
dj.sampleSize = N; dj.totalDraws = N;
dj.dataRange = `${dj.draws[0].num} - ${L.num}`;
dj.dateRange = `${dj.draws[0].date} ~ ${L.date}`;
dj.latest = { num: L.num, date: L.date, front: L.front, back: L.back };
const fTop = Array.from({length:35},(_,i)=>({number:i+1, count:0}));
const bTop = Array.from({length:12},(_,i)=>({number:i+1, count:0}));
dj.draws.forEach(d => d.front.forEach(n => fTop[n-1].count++));
dj.draws.forEach(d => d.back.forEach(n => bTop[n-1].count++));
dj.stats = {
  frontFrequencyTop10: fTop.sort((a,b)=>b.count-a.count||a.number-b.number).slice(0,10),
  backFrequencyTop5: bTop.sort((a,b)=>b.count-a.count||a.number-b.number).slice(0,5)
};
fs.writeFileSync(BASE + 'draws.json', JSON.stringify(dj));
console.log(`draws.json: ${N} 期（${dj.dataRange}）`);

// 3) 验证待验证预测记录
const pj = JSON.parse(fs.readFileSync(BASE + 'predictions.json', 'utf8'));
const byNum = Object.fromEntries(dj.draws.map(d => [d.num, d]));
for(const r of pj.records){
  if(r.verified) continue;
  const act = byNum[r.targetDrawNum];
  if(!act) continue;
  const pf = r.predictedFront || r.front6, pb = r.predictedBack || r.back3;
  r.actualFront = act.front; r.actualBack = act.back;
  r.frontHits = pf.filter(n => act.front.includes(n)).length;
  r.backHits = pb.filter(n => act.back.includes(n)).length;
  r.verified = true;
  const total = r.frontHits + r.backHits;
  if(r.mode === '6+3') r.hitGe4 = total >= 4;
  const show = pf.join(' ') + ' + ' + pb.join(' ');
  console.log(`验证 #${r.id} ${r.targetDrawNum} ${r.model}: 前中${r.frontHits} 后中${r.backHits} 合计${total}${r.mode==='6+3' ? (r.hitGe4?' ✓达标':' ✗未达标') : ''} | ${show}`);
}
pj.updatedAt = new Date().toISOString().slice(0,10);
fs.writeFileSync(BASE + 'predictions.json', JSON.stringify(pj, null, 1));
console.log('predictions.json 已更新');
