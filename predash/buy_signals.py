"""Manual buy-signal checklist for educational use; never implies live API verification."""
import streamlit as st

CRITERIA = (
    ("20일 이동평균선 상향 돌파", 15),
    ("60일 이동평균선 위에서 안착", 15),
    ("거래량이 20일 평균의 1.5배 이상", 20),
    ("외국인·기관 동반 순매수", 15),
    ("RSI 40~65이며 상승 중", 10),
    ("MACD 골든크로스", 10),
    ("영업이익 성장 또는 전망 상향", 10),
    ("지지선·손절 기준이 명확함", 5),
)

def render():
    st.title("매수 신호 점수표")
    st.caption("기술적·수급·실적 신호를 직접 체크하는 100점 평가표 · 실시간 자동 분석이 아닙니다.")
    st.info("각 항목은 실제 자료를 확인한 뒤에만 선택하세요. 체크하지 않은 항목은 0점 처리되며, 데이터가 없다고 부정적인 신호가 확인된 것은 아닙니다.")
    name = st.text_input("분석 대상 종목 (선택)", placeholder="예: 삼성전자 005930", key="buy_signal_name")
    checks = []
    for idx, (label, weight) in enumerate(CRITERIA):
        a, b = st.columns([6, 1], vertical_alignment="center")
        selected = a.checkbox(label, key=f"buy_signal_check_{idx}")
        b.write(f"+{weight}점")
        checks.append(selected)
    score = sum(weight for checked, (_, weight) in zip(checks, CRITERIA) if checked)
    if score >= 80:
        status, note = "매수 후보", "긍정 신호가 다수 충족되었습니다. 진입가와 손절가를 별도로 확인하세요."
    elif score >= 60:
        status, note = "추가 확인", "추세와 거래량, 위험 대비 기대수익을 더 검토하세요."
    else:
        status, note = "관망·검토", "선택된 긍정 신호가 적습니다. 미확인 항목은 자료를 먼저 확인하세요."
    st.metric("매수 신호 점수", f"{score} / 100점", status, delta_color="off")
    st.progress(score / 100)
    st.write(f"**분석 종목:** {name.strip() or '미입력'}")
    st.write(note)
    st.caption("점수와 분류는 자체 교육용 규칙입니다. 수익률·매수 성공 확률이 검증된 모델이 아니며 매수 추천 또는 자동 주문 신호가 아닙니다.")
    if st.button("체크 초기화", key="buy_signal_reset"):
        for idx in range(len(CRITERIA)):
            st.session_state[f"buy_signal_check_{idx}"] = False
        st.rerun()
