# 매일 정리 절차 (예약 작업이 이 문서대로 실행)

평일 저녁 7시(KST) 무렵 실행. 오늘(KST) 날짜 = `D`.

## 0. 준비
- 이 저장소(`luckyhan-bot/luckyhan-report`)와 `luckyhan-bot/luckyhan-app`을 클론해 둔다.
- 출처: 네이버 증권 종목분석 + 한경 컨센서스 기업 리포트(네이버에 없는 증권사 보충, 종목코드+증권사로 중복 제거). 한경 리포트 id는 900000000+report_idx.
- 출처: 네이버 증권 리서치(종목분석) + 한경 컨센서스(기업). 같은 종목·같은 증권사 리포트는 하나로 합친다(fetch.js가 처리).
- 네이버 접속에는 Playwright(크롬)와 `pdftotext`를 쓴다. `npm ls playwright` 가 안 되면 전역 `require('playwright')`를 쓰면 된다.

## 1. 수집
```
node scripts/fetch.js D          # work/D/reports.json + work/D/pdf/*.txt
python3 scripts/portfolio.py <luckyhan-app 경로>   # work/portfolio.json
```
- 리포트가 0건이면(주말·휴장일) **아무것도 커밋하지 않고 끝낸다.**
- 이미 `data/D.json`이 있으면 다시 만들어 덮어써도 된다.

## 2. 판단 → `work/D/judge.json`
reports.json의 **모든 리포트**에 대해, PDF 첫 장(`textFile`)과 끝부분 '투자의견·목표주가 변동 내역' 표를 읽고 작성:
```json
{"<리포트 id>": {"sector": "반도체", "sub": "전공정 장비(고압 열처리)", "ai": true, "robot": false,
                 "target_prev": 71000, "target_dir": "keep", "opinion_changed": false}}
```
- `target_dir`: `up`/`down`/`keep`(같은 증권사 직전 목표가 대비), `new`(신규 커버리지), `none`(목표가 없음).
  reports.json의 `prev`(같은 증권사 직전 리포트)와 PDF 표기('상향/하향/유지', 변동 내역 표)를 함께 확인.
- `ai`: 반도체(메모리·HBM·파운드리·장비·소재·부품), AI 서버용 기판·전자부품, 전력기기·전선(데이터센터 전력),
  데이터센터·클라우드, AI 소프트웨어·플랫폼. `robot`: 휴머노이드·산업용·협동로봇, 감속기·액추에이터 등 로봇 부품.
- 업종(`sector`)은 큰 분류로 통일(반도체, 전자부품, 전력기기, IT서비스, 로봇, 자동차, 조선, 방산, 운송, 화학, 소재,
  2차전지, 헬스케어, 금융, 핀테크, 유통, 음식료, 미디어, 게임, 건설, 기계, 장비, 디스플레이, 에너지 등).
  `sub`는 처음 보는 사람도 알 수 있게 구체적으로.

## 3. 선정
```
python3 scripts/pick.py D        # work/D/picks.json
```
규칙은 pick.py 머리말 참고(관심 종목 → AI 최대 6·로봇 최소 1 → 목표가 변경 > 의견 변경 > 업종 다양성).

## 4. 요약 → `work/D/content.json`
picks.json의 10개 리포트 PDF를 **앞부분과 실적·밸류에이션 표까지** 읽고 build.py 머리말 형식대로 작성.
- **리포트 문장을 베끼지 말고 직접 다시 쓴 문장**으로. 숫자 위주, 처음 보는 사람도 이해되게 상세하게.
- `headline`: ["첫 줄", "둘째 줄(빨강)"] — 오늘 리포트 전체를 꿰는 대비/반전형 제목. `dek`: 표지 소개 1~2문장.
- `line`: 업종 지도용 한 줄(무엇을 만드는/하는 회사인지).
- `about`: "어떤 회사?" 2~3문장. 제품·고객·매출 구조, 핵심어는 `**굵게**`.
- `thesis`: 증권사 결론 한 줄(의견·목표가를 왜 그렇게 했는지). 의견 없는 리포트는 "(○○, 투자의견 없음)"으로 시작.
- `points` 4개: `{"h": 굵은 소제목(숫자 포함, 15자 안팎), "d": 1~2문장 설명}`. 전문 용어(LTA, SOTP, HKMG, GPUaaS 등)는 괄호로 풀어 쓰기.
  목표가 변경이 있으면 첫 포인트에서 "왜 바꿨는지(이익 변화 vs 멀티플 변화)"를 설명.
- `metrics` 3칸: 연도 표기(27E 등) + 값. P/E, 영업이익, 이익률, 배당수익률, 최근 주가 수익률 중 그 종목에 의미 있는 것.
- `risk`: 체크할 리스크 1~2문장, 핵심은 `**굵게**`.
- `signals` 3개: 10개 리포트를 **가로질러** 보이는 공통 흐름. "N개 중 M개", 종목명·숫자를 `**굵게**` 넣어 근거를 댄다.
  예) 목표가 하향인데 이익 추정은 상향 → 멀티플 수축 / 신규 팹 → 장비·소재·부품 수혜 체인 / 판가 인상 국면.
- `standouts` 2~4개: 유일한 상향·하향, 유일한 HOLD, 최대 하향폭, 상승여력 1위, 신규 커버리지 등. `dir`는 up/down/none.

## 5. 저장·배포
```
python3 scripts/build.py D       # data/D.json, data/index.json
git add data && git commit -m "report D" && git pull --rebase && git push origin main
```
GitHub Pages(main 브랜치 루트)로 바로 반영된다.
