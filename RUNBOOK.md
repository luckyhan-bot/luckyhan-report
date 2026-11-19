# 매일 정리 절차 (예약 작업이 이 문서대로 실행)

평일 저녁 7시(KST) 무렵 실행. 오늘(KST) 날짜 = `D`.

## 0. 준비
- 이 저장소(`luckyhan-bot/luckyhan-report`)와 `luckyhan-bot/luckyhan-app`을 클론해 둔다.
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
picks.json의 10개 리포트 PDF를 읽고 build.py 머리말 형식대로 작성.
- **리포트 문장을 베끼지 말고 직접 다시 쓴 문장**으로. 숫자 위주.
- `line`: 업종 지도용 한 줄 설명(처음 보는 기업도 이해되게). `about`: "어떤 회사?" 두 줄.
- `points` 4개(숫자 위주), `metrics` 3칸(PER·영업이익 등, 연도 표기), `risk` 한 줄.
- `signals` 3개: 오늘 리포트들의 공통 흐름. `standouts`: 유일한 상향/하향, 최대 상승여력, 신규 커버리지 등.
- `headline`: 오늘의 한 줄 제목.

## 5. 저장·배포
```
python3 scripts/build.py D       # data/D.json, data/index.json
git add data && git commit -m "report D" && git pull --rebase && git push origin main
```
GitHub Pages(main 브랜치 루트)로 바로 반영된다.
