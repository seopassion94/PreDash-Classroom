# PreDash Classroom · 매수 신호 점수표

개인 전용 Sites 앱의 공개 소스 보관본입니다. 원본 Streamlit 앱과 독립된 웹 앱이며, 이 폴더를 추가해도 기존 `app.py`의 동작과 배포 설정은 바뀌지 않습니다. `seopassion94/PreDash-Classroom`의 커밋 `9cff678d87eb282600d20b74b02ac9cec1d006b5`를 참고했고, Sites 배포 소스 커밋 `bbbe71c895f5e4815619adf5e523c71f0c6afefc`를 보관했습니다. 공개 소스 저장과 운영 사이트의 비공개 접근 정책은 별개입니다.

## 로컬 실행 및 테스트

Node.js 22.13 이상이 필요합니다. 저장소 루트에서 실행합니다.

```bash
cd sites/buy-signals
npm run install:ci
npm run dev
```

```bash
node --test tests/*.test.mjs
node node_modules/typescript/bin/tsc --noEmit
npm run build
```

개발 서버 주소는 실행 결과를 확인하세요. 로컬에서는 인증키를 데이터 연결 화면에 입력합니다. 배포된 사이트의 비공개 인증은 Sites가 담당하므로, 별도의 호스팅으로 옮길 때는 서버 인증을 준비해야 합니다. `.openai/hosting.json`은 현재 Sites 프로젝트 연결 정보이며 인증키가 아닙니다. 다른 Site로 배포하려면 새 프로젝트의 정확한 ID를 사용해야 합니다.

## 사용

1. 본인 ChatGPT 계정으로 비공개 사이트를 엽니다.
2. 데이터 연결에서 금융위원회_주식시세정보 활용승인이 완료된 공공데이터포털 인증키를 입력합니다. 현재 공식 V2와 기존 PreDash API 주소를 구분해 선택합니다.
3. 종목 선택 시 최근 400일 공식 종가·거래량을 조회하고 점수를 계산합니다. 열린 페이지는 15분마다 다시 조회합니다. 백그라운드 예약 작업은 아닙니다.
4. 최대 8개 관심종목을 브라우저에 보관하며, 기존 PreDash `version:1` JSON 백업을 불러오고 내보낼 수 있습니다. 종목코드의 앞자리 0을 유지합니다.

입력한 인증키는 페이지 메모리에서만 유지되고, 주소·브라우저 저장소·백업·소스에 저장하지 않습니다. 새로고침 후에는 다시 입력해야 합니다. 선택적으로 Sites 서버 환경 변수 `DATA_GO_KR_SERVICE_KEY`를 설정하면 페이지를 열 때 자동 연결할 수 있습니다. 환경 변수는 Sites 네이티브 설정에서 관리합니다.

## 구현 범위

원본의 8개 조건과 배점을 유지합니다. 공식 시세 기반 5개 조건(최대 70점)을 자동 계산합니다. 이번 최소 버전은 KIS 수급(15점), DART 실적(10점), 개인 지지선·손절 기준(5점)을 조회하거나 자동 가점하지 않습니다. 따라서 검증 가능한 배점 80점에 미달하여 종합 신호는 판정 보류입니다. 미확인과 미충족을 구분합니다.

공식 API의 종가·거래량만 사용합니다. 미래 날짜·잘못된 날짜·비정상 수치·다른 종목을 제외하고 동일 날짜 값의 충돌이나 불완전한 페이지 수신 시 계산을 중단합니다. 최근 시세가 5일 초과 경과하면 가격 신호를 보류합니다. 원시 종가 기준이므로 기업행사에 따른 가격 불연속은 별도 확인이 필요합니다. 공식 시세는 다음 영업일 13시 이후 갱신되는 일별 자료이며 장중 데이터가 아닙니다.

## 검증

- `node --test tests/*.test.mjs`: 12개 점수·데이터 처리·백업 계약 테스트.
- `node node_modules/typescript/bin/tsc --noEmit`: 타입 검사.
- `node <sites-plugin>/scripts/build-site.mjs`: Sites 프로덕션 빌드.
- 원본 Python `evaluate`와 JavaScript 계산식을 168개 재현 가능한 가상 입력에서 비교해 조건 상태·점수·검증 배점·시세 기준일 일치 확인.
- 브라우저: 종목 전환, 잘못된 티커 차단, 관심종목 추가·저장, 조건 필터·계산 근거 펼침, 검증용 응답을 이용한 점수·가격 차트·거래량 렌더링 확인. 검증용 API는 최종 소스와 배포에 포함하지 않습니다.
- 실제 공식 API의 정상 수신 검증은 활용승인된 인증키 연결 후 가능합니다. 초기 제작 시 인증키가 제공되지 않아 수행하지 못했습니다.

호스팅의 비공개 접근 제어는 Sites가 담당합니다. API는 프로덕션에서 ChatGPT 사용자 헤더를 확인하고, 동일 출처 요청만 허용하며 응답과 요청 데이터를 캐시하지 않습니다.

## 출처

- https://github.com/seopassion94/PreDash-Classroom/blob/9cff678d87eb282600d20b74b02ac9cec1d006b5/predash/buy_signals.py
- https://github.com/seopassion94/PreDash-Classroom/blob/9cff678d87eb282600d20b74b02ac9cec1d006b5/predash/watchlist.py
- https://www.data.go.kr/data/15094808/openapi.do
- https://www.fsc.go.kr/in060501
