# PLAY25_us_rss_expansion

## 목적
mvp(news_alert.db)에 부족한 미국 외신 RSS 7~10개를 후보로 등록하고, 24h 풀로 fetch+본문 스크랩 성공률을 측정한 뒤 mvp에 merge 가능한 매체를 가려낸다. 부수적으로 Bloomberg "title+summary 만으로 카드 합성이 가능한가?" PoC와 Google News redirect 해석 PoC를 같이 돌린다.

## 실행법
```powershell
# mvp와 동일한 venv면 추가 설치 불필요. 없으면:
pip install requests feedparser beautifulsoup4 lxml

cd C:\Users\fivep\OneDrive\Desktop\PLAYGROUND\PLAY25_us_rss_expansion
python audit.py
# → audit_report.md 갱신, stdout에 "DONE: N feeds tested, M successful"
```

## 입력 / 출력
- **입력 (코드 내장):**
  - `feeds_us.py` — 12개 후보 피드 (Reuters x2, Seeking Alpha x2, Yahoo Finance x5 ticker, SEC EDGAR 8-K, PRNewswire, BusinessWire, MarketWatch MarketPulse, Investing.com).
  - `selectors_us.py` — 매체별 본문 CSS selector dict (mvp `SOURCE_SELECTORS` 포맷 호환).
  - mvp DB 경로 하드코딩: `C:\Users\fivep\OneDrive\Desktop\mvp\research_Mvp\news_alert.db` (Step 2 전용, 없어도 Step 1/3은 동작).
- **출력:**
  - `audit_report.md` — Step1 per-feed 표 + 소스별 집계 + Step2 키워드 클러스터 + Step3 redirect 표.
  - stdout: 진행 로그 + 마지막 라인 `DONE: N feeds tested, M successful (wall Xs) -> audit_report.md`.

## 가정 & 제약
- **Reuters는 공식 RSS를 2020년에 종료**한 것으로 알려져 있어, 두 fallback URL(`reutersagency.com`의 best-topics 피드 + `news.google.com` site:reuters.com 검색)을 함께 등록했다. 둘 다 실패하면 Reuters는 mvp 통합에서 보류하고, 본문 스크랩만 mvp scraper 쪽에 추가하는 식의 후속 작업이 필요하다.
- **Yahoo Finance per-ticker RSS는 종종 캐시·CDN 단에서 200 빈 피드를 내려주는 경우가 있다.** 24h 풀에 0건이어도 selector는 사전에 준비.
- **SEC EDGAR**는 정책상 `User-Agent`에 식별 가능한 연락처가 필요하므로 `"Researcher Contact: fivepeople201@gmail.com"`로 호출. 다른 모든 매체는 mvp와 동일한 Chrome UA.
- **본문 스크랩 측정은 피드당 첫 2건만** 수행한다 (`SCRAPE_PER_FEED=2`). 디스패치 45초 안에 끝내기 위함이고, 매체 단위 성공률은 통계적으로 충분하지 않을 수 있다 — 추세 신호용으로만 사용하고, mvp merge 결정은 24h 실제 운영 후 재검증 필요.
- **Step 1의 dup_rate는 같은 피드 *안에서*의 제목 sha256 충돌**만 본다. 피드 간 교차 중복(같은 Reuters 기사가 PRNewswire에도 뜨는 케이스)은 측정 범위 밖.
- **Step 2의 매크로 키워드 추출은 LLM 없이 정규식 빈도 기반 휴리스틱**이다. "Fed", "Treasury yield" 같은 단순 매칭이고, 부정문/맥락 무시 — PoC 수준의 신호 존재 증명용일 뿐 실서비스 합성에는 별도 LLM 호출이 필요하다.
- **Step 3의 Google redirect 해석**은 `requests.get(allow_redirects=True).url`이 google.com 외부 도메인이면 성공으로 친다. 실제로는 Google이 중간에 JS-only 인터셉터(`?continue=`)를 거는 경우도 있어, 본문 스크랩까지 가려면 추가 hop이 필요할 수 있다.
- **PLAY 간 의존 금지 규칙 준수.** mvp의 `RSS_FEEDS`/`SOURCE_SELECTORS`는 *읽기 전용*으로 포맷만 참고했고, mvp 파일은 일절 수정하지 않았다.
- **wall-clock 목표 ~50초.** ThreadPoolExecutor(MAX_PARALLEL_FEEDS=8, MAX_PARALLEL_SCRAPES=6) + 피드/스크랩 타임아웃 8초로 묶어두었다. 특정 매체가 connection-hang 하면 8초 늦어진다.

## mvp 통합 권장 기준
`audit_report.md`의 source-key 집계 표를 보고:
- **`feeds_ok > 0` & `scrape_rate >= 0.5`** → mvp `RSS_FEEDS`에 즉시 merge 가능, `SOURCE_SELECTORS`에 selectors_us.py 항목도 같이 등록.
- **`feeds_ok > 0` & `scrape_rate < 0.5`** → 헤드라인만 수집 (Bloomberg/NYT처럼 본문 0% 모드). Step 2 합성 파이프라인 대상으로 등록.
- **`feeds_ok == 0`** → 보류. URL 폐기됐거나 봇 차단. README 본 섹션에 사유 기록.

구체 권장 매체는 `audit_report.md`를 실행 후 확인 (실행마다 결과가 달라질 수 있으므로 README에 박지 않는다).

## 변경 이력
- 2026-05-26 — 최초 생성. 12 후보 피드 + 8 selector + 3-step audit 파이프라인. audit.py 검증 실행 1회 완료.
