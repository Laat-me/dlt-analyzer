/* 大乐透覆盖优化模块（双色球「蓝球保底+红球覆盖」思想的移植）
   前区 35 选 5 / 后区 12 选 2：
   - 后区单值 12 全覆盖：模型记录后区槽位均衡轮换（类比双色球蓝球 16 全覆盖）
   - 前区 35 值全覆盖修补（热号池冷号缺席时低损失替换）
   - 后区全对保底集：C(12,2)=66 个号码对，用 k 个三元组覆盖（覆盖设计 C(12,3,2)，下界 24）
     → 任何开奖后区对都落在某个三元组内 → 该注后区 2/2 全中，保底八等奖
   注意成本：24 个 5+3 复式 = 144 元/期，保底 5 元+前区机会，期望为负，是否购买由用户决定。 */
'use strict';
const NF = 35, NB = 12;

/* 近5×3+近10×1.5 热号分（与双色球 v2_hot 同型） */
function hotScore(draws){
  const f = new Float64Array(NF+1), b = new Float64Array(NB+1);
  draws.slice(-10).forEach((d, i) => {
    const w = i >= 5 ? 1.5 : 3;
    d.front.forEach(n => f[n] += w);
    d.back.forEach(n => b[n] += w);
  });
  return { f, b };
}
function topN(score, maxn, n){
  return Array.from({length:maxn},(_,i)=>i+1).sort((a,b)=>score[b]-score[a]||a-b).slice(0,n);
}
function okFront5(r){
  let odd = 0, z1 = 0, z2 = 0, s = 0;
  for(const n of r){ if(n%2) odd++; if(n<=12) z1++; else if(n<=24) z2++; s += n; }
  const z3 = 5-z1-z2;
  return odd>=2 && odd<=3 && z1>=1 && z1<=3 && z2>=1 && z2<=3 && z3>=1 && z3<=3 && s>=55 && s<=135 && r[4]-r[0]>=14;
}

/* 后区全对保底集：C(12,3,2) 覆盖设计（下界 24，退火已求得最优 24 组、每点恰好 6 次）。
   任何开奖后区对（66 对之一）必落在某个三元组内 → 对应 5+3 复式注后区 2/2 全中。 */
const OPTIMAL_24 = [[4,5,10],[3,9,11],[5,6,12],[2,8,9],[3,5,8],[1,3,10],[2,5,11],[1,5,7],[2,4,7],[1,4,6],[3,6,7],[3,4,8],[2,6,10],[1,7,8],[4,9,10],[1,2,11],[7,10,11],[5,6,9],[6,8,11],[7,9,12],[4,11,12],[8,10,12],[2,3,12],[1,9,12]];
function backPairCoverTriplets(){
  if(coversAllPairs(OPTIMAL_24)) return OPTIMAL_24.map(t=>t.slice());
  // 兜底：贪心集合覆盖 + 2→1 压缩
  const pairs = [];
  for(let i=1;i<=NB;i++) for(let j=i+1;j<=NB;j++) pairs.push([i,j]);
  const uncovered = new Set(pairs.map(p=>p[0]*16+p[1]));
  const triples = [];
  while(uncovered.size){
    let best=null, bestGain=-1;
    for(let a=1;a<=NB;a++) for(let c=a+1;c<=NB;c++) for(let d=c+1;d<=NB;d++){
      let gain=0;
      for(const [x,y] of [[a,c],[a,d],[c,d]]) if(uncovered.has(x*16+y)) gain++;
      if(gain>bestGain){ bestGain=gain; best=[a,c,d]; }
    }
    triples.push(best);
    for(const [x,y] of [[best[0],best[1]],[best[0],best[2]],[best[1],best[2]]]) uncovered.delete(x*16+y);
  }
  return triples;
}
function coversAllPairs(triples){
  const seen = new Set();
  for(const t of triples) for(const [x,y] of [[t[0],t[1]],[t[0],t[2]],[t[1],t[2]]]) seen.add(x*16+y);
  return seen.size === 66;
}

/* 模型记录覆盖后处理（原地修改，六爻记录由调用方排除）：
   - 后区：单遍贪心——每槽选「新值×3 + 新号码对×1」最大的组合，同时完成 12 值覆盖与对子展开
   - 前区：35 值低损失修补（尽力而为；槽位不足时无法全满，保底块补齐） */
function applyCoverage(records, draws){
  const { f:sf, b:sb } = hotScore(draws);
  // 后区贪心（值覆盖优先，对子展开其次）
  const valSeen = new Set(), pairSeen = new Set();
  for(const r of records){
    const k = r.predictedBack.length;                    // 2 或 3
    let best = null, bestScore = -Infinity;
    const gen = k === 2
      ? (()=>{ const out=[]; for(let a=1;a<=NB;a++)for(let b=a+1;b<=NB;b++)out.push([a,b]); return out; })()
      : (()=>{ const out=[]; for(let a=1;a<=NB;a++)for(let b=a+1;b<=NB;b++)for(let c=b+1;c<=NB;c++)out.push([a,b,c]); return out; })();
    for(const combo of gen){
      let newVals = 0, newPairs = 0;
      for(const v of combo) if(!valSeen.has(v)) newVals++;
      for(let i=0;i<combo.length;i++)for(let j=i+1;j<combo.length;j++) if(!pairSeen.has(combo[i]*16+combo[j])) newPairs++;
      const score = newVals*3 + newPairs + 0.01*combo.reduce((a,n)=>a+sb[n],0);
      if(score > bestScore){ bestScore = score; best = combo; }
    }
    best.forEach(v=>valSeen.add(v));
    for(let i=0;i<best.length;i++)for(let j=i+1;j<best.length;j++) pairSeen.add(best[i]*16+best[j]);
    r.predictedBack = best.slice().sort((a,b)=>a-b);
    r.note = (r.note||'') + '｜覆盖优化:后区12值+对子展开';
  }
  // 前区修补（带计数防互踢；槽位不足时尽力）
  const fcnt = new Map();
  records.forEach(r=>(r.predictedFront||[]).forEach(n=>fcnt.set(n,(fcnt.get(n)||0)+1)));
  for(let m=1;m<=NF;m++){
    if((fcnt.get(m)||0)>0) continue;
    let best=null,bestLoss=Infinity;
    for(const r of records){
      const pf=r.predictedFront;
      for(let i=0;i<pf.length;i++){
        const old=pf[i];
        if((fcnt.get(old)||0)<2) continue;
        const nr=pf.slice(); nr[i]=m; nr.sort((a,b)=>a-b);
        if(new Set(nr).size<pf.length || (pf.length===5 && !okFront5(nr))) continue;
        const loss=sf[old]-sf[m];
        if(loss<bestLoss){bestLoss=loss;best={r,nr,old};}
      }
    }
    if(best){ best.r.predictedFront=best.nr; fcnt.set(best.old,(fcnt.get(best.old)||1)-1); fcnt.set(m,1); }
  }
  records.forEach(r=>{ if(!r.note||!r.note.includes('前区35值')) r.note=(r.note||'')+'｜前区35值尽力修补'; });
}

/* 保底块出票：24 个 5+3 复式（后区=保底三元组，前区=热池 top12 枚举 C(12,5) 选 pair 展开最优 + 35 值修补） */
function buildGuaranteeBlock(draws, targetDrawNum, triples){
  const { f:sf } = hotScore(draws);
  const rank = topN(sf, NF, 24);                     // 前 24 热号
  const pairCnt = new Map();
  const fronts = triples.map((_, ri)=>{
    // 奇数注用 top1-12 池，偶数注用 top13-24 池，增加组合多样性
    const pool = ri % 2 ? rank.slice(12, 24) : rank.slice(0, 12);
    let best = null, bestScore = -Infinity;
    (function rec(start, cur){
      if(cur.length === 5){
        const r5 = cur.slice().sort((a,b)=>a-b);
        if(!okFront5(r5)) return;
        let newPairs = 0;
        for(let i=0;i<5;i++)for(let j=i+1;j<5;j++) if(!pairCnt.has(r5[i]*64+r5[j])) newPairs++;
        const score = newPairs + 0.01*r5.reduce((a,n)=>a+sf[n],0);
        if(score > bestScore){ bestScore = score; best = r5; }
        return;
      }
      for(let i=start;i<pool.length;i++){ cur.push(pool[i]); rec(i+1,cur); cur.pop(); }
    })(0,[]);
    if(!best) best = pool.slice(0,5).sort((a,b)=>a-b);
    for(let i=0;i<5;i++)for(let j=i+1;j<5;j++) pairCnt.set(best[i]*64+best[j],(pairCnt.get(best[i]*64+best[j])||0)+1);
    return best;
  });
  const records = triples.map((t,i)=>({
    predictedAt: new Date().toISOString().slice(0,10), targetDrawNum: String(targetDrawNum),
    model: `🛡 后区全对保底·${String(i+1).padStart(2,'0')}`, mode: '5+3',
    predictedFront: fronts[i], predictedBack: t.slice().sort((a,b)=>a-b),
    verified: false, isCoverage: true,
    note: `后区三元组${t.join('-')} ⊂ 66对全覆盖集(${triples.length}组) → 该注后区必 2/2 全中保底`
  }));
  // 保底块前区 35 值全覆盖修补（120 槽位，必可全满）
  const fcnt = new Map();
  records.forEach(r=>r.predictedFront.forEach(n=>fcnt.set(n,(fcnt.get(n)||0)+1)));
  for(let m=1;m<=NF;m++){
    if((fcnt.get(m)||0)>0) continue;
    let best=null,bestLoss=Infinity;
    for(const r of records){
      for(let i=0;i<5;i++){
        const old=r.predictedFront[i];
        if((fcnt.get(old)||0)<2) continue;
        const nr=r.predictedFront.slice(); nr[i]=m; nr.sort((a,b)=>a-b);
        if(new Set(nr).size<5 || !okFront5(nr)) continue;
        const loss=sf[old]-sf[m];
        if(loss<bestLoss){bestLoss=loss;best={r,nr,old};}
      }
    }
    if(best){ best.r.predictedFront=best.nr; fcnt.set(best.old,(fcnt.get(best.old)||1)-1); fcnt.set(m,1); }
  }
  return records;
}

module.exports = { NF, NB, hotScore, okFront5, backPairCoverTriplets, coversAllPairs, applyCoverage, buildGuaranteeBlock };
