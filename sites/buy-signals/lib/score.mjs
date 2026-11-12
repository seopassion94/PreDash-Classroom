export const RULES = [
  ['20일 이동평균선 상향 돌파',15,'추세','전일 종가 ≤ 전일 20일선, 당일 종가 > 당일 20일선'],
  ['60일 이동평균선 위에서 안착',15,'추세','당일 종가 > 당일 60일 단순이동평균'],
  ['거래량이 20일 평균의 1.5배 이상',20,'거래량','직전 20거래일 평균 대비 1.5배 이상이며 전일 대비 종가 상승'],
  ['외국인·기관 동반 순매수',15,'수급','시세 기준일과 동일한 날의 외국인·기관 순매수 모두 양수'],
  ['RSI 40~65이며 상승 중',10,'모멘텀','RSI(14)가 40~65 범위이고 전일보다 상승'],
  ['MACD 골든크로스',10,'모멘텀','MACD(12,26)가 당일 신호선(9)을 상향 돌파'],
  ['영업이익 성장 또는 전망 상향',10,'실적','공식 동기 영업이익 증가율이 양수'],
  ['지지선·손절 기준이 명확함',5,'위험 관리','사용자가 진입가·손절가·지지선을 별도로 검증'],
];
export function kstDay(now = new Date()) { return new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Seoul',year:'numeric',month:'2-digit',day:'2-digit'}).format(now); }
const dayValue = x => Date.parse(x+'T00:00:00Z');
const finiteNumber = x => typeof x==='number' && Number.isFinite(x);
const num = x => { if(typeof x!=='number' && typeof x!=='string')return NaN; if(String(x).trim()==='')return NaN; return Number(String(x).replaceAll(',','')); };
export function cleanCodes(values) {
  const result=[];
  for(const value of values ?? []) { const code=String(value).trim(); if(/^[0-9]{6}$/.test(code) && !result.includes(code))result.push(code); if(result.length===8)break; }
  return result;
}
export function parseBackup(text) {
  const v=JSON.parse(text);
  if(!v || v.version!==1 || !Array.isArray(v.codes))throw new Error('PreDash 관심종목 백업(version 1) 파일을 선택하세요.');
  const codes=cleanCodes(v.codes), names={};
  for(const c of codes)if(typeof v.names?.[c]==='string' && v.names[c].trim())names[c]=v.names[c].trim().slice(0,80);
  return {codes,names};
}
export function normalizePrices(rows,code,asof=kstDay()) {
  const points=new Map(); let rejected=0;
  for(const row of rows ?? []) {
    if(String(row.srtnCd??'').replace(/^A/,'').padStart(6,'0')!==code) {rejected++;continue;}
    const raw=String(row.basDt??''), date=raw.replace(/^(\d{4})(\d{2})(\d{2})$/,'$1-$2-$3');
    const close=num(row.clpr), volume=num(row.trqu);
    if(!/^\d{8}$/.test(raw)||!Number.isFinite(dayValue(date))||new Date(dayValue(date)).toISOString().slice(0,10)!==date||date>asof||!Number.isFinite(close)||close<=0||!Number.isFinite(volume)||volume<0){rejected++;continue;}
    const p={date,close,volume,name:typeof row.itmsNm==='string'?row.itmsNm.slice(0,80):'',market:typeof row.mrktCtg==='string'?row.mrktCtg:''};
    const old=points.get(date);
    if(old && (old.close!==close || old.volume!==volume))throw new Error('동일 날짜에 상충하는 공식 시세가 있어 계산을 중단했습니다.');
    points.set(date,p);
  }
  return {points:[...points.values()].sort((a,b)=>a.date.localeCompare(b.date)),rejected};
}
const mean = a => a.reduce((s,n)=>s+n,0)/a.length;
export const ema = (values,alpha) => values.reduce((a,v,i)=>{a.push(i?alpha*v+(1-alpha)*a[i-1]:v);return a;},[]);
const fmt = (n,d=0) => n.toLocaleString('ko-KR',{maximumFractionDigits:d});
export function evaluate(code,item={},asof=kstDay()) {
  const records=RULES.map(([label,weight,group,formula],id)=>({id,label,weight,group,formula,status:'미확인',earned:0,evidence:'공식 일별 시세 연결 후 확인'}));
  const {points,rejected}=normalizePrices(item.price_rows,code,asof);
  const end=points.at(-1), fresh=!!end && points.length>=2 && (dayValue(asof)-dayValue(end.date))/86400000<=5;
  const apply=(i,yes,evidence)=>Object.assign(records[i],{status:yes?'충족':'미충족',earned:yes?RULES[i][1]:0,evidence});
  const indicators={};
  if(fresh) {
    const c=points.map(x=>x.close),v=points.map(x=>x.volume),last=c.at(-1),previous=c.at(-2);
    for(const [days,idx] of [[20,0],[60,1]]) {
      if(c.length>=(days===20?21:60)) {
        const ma=mean(c.slice(-days)); indicators['ma'+days]=ma;
        const prevMA=mean(c.slice(-days-1,-1));
        apply(idx,days===20?previous<=prevMA && last>ma:last>ma,days===20?`전일 ${fmt(previous)}원 / 20일선 ${fmt(prevMA)}원 → 당일 ${fmt(last)}원 / 20일선 ${fmt(ma)}원`:`종가 ${fmt(last)}원 / 60일선 ${fmt(ma)}원`);
      } else records[idx].evidence=`최소 ${days===20?21:60}거래일 필요 · 현재 ${c.length}일`;
    }
    if(v.length>=21) {
      const baseline=mean(v.slice(-21,-1));
      if(baseline>0){const multiple=v.at(-1)/baseline;indicators.volumeRatio=multiple; apply(2,last>previous && multiple>=1.5,`거래량 ${fmt(v.at(-1))}주 / 직전 20일 평균 ${fmt(baseline)}주 = ${multiple.toFixed(2)}배 · 종가 ${last>previous?'상승':'상승 아님'}`);}
      else records[2].evidence='직전 20일 평균 거래량이 0이므로 배수 산정 불가';
    } else records[2].evidence=`최소 21거래일 필요 · 현재 ${c.length}일`;
    if(c.length>=16) {
      const diff=c.slice(1).map((x,i)=>x-c[i]);
      const ups=ema(diff.map(x=>Math.max(0,x)),1/14),downs=ema(diff.map(x=>Math.max(0,-x)),1/14);
      const rsi=(u,d)=>d===0?(u>0?100:50):100-100/(1+u/d);
      const r1=rsi(ups.at(-1),downs.at(-1)),r0=rsi(ups.at(-2),downs.at(-2));
      indicators.rsi=r1;apply(4,r1>=40 && r1<=65 && r1>r0,`RSI(14) ${r1.toFixed(1)} / 전일 ${r0.toFixed(1)} · 초기값은 첫 변동값 기준`);
    } else records[4].evidence=`최소 16거래일 필요 · 현재 ${c.length}일`;
    if(c.length>=35) {
      const fast=ema(c,2/13),slow=ema(c,2/27),macd=fast.map((x,i)=>x-slow[i]),signal=ema(macd,2/10);
      indicators.macd=macd.at(-1);indicators.macdSignal=signal.at(-1);
      apply(5,macd.at(-2)<=signal.at(-2) && macd.at(-1)>signal.at(-1),`MACD ${fmt(macd.at(-2),2)} → ${fmt(macd.at(-1),2)} / 신호선 ${fmt(signal.at(-2),2)} → ${fmt(signal.at(-1),2)}`);
    } else records[5].evidence=`최소 35거래일 필요 · 현재 ${c.length}일`;
  } else for(const i of [0,1,2,4,5])records[i].evidence=!end?'유효한 공식 시세 없음':points.length<2?'최소 2거래일 필요':`최근 시세 ${end.date} · 5일 초과 경과로 신호 계산 보류`;
  records[3].evidence='동일 기준일의 KIS 일별 수급 미연결';
  if(fresh && item.flow?.date===end.date && ['foreign','institution'].every(k=>finiteNumber(item.flow?.daily?.[k]))) {
    const {foreign,institution}=item.flow.daily;
    apply(3,foreign>0 && institution>0,`외국인 ${fmt(foreign)}주 / 기관 ${fmt(institution)}주 · ${end.date}`);
  }
  records[6].evidence='DART 동기 영업이익 자료 미연결';
  if(finiteNumber(item.metrics?.growth_pct))apply(6,item.metrics.growth_pct>0,`동기 영업이익 증가율 ${item.metrics.growth_pct.toFixed(1)}% · ${item.metrics.year}년 ${item.metrics.quarter}분기 누적`);
  records[7].evidence='진입가·손절가·지지선은 사용자가 별도로 검증 · 자동 가점 없음';
  const score=records.reduce((s,r)=>s+r.earned,0),verified=records.reduce((s,r)=>s+(r.status==='미확인'?0:r.weight),0);
  return {code,records,score,verified,latest:fresh?end.date:null,lastDate:end?.date??null,fresh,points,rejected,indicators,classification:verified<80?'판정 보류':score>=80?'매수 후보':score>=60?'추가 확인':'관망·검토'};
}
