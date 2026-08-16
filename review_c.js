// 复盘步骤C：写入26093预测 → model.json复盘备注 → 数据一致性校验
const fs = require('fs');
const BASE = 'D:/dream/dlt-analyzer/.agents/skills/dlt-analyzer/data/';
const out = JSON.parse(fs.readFileSync('D:/dream/dlt-analyzer/review_out.json', 'utf8'));

// 1) 追加 26093 预测（主推 AI_U_wide + 参考 K_prob_ensemble，格式对齐 #17/#18）
const pj = JSON.parse(fs.readFileSync(BASE + 'predictions.json', 'utf8'));
const next = '26093';
if(!pj.records.some(r => r.targetDrawNum === next)){
  let id = Math.max(...pj.records.map(r => r.id || 0));
  const now = new Date().toISOString().slice(0,10);
  pj.records.push({
    id: ++id, predictedAt: now, targetDrawNum: next, model: 'AI_U_wide', mode: '6+3',
    predictedFront: out.pred26093.AI_U_wide.front6, predictedBack: out.pred26093.AI_U_wide.back3,
    verified: false, hitGe4: null, algorithm: 'AI_U_wide',
    note: '6+3主推: AI_U_wide(重号+宽邻域, 还原版), 数据口径 draws.json 1006期(19123-26092)'
  });
  pj.records.push({
    id: ++id, predictedAt: now, targetDrawNum: next, model: 'K_prob_ensemble', mode: '6+3',
    predictedFront: out.pred26093.K_prob_ensemble.front6, predictedBack: out.pred26093.K_prob_ensemble.back3,
    verified: false, hitGe4: null, algorithm: 'K_prob_ensemble',
    note: '6+3参考组: H+I+J 等权集成'
  });
  console.log(`已写入 26093 期预测 2 条（#${id-1} AI_U_wide, #${id} K_prob_ensemble）`);
} else {
  console.log('26093 预测已存在，跳过');
}
fs.writeFileSync(BASE + 'predictions.json', JSON.stringify(pj, null, 1));

// 2) model.json 复盘备注（不动算法/权重，仅记录观察）
const mj = JSON.parse(fs.readFileSync(BASE + 'model.json', 'utf8'));
mj.reviewNotes = mj.reviewNotes || [];
mj.reviewNotes.push({
  round: 26, date: new Date().toISOString().slice(0,10),
  event: '复盘26092期(2026-08-15开奖)',
  result: '正式预测3条(#17/#18/#19)全部未达标(合计命中1/1/2); 31算法事后前向验证0个达标(最高E_entropy=3, 随机期望0.6个), 属正常波动',
  v1v2v3: 'v1累计8期平均命中1.13, v2累计6期平均1.33, v3累计2期平均1.00; v2-v1差0.21≥0.08满足调整门槛, 但主算法已切换AI_U_wide且样本小, 本轮不调权重只记录观察',
  next: '26093期预测已按v29口径(AI_U_wide主+K_prob_ensemble参考)写入predictions.json'
});
fs.writeFileSync(BASE + 'model.json', JSON.stringify(mj, null, 1));
console.log('model.json 已追加 reviewNotes(round-26)');

// 3) 一致性校验
const d = JSON.parse(fs.readFileSync(BASE + 'draws.json', 'utf8'));
const p2 = JSON.parse(fs.readFileSync(BASE + 'predictions.json', 'utf8'));
const nums = new Set(d.draws.map(x => x.num));
const unverified = p2.records.filter(r => !r.verified);
console.log(`校验: draws ${d.draws.length} 期(最新${d.latest.num}) | records ${p2.records.length} 条 | 待验证 ${unverified.length} 条(目标期: ${unverified.map(r=>r.targetDrawNum).join(',')})`);
unverified.forEach(r => { if(nums.has(r.targetDrawNum)) throw new Error(`记录 #${r.id} 目标期 ${r.targetDrawNum} 已开奖但未验证!`); });
console.log('一致性 OK');
