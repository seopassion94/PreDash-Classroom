import test from 'node:test';
import assert from 'node:assert/strict';
import {cleanCodes,parseBackup,normalizePrices,evaluate,kstDay} from '../lib/score.mjs';
import {fetchHistory,parseOfficial} from '../lib/official.mjs';
const CODE='005930', ASOF='2026-11-12';
function rows(values,volumes=[]){return values.map((clpr,i)=>{const date=new Date(ASOF+'T00:00:00Z');date.setUTCDate(date.getUTCDate()-(values.length-1-i));return {srtnCd:CODE,basDt:date.toISOString().slice(0,10).replaceAll('-',''),clpr:String(clpr),trqu:String(volumes[i]??100)};});}
const assess=(values,v)=>evaluate(CODE,{price_rows:rows(values,v)},ASOF);
test('watchlist keeps six digit tickers, leading zeroes, order, uniqueness and max eight',()=>{
 assert.deepEqual(cleanCodes(['005930',' 000660 ','A353200',123,'005930',...'123456789'.split('').map(x=>x.repeat(6))]),['005930','000660','111111','222222','333333','444444','555555','666666']);
 assert.deepEqual(parseBackup('{"version":1,"codes":["005930","000660"],"names":{"005930":" 삼성전자 ","INVALID":"bad"}}'),{codes:['005930','000660'],names:{'005930':'삼성전자'}});
 assert.throws(()=>parseBackup('{"version":2,"codes":[]}'));
});
test('KST calendar day includes UTC rollover',()=>assert.equal(kstDay(new Date('2026-11-12T16:00:00Z')),'2026-11-13'));
test('normalization sorts, deduplicates and rejects invalid/future/other-ticker records',()=>{
 const good=rows([100,101]);
 const invalid=[{...good[0],srtnCd:'000660'},{...good[0],basDt:'20260230'},{...good[0],basDt:'20261113'},{...good[0],clpr:'NaN'},{...good[0],trqu:-1}];
 const n=normalizePrices([...good.reverse(),...good,...invalid],CODE,ASOF);
 assert.deepEqual(n.points.map(p=>p.close),[100,101]);assert.equal(n.rejected,5);
 assert.throws(()=>normalizePrices([...good,{...good[0],clpr:99}],CODE,ASOF),/상충/);
});
test('20-day crossover requires a crossing today, not simply trading above average',()=>{
 const crossing=assess([...Array(20).fill(100),110]);assert.equal(crossing.records[0].earned,15);
 const above=assess([...Array(20).fill(100),110,111]);assert.equal(above.records[0].status,'미충족');
 assert.equal(assess(Array(20).fill(100)).records[0].status,'미확인');
});
test('60-day rule is strict above, with exactly 60 observations sufficient',()=>{
 assert.equal(assess([...Array(59).fill(100),110]).records[1].earned,15);
 assert.equal(assess(Array(60).fill(100)).records[1].status,'미충족');
});
test('volume baseline excludes today, ratio boundary is inclusive and requires rising close',()=>{
 const prices=[...Array(20).fill(100),110],volumes=[...Array(20).fill(100),150];
 const r=assess(prices,volumes);assert.equal(r.records[2].earned,20);assert.equal(r.indicators.volumeRatio,1.5);
 assert.equal(assess([...Array(20).fill(110),100],volumes).records[2].earned,0);
 assert.equal(assess(prices,Array(21).fill(0)).records[2].status,'미확인');
});
test('flat RSI and MACD have finite values, no false rising/crossover signal',()=>{
 const r=assess(Array(60).fill(100));assert.equal(r.indicators.rsi,50);assert.equal(r.records[4].status,'미충족');assert.equal(r.records[5].earned,0);
});
test('freshness expires after 5 calendar days and missing evidence is never normalized into a higher score',()=>{
 const data={price_rows:rows(Array(60).fill(100))};
 assert.equal(evaluate(CODE,data,'2026-11-17').verified,70);
 const old=evaluate(CODE,data,'2026-11-18');assert.equal(old.verified,0);assert.equal(old.score,0);assert.equal(old.latest,null);
 const r=evaluate(CODE,data,ASOF);assert.equal(r.verified,70);assert.equal(r.classification,'판정 보류');assert.equal(r.records[3].status,'미확인');assert.equal(r.records[6].status,'미확인');assert.equal(r.records[7].status,'미확인');
});
test('investor flow needs same date and finite numeric quantities',()=>{
 const base={price_rows:rows(Array(60).fill(100)),flow:{date:ASOF,daily:{foreign:1,institution:2}}};
 assert.equal(evaluate(CODE,base,ASOF).records[3].earned,15);
 for(const flow of [{date:'2026-11-11',daily:{foreign:1,institution:2}},{date:ASOF,daily:{foreign:Infinity,institution:2}}])assert.equal(evaluate(CODE,{...base,flow},ASOF).records[3].status,'미확인');
});
test('official parser distinguishes authentication, limit and malformed response failures',()=>{
 for(const [text,status,code] of [['{}',403,'ACCESS_DENIED'],['{}',429,'RATE_LIMIT'],['<returnReasonCode>30</returnReasonCode>',200,'AUTH_ERROR'],['{}',200,'API_ERROR']])assert.throws(()=>parseOfficial(text,status),e=>e.code===code);
 assert.throws(()=>parseOfficial(JSON.stringify({response:{header:{resultCode:'00'},body:{totalCount:null}}})),e=>e.code==='FORMAT');
});
test('official fetch requests only approved host, correct ticker/window/version, preserves encoded key and paginates',async()=>{
 const calls=[],pageRows=rows([100,101]);
 const result=await fetchHistory({code:CODE,key:'test%2Bkey%3D',asof:ASOF,fetcher:async raw=>{const u=new URL(raw);calls.push(u);return new Response(JSON.stringify({response:{header:{resultCode:'00'},body:{totalCount:2,items:{item:pageRows[calls.length-1]}}}}));}});
 assert.equal(result.length,2);assert.equal(calls.length,2);
 assert.equal(calls[0].origin,'https://apis.data.go.kr');assert.equal(calls[0].searchParams.get('likeSrtnCd'),CODE);assert.equal(calls[0].searchParams.get('serviceKey'),'test+key=');assert.equal(calls[0].searchParams.get('endBasDt'),'20261113');assert.ok(calls[0].pathname.endsWith('getStockPriceInfo_V2'));
});
test('incomplete provider response fails closed and no-key request makes no network call',async()=>{
 await assert.rejects(()=>fetchHistory({code:CODE,key:'test',asof:ASOF,fetcher:async()=>new Response('{"response":{"header":{"resultCode":"00"},"body":{"totalCount":2,"items":{}}}}')}),e=>e.code==='INCOMPLETE');
 await assert.rejects(()=>fetchHistory({code:CODE,key:'',asof:ASOF,fetcher:()=>{throw new Error('unexpected network')}}),e=>e.code==='KEY_REQUIRED');
});
