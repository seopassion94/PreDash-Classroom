"""Classroom credentials are held only in the current Streamlit session."""
import streamlit as st
from predash.kis import KIS, BrokerError


def account_settings(mode=None):
    settings = st.session_state.get('classroom_credentials', {})
    if not settings and not st.session_state.get('kis_secrets_disconnected'):
        try:
            selected = str(st.secrets.get('KIS_ENV', 'demo')).strip()
            requested = mode or selected
            prefix = 'KIS_DEMO_' if requested == 'demo' and (
                selected != 'demo' or any(st.secrets.get('KIS_DEMO_' + key)
                    for key in ('APP_KEY','APP_SECRET','CANO','ACNT_PRDT_CD'))
            ) else 'KIS_'
            if requested != selected and prefix == 'KIS_':
                return dict(mode=requested, key='', secret='', cano='', product='')
            names = dict(key='APP_KEY', secret='APP_SECRET', cano='CANO', product='ACNT_PRDT_CD')
            return dict(mode=requested, **{
                key: str(st.secrets.get(prefix + name, '')).strip()
                for key, name in names.items()
            })
        except FileNotFoundError:
            pass
    selected = mode or settings.get('mode', 'demo')
    if selected != settings.get('mode'):
        return dict(mode=selected, key='', secret='', cano='', product='')
    return dict(mode=selected, **{k: settings.get(k, '') for k in ('key','secret','cano','product')})


def connection_form():
    if st.session_state.pop('classroom_clear_inputs', False):
        for key in ('class_key','class_secret','class_cano','class_product'):
            st.session_state.pop(key, None)
    st.subheader('내 증권사 계좌 연결')
    st.caption('각자 Fork한 앱에서 본인 키를 입력하세요. 현재 접속 세션에서만 사용합니다.')
    settings = account_settings()
    if all(settings[k] for k in ('key','secret','cano','product')):
        if not st.session_state.get('classroom_credentials'):
            try:
                KIS(settings=settings)
            except BrokerError as error:
                st.error(str(error))
                return
            st.caption('Streamlit Secrets 사용 · 내 계좌에서 새로고침하면 인증 후 잔고를 조회합니다.')
        st.success('계좌 설정 준비됨 · ' + ('모의투자' if account_settings()['mode']=='demo' else '실전 조회'))
        if st.button('계좌 연결 해제'):
            authorized = st.session_state.get('authorized')
            st.session_state.clear()
            st.session_state.kis_secrets_disconnected = True
            if authorized: st.session_state.authorized = True
            st.rerun()
        return
    if st.session_state.get('kis_secrets_disconnected'):
        if st.button('Secrets 계좌 다시 사용'):
            st.session_state.pop('kis_secrets_disconnected', None)
            st.rerun()
    with st.form('classroom_connection'):
        mode = st.radio('투자 환경', ['모의투자','실전 조회'], horizontal=True)
        key = st.text_input('App Key', type='password', key='class_key')
        secret = st.text_input('App Secret', type='password', key='class_secret')
        cano = st.text_input('계좌번호 앞 8자리', type='password', max_chars=8, key='class_cano')
        product = st.text_input('계좌번호 뒤 2자리', max_chars=2, key='class_product')
        submitted = st.form_submit_button('연결 확인', type='primary', use_container_width=True)
    if submitted:
        settings = dict(mode='demo' if mode=='모의투자' else 'real',key=key.strip(),secret=secret.strip(),cano=cano.strip(),product=product.strip())
        try:
            client = KIS(settings=settings)
            with st.spinner('잔고 조회 권한을 확인합니다…'):
                client.balance()
            st.session_state.classroom_credentials = settings
            st.session_state['_kis_client_demo' if settings['mode']=='demo' else '_kis_client'] = client
            st.session_state.classroom_clear_inputs = True
            st.rerun()
        except BrokerError as error:
            st.error(str(error))
    st.info('연결 해제와 로그아웃은 키·잔고·접속 중 실습 기록을 지웁니다. 필요한 기록은 먼저 백업하세요.')
