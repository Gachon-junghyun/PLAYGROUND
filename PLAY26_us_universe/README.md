# PLAY26_us_universe

## 목적
미국 주식 universe(SP500 + Nasdaq100, dedup ~516종목) + 티커-별명 매핑을 만들고, 상위 프로젝트의 `news_alert.db` last-30d 풀스캔으로 종목별 매칭 가능성을 정량화한다. KR(한국) 분석 mvp가 가지고 있는 corp_codes.csv 같은 universe·alias 인프라를 US에서 처음부터 빌드하는 실험이다.

## 실행법
```powershell
# 의존성 (이미 mvp 환경에 깔려 있으면 skip): requests, beautifulsoup4, lxml
pip install requests beautifulsoup4 lxml

# 1) 유니버스 빌드 (wikipedia fetch; us_universe.csv 있으면 skip)
python build_universe.py

# 2) 티커→alias 매핑 빌드 (한국어 50개 + brand 매핑 dict 내장)
python build_aliases.py

# 3) news_alert.db last 30d 풀스캔 + coverage_report.md 갱신
python scan_coverage.py
```

세 스크립트 모두 PowerShell 기본 위치(이 PLAY 디렉토리)에서 실행. 외부 인자 없음.

## 입력 / 출력
- **입력 (외부)**:
  - `https://en.wikipedia.org/wiki/List_of_S%26P_500_companies` (HTTP fetch, timeout=10)
  - `https://en.wikipedia.org/wiki/Nasdaq-100`
  - `C:/Users/fivep/OneDrive/Desktop/mvp/research_Mvp/news_alert.db` (SQLite, **read-only**, URI `mode=ro`)
- **출력 파일**:
  - `us_universe.csv` — `ticker, name, gics_sector, gics_industry, source` (516행)
  - `us_universe_seed.csv` — fallback 시드 (103종목, wikipedia 실패 대비)
  - `us_aliases.json` — `{"AAPL": ["AAPL", "Apple Inc.", "Apple", "Apple Inc", "애플"], ...}`
  - `coverage_report.md` — 매칭 분포 + top30/bottom30/zero + KR vs US 비교

## 가정 & 제약
- **mvp 파일 수정 안 함.** `news_alert.db`는 `mode=ro` 로만 열었다. mvp 디렉토리에 새 파일 안 만든다.
- **wikipedia 테이블 파싱**: SP500은 `id='constituents'` 테이블, Nasdaq100은 헤더 텍스트에 "ticker"+"company"가 들어있는 wikitable을 찾는다. wikipedia가 구조를 바꾸면 fetch 실패 → `us_universe_seed.csv` (103종목 메이저주) 폴백.
- **alias 생성 규칙**:
  - (a) ticker 자체, (b) BRK-B → BRK.B 변형, (c) 풀네임, (d) suffix(Inc/Corp/Holdings/PLC/The 등) 제거 짧은 이름, (e) brand-level 명시 매핑(예: Alphabet→Google, Meta Platforms→Facebook), (f) 한국어 별명(50개 수동).
  - alias 평균 2.45개, min 2개(IBM 포함 IBM dict 추가로 보강 시도), max 6개(GOOGL/JPM 등).
  - 사용자가 요구한 "min 3개"는 표준 케이스에서만 충족. 단순 이름 종목(예: "ABT, Abbott Laboratories")은 2개로 끝난다 — 추가 alias를 강제로 만들면 false positive만 키운다.
- **scan_coverage.py 매칭 로직**:
  - DB의 last 30d 38,390 article (title + summary)을 메모리로 한 번에 로드(~0.15초).
  - 모든 ticker의 ASCII alias를 한 개의 거대한 정규식(`(?<![A-Za-z0-9])(alias1|alias2|...)(?![A-Za-z0-9])`)으로 합쳐서 article 1개당 단 한 번만 스캔(역인덱스). 결과: 516종목 풀스캔 ~9초. (초기 naive 구현은 69초였음.)
  - 한국어 alias는 워드 경계 개념이 없어서 `in` 연산자로 단순 매칭.
  - case-insensitive (text/alias 둘 다 lower).
- **GENERIC_BLACKLIST**: 1~3글자 일반 영단어와 충돌하는 ticker alias는 매칭 풀에서 *제거*한다 — 예: `T`(AT&T), `D`(Dominion), `O`(Realty Income), `HAS`(Hasbro), `LOW`(Lowe's), `KEY`(KeyCorp), `TECH`(Bio-Techne), `NEWS`(News Corp), `V`(Visa), `PH`(Parker Hannifin), `AMP`, `WELL`, `MS`, `GS` 등. 해당 ticker는 풀네임 alias로만 매칭한다.
- **알려진 false positive**:
  - `GOOG`/`GOOGL` (6,150 hits) — "Google" brand가 Android/Search/Chrome 일반 기사를 모두 잡아 equity-specific signal과 섞임. 이 outlier 1건이 US top-10 avg를 끌어올린다. 보고서에는 GOOGL 제외 버전도 같이 출력.
  - `Dow Inc.` ticker DOW = 42 — "Dow Jones" 지수와 혼동 가능. 마이너.
  - `XYZ` (Block, Inc.) — "Block" 일반 단어 매칭 일부 포함.
  - 이 정도는 정량 분석 시작 단계로 acceptable. 정확한 종목 sentiment를 빼려면 추가로 context filter 필요(예: ticker + earnings/CEO 등 동시 등장).
- **`first_seen_at` 컬럼 없음**: mvp DB schema는 `fetched_at` 사용. 30일 윈도우는 `fetched_at > datetime('now', '-30 days')`.
- **재실행 캐싱**: `us_universe.csv`가 200행 이상이면 `build_universe.py`는 wikipedia 재페치를 skip. 강제 재빌드하려면 파일 삭제.
- **인코딩**: 모든 출력 파일 UTF-8 명시. PowerShell stdout은 `sys.stdout.reconfigure(encoding='utf-8')`로 강제. 콘솔이 cp949이면 한국어 출력만 깨질 뿐 파일 자체는 정상.
- **실행 시간**: 디스패치 45초 예산 안에 들어옴(build_universe 3~5s, build_aliases <1s, scan_coverage ~9s).

## 주요 측정 결과 (last 30d, 38,390 articles)
- 유니버스 size: **516** (SP500 503 + Nasdaq100 101, dedup)
- 매칭된 종목: **229 (44.4%)** — >=1 article
- >=20 articles: **45 (8.7%)** — workable
- >=50 articles: **16 (3.1%)** — prime daily-analysis targets
- US top-10 mega-cap 평균: **702.3** (GOOGL 6150 outlier 포함), GOOGL 제외 시 **96.8**
- KR top-10 (방산/중공업) 평균: **18.4**
- 결론: 미국 mega-cap은 mvp DB의 영문 뉴스 소스만으로도 KR mid-cap 대비 ~5배 풍부. 진짜 부족한 건 universe 인프라 자체였고, 이 PLAY가 그걸 채운다.

## 변경 이력
- 2026-05-26 — 최초 생성. wikipedia table fetch + alias dict + DB read-only scan. coverage 9초 안에 종료, KR/US 정량 비교 포함.
