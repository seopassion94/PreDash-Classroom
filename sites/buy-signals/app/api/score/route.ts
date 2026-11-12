import { env } from 'cloudflare:workers';
import { getChatGPTUser } from '../../chatgpt-auth';
import { evaluate,kstDay } from '../../../lib/score.mjs';
import { fetchHistory } from '../../../lib/official.mjs';
export const dynamic='force-dynamic';
const headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'};
export async function GET() {
  if(process.env.NODE_ENV==='production' && !await getChatGPTUser())return Response.json({error:'로그인이 필요합니다.'},{status:401,headers});
  return Response.json({configured:!!env.DATA_GO_KR_SERVICE_KEY,asof:kstDay()},{headers});
}
export async function POST(request:Request) {
  if(process.env.NODE_ENV==='production' && !await getChatGPTUser())return Response.json({error:'로그인이 필요합니다.'},{status:401,headers});
  const origin=request.headers.get('origin');
  if(origin && origin!==new URL(request.url).origin)return Response.json({error:'허용되지 않은 요청입니다.'},{status:403,headers});
  if(!request.headers.get('content-type')?.includes('application/json'))return Response.json({error:'JSON 요청이 필요합니다.'},{status:415,headers});
  try {
    const text=await request.text();
    if(text.length>6000)return Response.json({error:'요청 크기 초과'},{status:413,headers});
    const body=JSON.parse(text),code=typeof body.code==='string'?body.code:'';
    const key=typeof body.key==='string'?body.key:env.DATA_GO_KR_SERVICE_KEY??'';
    const version=body.version==='legacy'?'legacy':'v2',asof=kstDay();
    const price_rows=await fetchHistory({code,key,version,asof});
    const result=evaluate(code,{price_rows},asof);
    return Response.json({...result,asof,fetchedAt:new Date().toISOString(),source:version==='v2'?'금융위원회 주식시세정보 V2 (원천: KRX)':'금융위원회 주식시세정보 기존 API (원천: KRX)',version},{headers});
  } catch(error:unknown) {
    const e=error as {code?:string;message?:string};
    const safe=['KEY_REQUIRED','INVALID_CODE','AUTH_ERROR','ACCESS_DENIED','RATE_LIMIT','UPSTREAM','FORMAT','API_ERROR','NETWORK','TOO_LARGE','INCOMPLETE'].includes(e.code??'');
    return Response.json({code:safe?e.code:'CALCULATION_ERROR',error:safe?e.message:'응답 자료를 안전하게 검증하지 못해 계산을 중단했습니다.'},{status:e.code==='KEY_REQUIRED'||e.code==='INVALID_CODE'?400:502,headers});
  }
}
