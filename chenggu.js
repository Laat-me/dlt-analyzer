/* 称骨歌 · 大乐透开奖盘（round-32, 统计娱乐）
   数据: .agents/skills/dlt-analyzer/data/mystic_chenggu.json
         （六十甲子年重 + 农历月重12 + 日重30 + 时辰重12 + 男命批语52级2.1~7.2两
           + 女命批语51级2.1~7.1两，源自算准网全表并与百度知道/kknews主流版交叉核对）
   口径: 以开奖日农历年月日时为"开奖生辰"（21:25 开奖属亥时），
         四柱骨重相加 = 总骨重（钱），查批语（开奖盘性别未知按传统男命口径）。
   出号（自创娱乐规则）: 年/月/日/时四柱骨重各 %35 入一号，总骨重 %35 补第五号；
         后区 = 总骨重 %12、年月日骨重和 %12；不足用 seed 随机补足。
   诚实声明: 大乐透为独立随机事件，骨重与开奖无任何因果，仅供统计娱乐。 */
'use strict';
const fs = require('fs');
const path = require('path');
const Ziwei = require('/Users/mac/dream/ssq-analyzer/ziwei.js');
const DATA = JSON.parse(fs.readFileSync(path.join(__dirname, '.agents/skills/dlt-analyzer/data/mystic_chenggu.json'), 'utf8'));

const GAN = '甲乙丙丁戊己庚辛壬癸';
const ZHI = '子丑寅卯辰巳午未申酉戌亥';

function fnv1a(s){let h=2166136261;for(const ch of unescape(encodeURIComponent(s))){h^=ch.charCodeAt(0);h=Math.imul(h,16777619);}return h>>>0;}
function mulberry32(a){return function(){a|=0;a=a+0x6D2B79F5|0;let t=Math.imul(a^a>>>15,1|a);t=t+Math.imul(t^t>>>7,61|t)^0;return((t^t>>>14)>>>0)/4294967296;};}
function pickN(maxn, m, rng){
  const a = Array.from({length:maxn},(_,i)=>i+1);
  for(let i=maxn-1;i>0;i--){ const j=(rng()*(i+1))|0; [a[i],a[j]]=[a[j],a[i]]; }
  return a.slice(0,m);
}

function chengguCast(draws, issue, nextDrawTime){
  const t = nextDrawTime(draws, issue);
  const lu = Ziwei.solarToLunar(t.y, t.m, t.d);
  const gz = GAN[(lu.year - 4) % 10] + ZHI[(lu.year - 4) % 12];
  const shiIdx = Math.floor(((t.hour + 1) % 24) / 2);        // 21点 → 亥
  const shi = ZHI[shiIdx];
  const wy = DATA.yearWeights[gz];
  const wm = DATA.monthWeights[String(lu.month)];
  const wd = DATA.dayWeights[String(lu.day)];
  const wh = DATA.hourWeights[shi];
  const total = wy + wm + wd + wh;                            // 钱
  const verseKey = String(Math.min(72, Math.max(21, total)));
  const verse = DATA.maleVerses[verseKey];
  const liang = Math.floor(total / 10), qian = total % 10;

  const seed = fnv1a(`chenggu|${issue}|${gz}|${lu.month}|${lu.day}|${shiIdx}`);
  const rng = mulberry32(seed);
  const front = [];
  for (const c of [wy, wm, wd, wh, total]) {
    const v = ((c - 1) % 35) + 1;
    if (!front.includes(v)) front.push(v);
  }
  for (const n of pickN(35, 35, rng)) { if (front.length >= 5) break; if (!front.includes(n)) front.push(n); }
  const back = [];
  for (const c of [total, wy + wm + wd]) {
    const v = ((c - 1) % 12) + 1;
    if (!back.includes(v)) back.push(v);
  }
  for (const n of pickN(12, 12, rng)) { if (back.length >= 2) break; if (!back.includes(n)) back.push(n); }

  return {
    method: '称骨歌', benGua: `总骨重${liang}两${qian}钱`, bianGua: '—',
    moving: `${gz}年${wy}钱 · ${lu.month}月${wm}钱 · ${lu.day}日${wd}钱 · ${shi}时${wh}钱`,
    timeGua: `农历${lu.year}年${lu.month}月${lu.day}日 ${shi}时（开奖 21:25）`,
    front: front.slice(0, 5).sort((a, b) => a - b),
    back: back.slice(0, 2).sort((a, b) => a - b),
    story: `称得${liang}两${qian}钱（${gz}年${wy}+${lu.month}月${wm}+${lu.day}日${wd}+${shi}时${wh}）；批语：${verse}`,
    verse, totalQian: total, seed, isEntertainment: true,
  };
}

module.exports = { chengguCast, DATA };
