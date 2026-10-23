"""Automatic evidence-based buy-signal scorecard from PreDash daily watch data."""
from datetime import datetime, date
from math import isfinite
from zoneinfo import ZoneInfo
import re
import pandas as pd
import streamlit as st

RULES = [
    ("20일 이동평균선 상향 돌파",15),
    ("60일 이동평균선 위에서 안착",15),
    ("거래량이 20일 평균의 1.5배 이상",20),
    ("외국인·기관 동반 순매수",15),
    ("RSI 40~65이며 상승 중",10),
    ("MACD 골든크로스",10),
    ("영업이익 성장 또는 전망 상향",10),
    ("지지선·손절 기준이 명확함",5),
]

def _prices(rows, code):
    points = {}
    for row in rows or []:
        if str(row.get("srtnCd","")).removeprefix("A").zfill(6) != code: continue
        try:
            stamp = datetime.strptime(str(row["basDt"]),"%Y%m%d").date()
            price = float(str(row["clpr"]).replace(",",""))
            vol = float(str(row["trqu"]).replace(",",""))
            if not (isfinite(price) and isfinite(vol) and price>0 and vol>=0): continue
            if stamp in points and points[stamp] != (price,vol):
                raise ValueError("동일 날짜에 상충하는 시세가 있습니다.")
            points[stamp]=(price,vol)
        except (KeyError,TypeError,ValueError):
            continue
    return sorted(points.items())

def evaluate(code, item, asof=None):
    """Return (records, total, verified maximum, date), None for unverified criteria."""
    asof = asof or datetime.now(ZoneInfo("Asia/Seoul")).date()
    result=[{"조건":label,"배점":points,"상태":"미확인","획득":0,"근거":"데이터 부족"} for label,points in RULES]
    pairs=[(d,p) for d,p in _prices(item.get("price_rows"),code) if d<=asof]
    if len(pairs)>=2 and (asof-pairs[-1][0]).days<=5:
        dates=[d for d,_ in pairs]
        closes=pd.Series([x[0] for _,x in pairs],dtype=float)
        volumes=pd.Series([x[1] for _,x in pairs],dtype=float)
        latest=dates[-1].isoformat()
        def apply(idx, yes, detail):
            result[idx].update(상태="충족" if yes else "미충족",획득=RULES[idx][1] if yes else 0,근거=detail)
        if len(closes)>=21:
            avg=closes.rolling(20).mean()
            yes=bool(closes.iloc[-2]<=avg.iloc[-2] and closes.iloc[-1]>avg.iloc[-1])
            apply(0,yes,f"종가 {closes.iloc[-1]:,.0f} / 20일선 {avg.iloc[-1]:,.0f}원")
        if len(closes)>=60:
            avg=closes.rolling(60).mean()
            apply(1,bool(closes.iloc[-1]>avg.iloc[-1]),f"종가 {closes.iloc[-1]:,.0f} / 60일선 {avg.iloc[-1]:,.0f}원")
        if len(volumes)>=21:
            baseline=volumes.iloc[-21:-1].mean()
            if baseline>0:
                multiple=volumes.iloc[-1]/baseline
                apply(2,bool(closes.iloc[-1]>closes.iloc[-2] and multiple>=1.5),f"전일 대비 상승 여부 포함 · 거래량 {multiple:.2f}배")
        if len(closes)>=16:
            diff=closes.diff()
            ups=diff.clip(lower=0).ewm(alpha=1/14,adjust=False).mean()
            downs=(-diff.clip(upper=0)).ewm(alpha=1/14,adjust=False).mean()
            def rsi(up,down):
                if down==0:return 100.0 if up>0 else 50.0
                return 100-100/(1+up/down)
            r1,r0=rsi(ups.iloc[-1],downs.iloc[-1]),rsi(ups.iloc[-2],downs.iloc[-2])
            apply(4,bool(40<=r1<=65 and r1>r0),f"RSI(14) {r1:.1f} / 전일 {r0:.1f}")
        if len(closes)>=35:
            macd=closes.ewm(span=12,adjust=False).mean()-closes.ewm(span=26,adjust=False).mean()
            signal=macd.ewm(span=9,adjust=False).mean()
            apply(5,bool(macd.iloc[-2]<=signal.iloc[-2] and macd.iloc[-1]>signal.iloc[-1]),"MACD(12,26,9) 일봉 골든크로스 확인")
    else:
        latest=None
    flow=item.get("flow") or {}
    # Use daily investor quantities only when source day equals latest stock close day.
    flow_date=flow.get("date")
    flow_daily=flow.get("daily") or {}
    if latest and flow_date==latest and all(isinstance(flow_daily.get(k),(int,float)) for k in ("foreign","institution")):
        f,i=flow_daily["foreign"],flow_daily["institution"]
        yes=f>0 and i>0
        result[3].update(상태="충족" if yes else "미충족",획득=15 if yes else 0,근거=f"외국인 {f:+,.0f}주 / 기관 {i:+,.0f}주 · {flow_date}")
    metrics=item.get("metrics") or {}
    growth=metrics.get("growth_pct")
    if isinstance(growth,(int,float)) and isfinite(growth):
        yes=growth>0
        result[6].update(상태="충족" if yes else "미충족",획득=10 if yes else 0,근거=f"동기 영업이익 증가율 {growth:+.1f}% · {metrics.get('year','연도 미확인')}년 {metrics.get('quarter','?')}분기 누적")
    # Risk/reward and stop loss are personal inputs; never infer automatically.
    result[7]["근거"]="진입가·손절가·지지선은 사용자가 별도로 검증"
    score=sum(x["획득"] for x in result)
    verified=sum(x["배점"] for x in result if x["상태"]!="미확인")
    return result,score,verified,latest

def render(fetcher=None):
    st.title("매수 신호 점수표 · 자동 조회")
    st.caption("국내 주식 6자리 종목코드 · 공식 일별 종가/거래량, KIS 일별 수급, DART 실적 자료 기준")
    codes=st.session_state.get("watch_codes",[])
    names=st.session_state.get("watch_names",{})
    choices={c:f"{names.get(c,c)} · {c}" for c in codes}
    selected=st.selectbox("관심종목 선택",["직접 입력"]+list(choices),format_func=lambda x:choices.get(x,x))
    if selected=="직접 입력":
        code=st.text_input("6자리 종목코드",key="auto_signal_code",placeholder="005930").strip()
    else:
        code=selected
    if not re.fullmatch(r"\d{6}",code):
        st.info("국내 주식의 숫자 6자리 종목코드를 입력하세요.")
        return
    key="auto_buy_result_"+code
    if st.button("공식 데이터 조회 및 점수 계산",type="primary"):
        try:
            from predash.official import Official
            now=datetime.now(ZoneInfo("Asia/Seoul")).date()
            if fetcher is not None:
                item=fetcher(code,Official(),now)
            else:
                item=dict(st.session_state.get("watch_results",{}).get(code,{}) or {})
                item["price_rows"]=Official().price_history(code,now,lookback_days=400)
            st.session_state[key]=item
            st.session_state["auto_signal_time_"+code]=datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M")
        except Exception as exc:
            st.error(f"가격 조회 실패: {exc}")
    item=st.session_state.get(key) or st.session_state.get("watch_results",{}).get(code)
    if not item:
        st.info("조회 버튼을 눌러 자료를 가져오세요. 관심종목 화면의 '목록 전체 새로고침'을 먼저 실행하면 실적·KIS 수급도 활용할 수 있습니다.")
        return
    rows,score,verified,day=evaluate(code,item)
    if not day:
        st.warning("최근 유효한 일별 종가가 없습니다. 가격 신호는 미확인으로 처리합니다.")
    st.metric("확인된 조건 획득 점수",f"{score} / 100점")
    st.progress(score/100)
    st.caption(f"검증 가능한 배점: {verified}/100점 · 시세 기준일: {day or '미확인'} · 체크되지 않은 항목과 미확인 항목은 다릅니다.")
    if verified<80:
        st.warning("데이터가 충분하지 않아 종합 매수 신호 판정을 보류합니다. 특히 수급·실적과 손절 기준을 확인하세요.")
    else:
        label="매수 후보" if score>=80 else "추가 확인" if score>=60 else "관망·검토"
        st.info(f"규칙 기반 분류: {label} (매수 추천 또는 상승 확률이 아닙니다)")
    st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True)
    st.caption("공식 시세·실적과 연결된 KIS 일별 수급을 조회합니다. 실적 기간, 각 자료 기준일, API 오류를 반드시 확인하세요. 개인 손절·지지선 항목 5점은 자동 점수에 포함하지 않습니다.")
    errors=item.get("errors") or {}
    if errors:
        with st.expander("데이터 조회 오류·미확인 사유"):
            for source, reason in errors.items():
                st.write(f"{source}: {reason}")
