# PLAY27_edgar_fetch

## 목적
SEC EDGAR 필링을 fetch 해 한국 `module_disclosure` 와 동등한 카테고리별 markdown 리포트를 만드는 PoC. (KR DART → US EDGAR 1:1 대응)

## 실행법
```powershell
# 의존성 (대부분 이미 깔려있을 것)
pip install requests beautifulsoup4 lxml

cd C:\Users\fivep\OneDrive\Desktop\PLAYGROUND\PLAY27_edgar_fetch

# 단일 종목
python edgar_fetch.py AAPL --days 90 --out report_AAPL.md

# 5종목 일괄 (AAPL/NVDA/MSFT/TSLA/META)
python run_all.py
```

## 입력 / 출력
- **입력:** 티커 심볼 (`AAPL` 등). API 키 불필요 (EDGAR 무인증).
- **출력:**
  - `report_{TICKER}.md` — 카테고리별 markdown 표 (KR module_disclosure 출력과 형식 호환).
  - `ticker_cik_map.json` — 첫 실행 시 자동 생성되는 ticker→CIK 매핑 캐시 (~360KB).
  - stdout: `DONE: N filings` (단일) / `DONE: 5/5` (일괄).

## 카테고리 매핑
8-K Item 코드 → 카테고리 (KR DART 카테고리와 의미 매칭):

| Item | 카테고리 | KR 대응 |
|---|---|---|
| 1.01, 2.01 | contract | 단일판매·공급계약 |
| 2.02 | earnings | 잠정실적 |
| 7.01 | guidance | 영업/투자 가이던스 |
| 3.02, 2.03 | equity | 증자, 채무발생 |
| 5.02 | exec | 임원/이사 변경 |
| 10-K | annual_report | 사업보고서 |
| 10-Q | quarterly_report | 분기보고서 |
| 4, 13G/D | insider | 주식등의대량보유 |

전체 매핑은 `_categorizer.py` 의 `ITEM_MAP`/`FORM_MAP` 참고.

## 가정 & 제약
- **User-Agent 의무**: SEC 정책상 `"PLAY27 Researcher fivepeople201@gmail.com"` 식별자 헤더 박아둠. 다른 사용자가 쓸 거면 본인 이메일로 바꿔야 SEC 차단(403) 회피.
- **Rate limit**: 호출 간 0.2~0.3초 sleep. 5종목 일괄에 약 30~50초 소요.
- **8-K 본문 fetch only**: 10-K/10-Q는 파일이 MB 단위로 거대해서 본문은 안 받고 *링크와 메타데이터*만 표시. 이건 미션에서도 명시된 사항.
- **Item 추출 규약**: 정규식 `Item\s+\d+\.\d+` 으로 본문 첫 등장 순서대로 최대 8개 추출. 8-K 한 건에 Item 여러 개면 *우선순위 가장 높은* 카테고리로 분류하고 나머지는 라벨에 `[+...]`로 병기. 우선순위: contract > earnings > guidance > equity > exec > insider > other.
- **요약(summary)**: 8-K HTML 본문에서 첫 Item 헤더 뒤 240자 추출 → 200자 컷. 형식적 한 줄 보강이고, 깊이 있는 NLP 분석은 안 함.
- **submissions API 한계**: `recent.filings` 만 본다 (최근 ~1000건). 90일 범위라면 충분히 커버. 1년+ 조회면 `files` 배열의 추가 페이지를 별도 fetch 해야 함 — 이건 현재 구현 안 됨.
- **ticker_cik_map.json 캐싱**: 첫 실행 시 SEC 에서 ~10MB JSON 받아 압축본(~360KB) 저장. `--force-refresh` 옵션은 안 만들었음. 캐시 다시 받고 싶으면 파일 삭제.
- **stdin 인코딩**: Windows PowerShell 대상 — `sys.stdout.reconfigure(encoding='utf-8')` 명시. 출력 .md 도 utf-8 강제.
- **XMLParsedAsHTMLWarning**: 일부 .htm 이 실은 XBRL XML 인 경우가 있어서 경고가 떴음. 무해해서 suppress.

## 검증 결과 (2026-05-26 기준)
| Ticker | 총 필링 (90d) | 8-K |
|---|---|---|
| AAPL | 27 | 2 |
| NVDA | 43 | 5 |
| MSFT | 28 | 2 |
| TSLA | 20 | 2 |
| META | 81 | 3 |
| **합계** | **199** | **14 (7.0%)** |

카테고리 분포: insider 105, other 73, earnings 7, exec 7, quarterly_report 5, annual_report 2. 인사이더 거래(Form 4)가 압도적 — 미국 시장 특성. 실적 발표(Item 2.02)와 경영진 변경(Item 5.02)이 그 다음.

## mvp 통합 권장 경로
별도 모듈로 분리 권장:
```
mvp/research_Mvp/
├── module_disclosure/          # 기존 KR (그대로)
└── module_disclosure_us/       # 신규 — 이 PLAY 의 코드를 이식
    ├── __main__.py
    ├── _edgar_api.py           # edgar_fetch.py 의 fetch 부분
    ├── _categorizer.py         # 그대로
    └── _renderer.py            # KR `_renderer.py` 스키마에 맞춰 ContractSummary 등 추가
```
- 이유: KR 모듈은 DART API 키 + 한국어 라벨 + 원화 포맷이 깊게 박혀 있어서 한 모듈에 dispatch layer 끼우면 분기지옥. US 는 별도 모듈로 두고 상위 워크플로(예: INVESTMENT_REPORT_PIPELINE) 에서 시장(KR/US) 으로 dispatch.
- 통합 시 추가 작업: ① 본문 요약을 LLM 으로 한 줄 한국어 번역, ② 가이던스 매칭 (수주잔고 vs YTD 목표) — KR `summarize_contracts` 와 대응.

## 변경 이력
- 2026-05-26 — 최초 생성. 5종목 PoC (AAPL/NVDA/MSFT/TSLA/META) 90일 필링 fetch + 카테고리 분류 + markdown 리포트 동작 확인.
