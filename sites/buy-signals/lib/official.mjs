export const ENDPOINTS={v2:'https://apis.data.go.kr/1160100/GetStockSecuritiesInfoService_V2/getStockPriceInfo_V2',legacy:'https://apis.data.go.kr/1160100/service/GetStockSecuritiesInfoService/getStockPriceInfo'};
export class DataError extends Error { constructor(code,message){super(message);this.code=code;} }
export function parseOfficial(text,status=200) {
  if(status===401||status===403)throw new DataError('ACCESS_DENIED',`공식 시세 API 접근 거절(HTTP ${status}). 인증키·서비스 활용승인·IP 제한을 확인하세요.`);
  if(status===429)throw new DataError('RATE_LIMIT','공식 시세 API 호출 한도 초과. 잠시 후 다시 조회하세요.');
  if(status>=400)throw new DataError('UPSTREAM',`공식 시세 제공 서버 오류(HTTP ${status}). 잠시 후 다시 조회하세요.`);
  let payload;
  try{payload=JSON.parse(text);}catch{
    const reason=text.match(/<returnReasonCode>([^<]*)</)?.[1];
    if(['20','30','31','32'].includes(reason))throw new DataError('AUTH_ERROR','시세 인증키·활용승인·키 유효기간·IP 제한을 확인하세요.');
    if(reason==='22')throw new DataError('RATE_LIMIT','공식 시세 API 호출 한도 초과.');
    throw new DataError('FORMAT','공식 시세 API가 JSON 대신 오류 또는 알 수 없는 형식을 반환했습니다. 연결 설정의 API 버전과 승인 상태를 확인하세요.');
  }
  const response=payload?.response;
  if(!response?.header||!['00','0'].includes(String(response.header.resultCode)))throw new DataError('API_ERROR','공식 시세 API가 정상 결과를 반환하지 않았습니다. 인증키·서비스 활용승인·요청 한도를 확인하세요.');
  const body=response.body;
  if(!body || body.totalCount===null || body.totalCount===undefined || body.totalCount==='' || !Number.isInteger(Number(body.totalCount)) || Number(body.totalCount)<0)throw new DataError('FORMAT','공식 시세 응답 구조 또는 전체 건수를 확인할 수 없습니다.');
  let rows=body.items?.item ?? [];
  if(rows && !Array.isArray(rows) && typeof rows==='object')rows=[rows];
  if(!Array.isArray(rows))throw new DataError('FORMAT','공식 시세 목록 형식이 올바르지 않습니다.');
  return {rows,total:Number(body.totalCount)};
}
export async function fetchHistory({code,key,version='v2',asof,fetcher=fetch}) {
  if(!/^[0-9]{6}$/.test(code))throw new DataError('INVALID_CODE','국내 주식 숫자 6자리 종목코드를 입력하세요.');
  if(!key?.trim())throw new DataError('KEY_REQUIRED','공식 시세 인증키를 연결하세요.');
  let decoded=key.trim();try{decoded=decodeURIComponent(decoded);}catch{}
  const begin=new Date(asof+'T00:00:00Z');begin.setUTCDate(begin.getUTCDate()-400);
  const end=new Date(asof+'T00:00:00Z');end.setUTCDate(end.getUTCDate()+1);
  const stamp=d=>d.toISOString().slice(0,10).replaceAll('-','');
  const rows=[];
  for(let page=1;page<=4;page++) {
    const url=new URL(ENDPOINTS[version]??ENDPOINTS.v2);
    url.search=new URLSearchParams({serviceKey:decoded,resultType:'json',numOfRows:'500',pageNo:String(page),likeSrtnCd:code,beginBasDt:stamp(begin),endBasDt:stamp(end)}).toString();
    let response,text;
    try{response=await fetcher(url.toString(),{signal:AbortSignal.timeout(20000),headers:{Accept:'application/json'},cache:'no-store'});text=await response.text();}
    catch{throw new DataError('NETWORK','공식 시세 서버에 연결하지 못했거나 20초 내 응답이 없었습니다. 잠시 후 다시 조회하세요.');}
    if(text.length>4000000)throw new DataError('TOO_LARGE','공식 응답 크기가 제한을 초과했습니다.');
    const data=parseOfficial(text,response.status);rows.push(...data.rows);
    if(rows.length>=data.total)return rows;
    if(data.rows.length===0)throw new DataError('INCOMPLETE','전체 일별 자료를 수신하지 못해 점수 계산을 보류했습니다.');
  }
  throw new DataError('INCOMPLETE','전체 일별 자료를 수신하지 못해 점수 계산을 보류했습니다.');
}
