/* 大乐透玄学工具箱（dlt-mystic，娱乐）—— round-31, 2026-09-25
   汇总各玄学流派出号，全部确定性可复现（种子=期号+卦/神参数）。
   方法清单：
     1. 六爻铜钱卦     liuyao.js（update.js 已集成，此处复用同口径生成清单）
     2. 梅花易数·时间起卦  传统农历口径：上卦=(年支数+农历月+农历日)%8、下卦=(…+时辰数)%8、
        动爻=(年+月+日+时)%6；体用生克→出号映射（自创娱乐规则，逐号可讲出处）
     3. 小六壬(诸葛马前课)  大安/留连/速喜/赤口/小吉/空亡，月→日→时三掐；
        三宫神序→号码映射（自创娱乐规则）
     4. 紫微斗数开奖盘  ziwei.js v2 排盘（以开奖日 21:25 亥时为"开奖生辰"），fatePick 出号
     5. 称骨歌          chenggu.js：开奖日农历年月日时四柱骨重相加查批语（51/52级落库），
        四柱骨重+总骨重映射出号（自创娱乐规则）
     6. 诸葛神数        zhuge.js：秘本384签落库；上期前区首/末号+后区末号拟"三字"按笔画位
        定签数（自创娱乐口径），签号与上期号码交织出号
   诚实声明：大乐透为独立随机事件，以上均为统计娱乐，不构成投注建议。
   用法: node dlt-mystic.js [期号]   （默认下一期） */
'use strict';
const fs = require('fs');
const path = require('path');
const DLT = '/Users/mac/dream/dlt-analyzer/.agents/skills/dlt-analyzer';
const LiuYao = require('/Users/mac/dream/ssq-analyzer/liuyao.js');
const Ziwei = require('/Users/mac/dream/ssq-analyzer/ziwei.js');
const Chenggu = require('./chenggu.js');
const Zhuge = require('./zhuge.js');

const STEMS = '甲乙丙丁戊己庚辛壬癸';
const BRANCHES = '子丑寅卯辰巳午未申酉戌亥';
const SHICHEN = ['子','丑','寅','卯','辰','巳','午','未','申','酉','戌','亥'];
const XIAOLIUREN = ['大安','留连','速喜','赤口','小吉','空亡'];

function fnv1a(s){let h=2166136261;for(const ch of unescape(encodeURIComponent(s))){h^=ch.charCodeAt(0);h=Math.imul(h,16777619);}return h>>>0;}
function mulberry32(a){return function(){a|=0;a=a+0x6D2B79F5|0;let t=Math.imul(a^a>>>15,1|a);t=t+Math.imul(t^t>>>7,61|t)^0;return((t^t>>>14)>>>0)/4294967296;};}
function pickN(maxn, m, rng){
  const a = Array.from({length:maxn},(_,i)=>i+1);
  for(let i=maxn-1;i>0;i--){ const j=(rng()*(i+1))|0; [a[i],a[j]]=[a[j],a[i]]; }
  return a.slice(0,m).sort((x,y)=>x-y);
}
function coinsOf(d){  // 与 update.js 同口径：前区和奇=背、后区和奇=背
  return [ d.front.reduce((a,b)=>a+b,0)%2===1, d.back.reduce((a,b)=>a+b,0)%2===1 ];
}

/* ---------- 1. 六爻铜钱卦（复用 update.js 口径） ---------- */
function liuyaoCast(draws, issue){
  const g = LiuYao.divine(draws.slice(-9), coinsOf, issue,
    {frontMax:35, frontN:5, backMax:12, backN:2},
    nextDrawTime(draws, issue));
  return {
    method:'六爻铜钱卦', benGua:g.benGua, bianGua:g.bianGua||'—',
    moving:g.movingIdx.join('、')||'无动爻',
    timeGua:g.timeGua ? `起始卦${g.timeGua.name}·动爻${g.timeGua.dongYao}` : '—',
    front:g.front, back:g.back,
    story:`前九期18枚铜钱起本卦${g.benGua}${g.bianGua?'变'+g.bianGua:''}，${g.movingIdx.join('、')||'静卦'}`,
    seed:g.seed, isEntertainment:true,
  };
}

/* ---------- 2. 梅花易数·时间起卦（传统农历口径） ---------- */
function meihuaTimeCast(draws, issue){
  const t = nextDrawTime(draws, issue);
  const lu = Ziwei.solarToLunar(t.y, t.m, t.d);
  const zhiN = ((lu.year - 4) % 12) + 1;                 // 年支数: 子1…亥12
  const shiN = Math.floor(((t.hour + 1) % 24) / 2) + 1;  // 时辰数: 子1…亥12
  const sUp = zhiN + lu.month + lu.day;
  const sLow = sUp + shiN;
  const triOf = n => LiuYao.TRI.find(tr => tr.num === ((n - 1) % 8) + 1);
  const up = triOf(sUp), low = triOf(sLow);
  const dong = ((sLow - 1) % 6) + 1;
  const yao = [...low.b, ...up.b].map(Number);
  yao[dong - 1] = 1 - yao[dong - 1];
  const low2 = LiuYao.TRI.find(tr => tr.b === yao.slice(0,3).join(''));
  const up2 = LiuYao.TRI.find(tr => tr.b === yao.slice(3).join(''));
  const dongInUpper = dong > 3;
  const tiTi = dongInUpper ? low : up;      // 体卦=动爻不在之卦
  const tiYong = dongInUpper ? up : low;    // 用卦=动爻所在之卦
  const seed = (fnv1a(`meihua|${issue}|${sUp}|${sLow}|${dong}`) ^ (up.num*4096 + low.num*64 + dong)) >>> 0;
  const rng = mulberry32(seed);
  // 出号映射（自创娱乐）：体卦数、用卦数、变卦上下卦数、体+用+动 和值 → 号段映射
  const picks = [tiTi.num, tiYong.num, up2.num, low2.num, (tiTi.num + tiYong.num + dong)]
    .map(x => ((x - 1) % 35) + 1);
  const front = [...new Set(picks)];
  for (const n of pickN(35, 35, rng)) { if (front.length >= 5) break; if (!front.includes(n)) front.push(n); }
  const backPicks = [tiYong.num, low2.num].map(x => ((x - 1) % 12) + 1);
  const back = [...new Set(backPicks)];
  for (const n of pickN(12, 12, rng)) { if (back.length >= 2) break; if (!back.includes(n)) back.push(n); }
  return {
    method:'梅花易数·时间起卦', benGua:LiuYao.HEX64[up.name][low.name], bianGua:LiuYao.HEX64[up2.name][low2.name],
    moving:`${['初爻','二爻','三爻','四爻','五爻','上爻'][dong-1]}`,
    timeGua:`农历${lu.year}年${lu.month}月${lu.day}日 ${SHICHEN[shiN-1]}时 · 上卦${up.name}(${sUp}%8) 下卦${low.name}(${sLow}%8) 动爻${dong}`,
    front:front.slice(0,5).sort((a,b)=>a-b), back:back.slice(0,2).sort((a,b)=>a-b),
    story:`体卦${tiTi.name}·用卦${tiYong.name}·动爻第${dong}爻；体${tiTi.num}/用${tiYong.num}/变${up2.num}${low2.num}/和值入号`,
    seed, isEntertainment:true,
  };
}

/* ---------- 3. 小六壬（诸葛马前课） ---------- */
function xiaoliurenCast(draws, issue){
  const t = nextDrawTime(draws, issue);
  const lu = Ziwei.solarToLunar(t.y, t.m, t.d);
  const idxOf = (start, count) => (start - 1 + count - 1) % 6;   // 从大安起顺数
  const mPal = idxOf(1, lu.month);            // 正月起大安，数至占月
  const dPal = idxOf(mPal + 1, lu.day);       // 月宫起初一，数至占日
  const shiN = Math.floor(((t.hour + 1) % 24) / 2) + 1;
  const hPal = idxOf(dPal + 1, shiN);         // 日宫起子时，数至占时
  const gods = [XIAOLIUREN[mPal], XIAOLIUREN[dPal], XIAOLIUREN[hPal]];
  const nums = [mPal+1, dPal+1, hPal+1];      // 神序 1..6
  const seed = fnv1a(`xlr|${issue}|${mPal}|${dPal}|${hPal}`);
  const rng = mulberry32(seed);
  // 出号映射（自创娱乐）：神序 a→{a, a+7, a+14, a+21, a+28} 五级阶梯取号
  const front = [];
  for (const n of nums) for (const k of [0,7,14,21,28]) {
    const v = ((n + k - 1) % 35) + 1;
    if (!front.includes(v) && front.length < 5) front.push(v);
  }
  for (const n of pickN(35, 35, rng)) { if (front.length >= 5) break; if (!front.includes(n)) front.push(n); }
  const back = [];
  for (const n of nums) { const v = ((n - 1) % 12) + 1; if (!back.includes(v)) back.push(v); }
  for (const n of pickN(12, 12, rng)) { if (back.length >= 2) break; if (!back.includes(n)) back.push(n); }
  return {
    method:'小六壬(诸葛马前课)', benGua:`月宫${gods[0]}→日宫${gods[1]}→时宫${gods[2]}`, bianGua:'—',
    moving:'三掐', timeGua:`农历${lu.month}月${lu.day}日 ${SHICHEN[shiN-1]}时`,
    front:front.slice(0,5).sort((a,b)=>a-b), back:back.slice(0,2).sort((a,b)=>a-b),
    story:`神序${nums.join('/')} → 阶梯映射(a+0/7/14/21/28)%35`,
    seed, isEntertainment:true,
  };
}

/* ---------- 4. 紫微斗数开奖盘 ---------- */
function ziweiCast(draws, issue){
  const t = nextDrawTime(draws, issue);
  const tk = Ziwei.ticket({ year:t.y, month:t.m, day:t.d, hour:21, gender:'unknown' }, 'dlt', issue);
  return {
    method:'紫微斗数开奖盘', benGua:tk.chart.fiveElement, bianGua:'—',
    moving:`紫微在${tk.chart.ziwei}`, timeGua:`${tk.chart.lunar} · ${tk.chart.ganzhi}年 亥时`,
    front:tk.red, back:tk.blue,
    story:`命宫${tk.chart.mingong} 身宫${tk.chart.shengong}；${tk.fateStory}`,
    seed:tk.seed, isEntertainment:true,
  };
}

/* ---------- 期号 → 开奖时间（周一三六 21:25） ---------- */
function nextDrawTime(draws, issue){
  const last = draws[draws.length-1];
  if (String(issue) <= last.num) {          // 历史期：用实际日期
    const d = draws.find(x => String(x.num) === String(issue));
    if (d) { const dt = new Date(d.date + 'T21:25:00+08:00');
      return { y:dt.getFullYear(), m:dt.getMonth()+1, d:dt.getDate(), hour:21 }; }
  }
  let dt = new Date(last.date + 'T21:25:00+08:00');
  do { dt = new Date(dt.getTime() + 864e5); } while (![1,3,6].includes(dt.getDay()));
  return { y:dt.getFullYear(), m:dt.getMonth()+1, d:dt.getDate(), hour:21 };
}

/* ---------- 主入口 ---------- */
function allCast(issue){
  const draws = JSON.parse(fs.readFileSync(path.join(DLT, 'data/draws.json'))).draws;
  return {
    issue:String(issue),
    generatedAt:new Date().toISOString().slice(0,10),
    disclaimer:'大乐透为独立随机事件，玄学方法仅供统计娱乐，不构成投注建议',
    casts:[ liuyaoCast(draws, issue), meihuaTimeCast(draws, issue),
            xiaoliurenCast(draws, issue), ziweiCast(draws, issue),
            Chenggu.chengguCast(draws, issue, nextDrawTime),
            Zhuge.zhugeCast(draws, issue, nextDrawTime) ],
  };
}
module.exports = { allCast, liuyaoCast, meihuaTimeCast, xiaoliurenCast, ziweiCast,
  chengguCast: Chenggu.chengguCast, zhugeCast: Zhuge.zhugeCast, nextDrawTime };
if (require.main === module) {
  const draws = JSON.parse(fs.readFileSync(path.join(DLT, 'data/draws.json'))).draws;
  const issue = process.argv[2] || String(Number(draws[draws.length-1].num) + 1);
  console.log(JSON.stringify(allCast(issue), null, 1));
}
