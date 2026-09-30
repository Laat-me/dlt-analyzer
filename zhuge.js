/* 诸葛神数 · 大乐透求签（round-32, 统计娱乐）
   数据: .agents/skills/dlt-analyzer/data/mystic_zhuge.json
         （秘本诸葛神数 384 签繁体全文，源自白云深处人家海外站数据文件）
   传统占法: 心念所问之事，报三字——第一字笔画为百位、第二字十位、第三字个位；
         笔画 ≤9 照算，≥10 取个位，10 的倍数照 1 算；总数 >384 递减 384 定签号。
   大乐透自创娱乐口径: 「三字」取上一期开奖——前区首号、前区末号、后区末号，
         按上述笔画规则化成百/十/个位组成签数（确定性，无人工输入）；
         历史期复盘取该期前一期开奖，前瞻期取最新一期。
   出号（自创娱乐规则）: 前区 = 签号s、s+上期首号、s+上期末号、2s、s+上期后区和值
         各 %35；后区 = s%12、(s+上期后区和值)%12；不足用 seed 随机补足。
   诚实声明: 大乐透为独立随机事件，签文与开奖无任何因果，仅供统计娱乐。 */
'use strict';
const fs = require('fs');
const path = require('path');
const DATA = JSON.parse(fs.readFileSync(path.join(__dirname, '.agents/skills/dlt-analyzer/data/mystic_zhuge.json'), 'utf8'));

function fnv1a(s){let h=2166136261;for(const ch of unescape(encodeURIComponent(s))){h^=ch.charCodeAt(0);h=Math.imul(h,16777619);}return h>>>0;}
function mulberry32(a){return function(){a|=0;a=a+0x6D2B79F5|0;let t=Math.imul(a^a>>>15,1|a);t=t+Math.imul(t^t>>>7,61|t)^0;return((t^t>>>14)>>>0)/4294967296;};}
function pickN(maxn, m, rng){
  const a = Array.from({length:maxn},(_,i)=>i+1);
  for(let i=maxn-1;i>0;i--){ const j=(rng()*(i+1))|0; [a[i],a[j]]=[a[j],a[i]]; }
  return a.slice(0,m);
}

// 诸葛笔画位规则: ≤9 照算；≥10 取个位；10 的倍数照 1 算
function strokeDigit(n){
  if (n < 10) return n;
  if (n % 10 === 0) return 1;
  return n % 10;
}

function zhugeCast(draws, issue, nextDrawTime){
  // "上期"基准：历史期复盘取该期前一期（无前视），前瞻期取最新一期
  const idx = draws.findIndex(d => String(d.num) === String(issue));
  const prev = idx > 0 ? draws[idx - 1] : draws[draws.length - 1];
  const trio = [prev.front[0], prev.front[4], prev.back[1]];   // 拟"三字"
  const digits = trio.map(strokeDigit);
  const raw = digits[0] * 100 + digits[1] * 10 + digits[2];
  let sign = raw;
  while (sign > 384) sign -= 384;
  const poem = DATA.signs[String(sign)];
  const backSum = prev.back[0] + prev.back[1];

  const seed = fnv1a(`zhuge|${issue}|${raw}|${sign}`);
  const rng = mulberry32(seed);
  const front = [];
  for (const v of [sign, sign + trio[0], sign + trio[1], sign * 2, sign + backSum]) {
    const x = ((v - 1) % 35) + 1;
    if (!front.includes(x)) front.push(x);
  }
  for (const n of pickN(35, 35, rng)) { if (front.length >= 5) break; if (!front.includes(n)) front.push(n); }
  const back = [];
  for (const v of [sign, sign + backSum]) {
    const x = ((v - 1) % 12) + 1;
    if (!back.includes(x)) back.push(x);
  }
  for (const n of pickN(12, 12, rng)) { if (back.length >= 2) break; if (!back.includes(n)) back.push(n); }

  return {
    method: '诸葛神数', benGua: `第${sign}签`, bianGua: '—',
    moving: `三数${trio.join('/')} → 笔画位${digits.join('-')} → 签数${raw}`,
    timeGua: `上期 ${prev.num}（前区 ${prev.front.join(' ')}｜后区 ${prev.back.join(' ')}）`,
    front: front.slice(0, 5).sort((a, b) => a - b),
    back: back.slice(0, 2).sort((a, b) => a - b),
    story: `第${sign}签（签数${raw}${raw > 384 ? '-384' : ''}）：${(poem || '').split('\n').join(' ')}`,
    poem, signNo: sign, seed, isEntertainment: true,
  };
}

module.exports = { zhugeCast, DATA, strokeDigit };
