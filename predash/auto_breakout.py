"""KOSPI breakout discovery using approved KRX EOD data and KIS investor flow."""
from datetime import date, timedelta
import requests
import re
import time
import pandas as pd

class ScanError(RuntimeError):
    pass

def load_krx_history(key, asof=None, calendar_days=210):
    if not key:
        raise ScanError("KRX_AUTH_KEY가 설정되지 않았습니다.")
    end = asof or date.today()
    session = requests.Session()
    records = []
    successful_days = 0
    for offset in range(calendar_days, -1, -1):
        day = end - timedelta(days=offset)
        if day.weekday() >= 5:
            continue
        try:
            response = session.get("https://data-dbg.krx.co.kr/svc/apis/sto/stk_bydd_trd",
                headers={"AUTH_KEY": key}, params={"basDd": day.strftime("%Y%m%d")}, timeout=(5, 15))
            if response.status_code != 200:
                raise ScanError(f'KRX HTTP {response.status_code} · 요청일 {day:%Y-%m-%d} · 401/403 인증·승인, 429 호출 한도 확인')
            payload = response.json()
            rows = payload.get("OutBlock_1")
            if not isinstance(rows, list):
                raise ScanError("KRX 응답 형식 또는 서비스 이용 승인을 확인하세요.")
        except (requests.RequestException, ValueError) as exc:
            raise ScanError(f"KRX 통신/응답 실패 · 요청일 {day:%Y-%m-%d} · {type(exc).__name__}") from exc
        if not rows:
            continue
        successful_days += 1
        time.sleep(0.12)
        for item in rows:
            raw_code = str(item.get("ISU_SRT_CD") or item.get("ISU_CD") or "").strip()
            code = raw_code.zfill(6) if re.fullmatch(r"\d{1,6}", raw_code) else ""
            if not (len(code) == 6 and code.isdigit()):
                continue
            try:
                close = float(str(item["TDD_CLSPRC"]).replace(",", ""))
                volume = float(str(item["ACC_TRDVOL"]).replace(",", ""))
            except (ValueError, TypeError, KeyError):
                continue
            if close <= 0 or volume < 0:
                continue
            records.append({"date":day, "code":code, "name":item.get("ISU_ABBRV") or item.get("ISU_NM") or code,
                            "close":close, "volume":volume})
    if successful_days < 121:
        raise ScanError(f"KRX 유효 거래일 {successful_days}일: 120일선 신규 돌파 판정에 최소 121거래일이 필요합니다.")
    return pd.DataFrame(records)

def breakout_candidates(history, volume_multiple=1.5):
    df = history.sort_values(["code", "date"]).copy()
    g = df.groupby("code", sort=False)
    df["ma120"] = g["close"].transform(lambda x: x.rolling(120, min_periods=120).mean())
    df["prev_close"] = g["close"].shift(1)
    df["prev_ma120"] = g["ma120"].shift(1)
    df["volume20"] = g["volume"].transform(lambda x: x.shift(1).rolling(20, min_periods=20).mean())
    day = df["date"].max()
    today = df[df["date"].eq(day)].copy()
    mask = ((today["prev_close"] <= today["prev_ma120"]) &
            (today["close"] > today["ma120"]) &
            (today["volume20"] > 0) &
            (today["volume"] >= today["volume20"] * volume_multiple))
    found = today.loc[mask].copy()
    found["괴리율(%)"] = (100 * (found["close"] / found["ma120"] - 1)).round(2)
    found["거래량배율"] = (found["volume"] / found["volume20"]).round(2)
    return day, found.sort_values("거래량배율", ascending=False)

def confirmed_joint_buy(candidates, day, investor_lookup):
    found = []
    errors = []
    for row in candidates.itertuples(index=False):
        code = row.code
        try:
            flow = investor_lookup(code)
            if not flow or flow.get("date") != day.isoformat():
                errors.append(f"{code}: 기준일 수급 미확인")
                continue
            daily = flow.get("daily", {})
            foreign, institution = daily.get("foreign"), daily.get("institution")
            if foreign is None or institution is None:
                errors.append(f"{code}: 투자자별 순매수 미확인")
                continue
            if foreign > 0 and institution > 0:
                found.append({"기준일":day.isoformat(), "종목코드":code, "종목명":row.name,
                    "종가":row.close, "괴리율(%)":round(100 * (row.close / row.ma120 - 1), 2),
                    "외국인 순매수(주)":foreign, "기관 순매수(주)":institution,
                    "거래량배율":round(row.volume / row.volume20, 2)})
        except Exception:
            errors.append(f"{code}: KIS 수급 조회 실패")
    return found, errors
