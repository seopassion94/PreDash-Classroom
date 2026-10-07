"""KOSDAQ 120-session breakout and investor net-buy scanner (CSV input)."""
import pandas as pd

REQUIRED = {"date", "code", "name", "close", "volume", "foreign_net", "institution_net"}

def scan(prices, volume_multiple=1.5):
    missing = REQUIRED - set(prices.columns)
    if missing:
        raise ValueError("필수 열 누락: " + ", ".join(sorted(missing)))
    df = prices.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["code"] = df["code"].astype(str).str.strip().str.zfill(6)
    for col in ("close", "volume", "foreign_net", "institution_net"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    if "market" in df.columns:
        df = df[df["market"].astype(str).str.upper().isin(["KOSDAQ", "코스닥"])]
    df = df.dropna(subset=["date", "close", "volume", "foreign_net", "institution_net"])
    df = df.sort_values(["code", "date"]).drop_duplicates(["code", "date"], keep="last")
    group = df.groupby("code", sort=False)
    df["ma120"] = group["close"].transform(lambda x: x.rolling(120, min_periods=120).mean())
    df["prev_close"] = group["close"].shift(1)
    df["prev_ma120"] = group["ma120"].shift(1)
    df["volume20"] = group["volume"].transform(lambda x: x.shift(1).rolling(20, min_periods=20).mean())
    latest = df["date"].max()
    rows = df[df["date"].eq(latest)].copy()
    rows = rows[(rows["prev_close"] <= rows["prev_ma120"]) &
                (rows["close"] > rows["ma120"]) &
                (rows["foreign_net"] > 0) & (rows["institution_net"] > 0) &
                (rows["volume"] >= rows["volume20"] * volume_multiple)]
    rows["괴리율(%)"] = ((rows["close"] / rows["ma120"] - 1) * 100).round(2)
    rows["거래량배율"] = (rows["volume"] / rows["volume20"]).round(2)
    rows = rows.rename(columns={"date":"기준일","code":"종목코드","name":"종목명","close":"종가",
        "foreign_net":"외국인 순매수","institution_net":"기관 순매수"})
    return latest, rows[["기준일","종목코드","종목명","종가","괴리율(%)",
                         "외국인 순매수","기관 순매수","거래량배율"]].sort_values("거래량배율",ascending=False)
