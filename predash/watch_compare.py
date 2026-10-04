"""Comparison of already fetched public watchlist data; no extra API calls."""
import csv
import io
from math import isfinite


def numeric(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value if isfinite(value) else None


def comparison_rows(codes, results, names=None):
    names = names or {}
    rows = []
    for code in codes:
        item = results.get(code) or {}
        lamp = item.get('lamp') or {}
        metrics = item.get('metrics') or {}
        krx = item.get('krx') or {}
        period = f"{metrics['year']}년 {metrics['quarter']}분기 누적" if metrics else '미확인'
        basis = {'CFS': '연결', 'OFS': '별도'}.get(metrics.get('basis'), '미확인')
        name = item.get('name')
        if not name or name == code:
            name = names.get(code, code)
        rows.append({
            '종목명': name, '종목코드': code,
            '시장': krx.get('market') or item.get('benchmark') or '미확인',
            '종가 (원)': numeric(lamp.get('close')),
            '종가 기준일': lamp.get('date') or '미확인',
            '추세': lamp.get('state') or '판정 보류',
            '매출 (억원)': numeric(metrics.get('revenue')),
            '매출 증가율 (%)': numeric(metrics.get('revenue_growth_pct')),
            '영업이익 (억원)': numeric(metrics.get('profit')),
            '영업이익 증가율 (%)': numeric(metrics.get('growth_pct')),
            '영업이익률 (%)': numeric(metrics.get('margin_pct')),
            '실적 기간': period, '회계 기준': basis,
            '시가총액 (억원)': numeric(krx.get('market_cap')) / 1e8 if numeric(krx.get('market_cap')) is not None else None,
            'KRX 기준일': krx.get('date') or '미확인',
            '실적 조회일': metrics.get('fetched') or '미확인',
            '자료 조회': item.get('fetched') or '조회 전',
            '실적 공시': ('https://dart.fss.or.kr/dsaf001/main.do?rcpNo=' + metrics['receipt']) if metrics.get('receipt') else None,
        })
    return rows


def comparison_warnings(rows):
    messages = []
    periods = {row['실적 기간'] for row in rows if row['실적 기간'] != '미확인'}
    bases = {row['회계 기준'] for row in rows if row['회계 기준'] != '미확인'}
    dates = {row['종가 기준일'] for row in rows if row['종가 기준일'] != '미확인'}
    if len(periods) > 1:
        messages.append('실적 기간이 서로 다릅니다. 같은 기간의 기업끼리 비교하세요.')
    if len(bases) > 1:
        messages.append('연결·별도 재무제표가 섞여 있습니다. 회계 기준을 확인하세요.')
    if len(dates) > 1:
        messages.append('종가 기준일이 서로 다릅니다. 날짜를 확인하세요.')
    if any(row['실적 기간'] == '미확인' for row in rows):
        messages.append('실적 미확인 종목이 있습니다. DART 키·조회 결과를 확인하세요.')
    return messages


def comparison_csv(rows):
    output = io.StringIO(newline='')
    if rows:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        for row in rows:
            # Keep public names from becoming spreadsheet formulas.
            safe = {key: ("'" + value if isinstance(value, str) and value.startswith(('=', '+', '-', '@', '\t', '\r', '\n')) else value)
                    for key, value in row.items()}
            safe['종목코드'] = "'" + row['종목코드']
            writer.writerow(safe)
    return output.getvalue().encode('utf-8-sig')
