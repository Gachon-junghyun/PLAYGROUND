# 디스패치 브리프 — PLAY42: US corp 임베딩 재구축 + 집중도(ENB) 진단

> 이 파일을 새 Claude에게 그대로 주면 PLAY42를 만든다. 너는 이 대화 기억이 없는 fresh 상태라고 가정하고 썼다.
> 먼저 루트의 `CLAUDE.md`(PLAYGROUND 규칙)와 `VENV_GUIDE.md`를 읽어라. 아래는 그 위에 얹는 PLAY42 전용 설계 지시다.
> **이건 PLAYGROUND 실험이다. 프로덕션(`C:\Users\fivep\OneDrive\Desktop\mvp\research_Mvp`)의 DB·코드는 읽기만 하고 절대 수정하지 마라.** 검증되면 그때 사용자가 직접 포팅한다.

---

## 한 줄
프로덕션 자율매매 엔진에서 **현재 "미측정"으로 비워둔 두 가지** — ① 보유 바스켓의 **실효 베팅수(ENB)·종목간 상관**(집중도 진단) ② 신규 후보가 기존 보유와 **얼마나 같은 베팅인가**(peer 발굴) — 를 PLAYGROUND에서 프로토타입해서, 통하면 프로덕션 `trading_engine`에 꽂는다.

## ⚠️ 왜 (design intent — 이거 안 읽으면 엉뚱한 걸 만든다)

프로덕션에 `trading_engine`이라는 모의 자동매매 엔진이 있다(US 종목 9개 추세 바스켓 = NVDA·TSM·MU·META·MSFT·GOOGL·VST·GEV·CEG, 거기에 검증·공격 책). 그 룰 SSOT(`research_Mvp/docs/모의투자_룰_정제.md`) **§0**가 못박은 진실:

> "AI&전력 10종목은 분산이 아니라 **하나의 베팅**이다. PCA 1요인이 변동의 60~75%(폭락일 ~100%) 흡수. 실효 베팅수(ENB)는 6~12종목 들어도 현실 **2~4**. NVDA-AVGO 0.53→0.66, VST-CEG 0.77. DeepSeek 쇼크: NVDA −17%·VST −28%·GEV −21%·CEG −21% 동반."

그런데 같은 문서 **§3 정직 규칙**이 인정한다:
> "**ENB·평균 pairwise 상관 — 공분산 행렬 필요. 별도 스크립트 없으면 서브테마 캡+breadth로 대용하고 'ENB 미측정'이라고 표기**(분식 금지)."

즉 엔진은 "이 바스켓은 사실상 1개 베팅"이라는 걸 **알면서도 그 집중도를 숫자로 못 재서** 캡으로 어림하고 있다. PLAY42가 그 빈틈을 메운다.

**핵심 통찰 (이걸로 실험이 두 갈래가 된다 — 섞지 마라):**
- **집중도/ENB/상관 = 수익률 공분산이 정답. 임베딩 아님.** ENB는 *같이 움직이느냐*(return correlation)의 문제다 → yfinance 일간수익률 상관행렬 → ENB. **임베딩 필요 없음.** 이게 §3 "미측정"을 직접 메우는 본체다.
- **peer 발굴/사업유사도 = 임베딩.** "이 신규 후보가 내가 이미 든 종목과 *같은 사업*인가"(=중복 베팅 경고) → 사업설명 임베딩 코사인. 이게 corp_embeddings 재구축이 필요한 부분.
- 둘은 **다른 신호**다. 임베딩 유사도 ≈ 수익률 상관의 *구조적 프록시*일 뿐(사업 비슷하면 대체로 같이 움직임). 둘을 교차검증하면 강력하지만, **ENB를 임베딩으로 재려고 하면 틀린다.**

## 이미 있는 재료 (재구축 금지 — 읽어서 미러링/복사만)

프로덕션 `research_Mvp/` 안 (읽기전용 소스):
- **US 유니버스 완성본**: `data_build/us_universe/us_universe.csv` — **516종목**(S&P500+NDX100), 컬럼 `ticker,name,gics_sector,gics_industry,source`. GICS 섹터/산업까지 있음 → 서브테마 캡·클러스터 라벨에 바로 씀. (`us_aliases.json`·`coverage_report.md`도 참고.)
- **KR 임베딩 파이프라인(미러링 대상)**: `data_build/build_embeddings.py` (DART 사업설명→Gemini 임베딩→`corp_embeddings.db`), `data_build/extract_business.py` (DART "II. 사업의 내용" 추출). **US판은 DART 대신 EDGAR 10-K Item 1(Business)로 소스만 바꾸면 된다.**
- **EDGAR 페처**: 프로덕션 `module_disclosure_us/_edgar_api.py` + PLAYGROUND `PLAY27_edgar_fetch/`(`_ticker_cik.py`·`_renderer.py`) — ticker→CIK→10-K 본문. Item 1 추출 로직만 얹으면 됨.
- **임베딩 소비 모듈(살리려는 대상)**: `module_embedding`(peers/matrix/audit/stats 서브커맨드)·`module_industry_map`(서브테마 클러스터링). 둘 다 `corp_embeddings.db`를 읽는데 **지금 그 DB는 한국 832종목뿐**이라 US엔 죽어있음.
- **임베딩 모델**: Gemini `embedding-001`, **3072d, task_type=SEMANTIC_SIMILARITY** (KR과 동일하게 맞춰야 module_embedding이 그대로 작동).

**`corp_embeddings.db` 스키마 (US판도 똑같이 만들어야 module_embedding 재사용 가능):**
```sql
CREATE TABLE corp_descriptions (
  ticker TEXT PRIMARY KEY, corp_name TEXT NOT NULL, corp_code TEXT,
  rcept_no TEXT, rcept_dt TEXT, section_text TEXT, embed_text TEXT,
  embedding BLOB,        -- float32 3072개 raw bytes
  embed_model TEXT, embed_dim INTEGER );
CREATE TABLE build_log ( ticker TEXT, status TEXT, error TEXT, timestamp TEXT );
```

PLAYGROUND 인접 실험: `PLAY26_us_universe`(유니버스 빌드)·`PLAY27_edgar_fetch`(EDGAR)·`PLAY2_chart_embedding`(임베딩 집계)·`PLAY12_concept_corpus`. 바퀴 다시 만들지 말고 차용.

## 이번에 만들 척추 (PLAY42 = 두 트랙 병렬)

**트랙 A — 집중도/ENB 진단 (임베딩 불필요. §3 미측정 직격. 먼저 이걸로 빠른 승부)**
1. `s1_returns.py` — yfinance로 바스켓(9종 + 후보) 일간 종가 → 로그수익률, 최근 ~120·252 거래일.
2. `s2_enb.py` — 수익률 **상관행렬** + **공분산** →
   - 평균 pairwise 상관(룰 §0의 0.53~0.77 재현되나?)
   - **ENB 두 방식**: (a) 비중 기반 `1/Σwᵢ²` (b) **PCA/고유값 기반** `exp(H(λ̂))` (λ̂=정규화 고유값, H=엔트로피) — 룰 §0 "ENB 2~4·1요인 60~75%" 검증.
   - 출력: 상관히트맵(텍스트), ENB, PC1 설명력%, 폭락일 시뮬(전종목 −1σ 동반 시 바스켓 손실).
3. 산출: `enb_report.md` + `enb.json`(trading_engine가 읽을 수 있는 스키마).

**트랙 B — US corp 임베딩 재구축 (peer 발굴)**
4. `s3_universe_subset.py` — 우선 **AI&전력 바스켓 + 인접 peer ~40~80종목만**(전 516개 아님 — Gemini 호출비·시간). seed = 9 보유 + AVGO·AMD·SMCI·ARM·ASML·AMZN·ORCL·OKLO·SMR·NRG·ETN·PWR·NEE 등 GICS로 추려.
5. `s4_edgar_business.py` — 각 ticker → EDGAR 최신 10-K **Item 1(Business)** 클린텍스트(PLAY27/module_disclosure_us 차용).
6. `s5_embed.py` — Item 1 텍스트 → Gemini embedding-001 3072d → `corp_embeddings_us.db`(**위 스키마 그대로**, embedding=float32 BLOB).
7. `s6_peers.py` — 코사인으로 peers/matrix/ENB(임베딩판). NVDA→peers가 AVGO·AMD 등 말 되는지, 임베딩-유사도 행렬 vs 트랙A 수익률-상관 행렬 **교차검증**(둘이 얼마나 일치?).

## 성공 기준 (이게 되면 프로덕션 포팅 가치 있음)
- **A**: 9종 바스켓 ENB가 룰 §0 주장(2~4)과 같은 자릿수로 나오고, PC1 설명력 60%+ 재현. → 그러면 `trading_engine`에 `concentration` 명령으로 꽂아 §3 "ENB 미측정"을 **실측치**로 교체.
- **A**: 신규 후보를 넣었을 때 "이 후보 추가 시 ENB 변화/한계상관" 계산 → 캡 대용이 아니라 **진짜 분산 기여** 게이트.
- **B**: `corp_embeddings_us.db`로 module_embedding `peers NVDA`가 US peer 반환(현재는 빈 결과). 임베딩-유사도 vs 수익률-상관 상위쌍 ≥60% 겹치면 "사업유사도=상관 프록시" 가설 확증.

## 포팅 계획 (실험 성공 시 — PLAYGROUND에선 만들기만)
- 트랙A `enb.json` → 프로덕션 `trading_engine/`에 `concentration.py` + `concentration` CLI로 이식. dashboard에 "ENB·PC1%·평균상관" 추가, size 게이트에 "후보 추가 후 ENB 하락폭" 추가(G5 캡의 정량 상위호환).
- 트랙B `corp_embeddings_us.db` → `research_Mvp/`로 복사 → module_embedding/module_industry_map US 부활.

## 가드레일 / 환경
- **PLAYGROUND 안에서만**. 프로덕션 `corp_embeddings.db`(한국 832종) 건드리지 말 것 — US는 **새 파일 `corp_embeddings_us.db`**.
- venv: PLAYGROUND `VENV_GUIDE.md` 따를 것. 의존: yfinance·numpy·scipy·pandas·requests + google-genai(임베딩).
- 키: `GEMINI_API_KEY`(임베딩), `SEC_USER_AGENT`(이메일 — EDGAR Fair Access 필수). EDGAR는 호출당 ~0.2s sleep(rate limit).
- 비용 절제: 트랙A 먼저(임베딩비 0). 트랙B는 ~40~80종목으로 시작, 전 516개는 검증 후.
- **정직 규칙**: 임베딩 유사도 ≠ 수익률 상관임을 리포트에 명시. 못 잰 건 "미측정"으로 표기(분식 금지). 표본 작으니(거래 연 10~30회) 상관·ENB는 롤링 재계산, 소수점 최적화 금지.

## 첫 턴에 할 일
1. `CLAUDE.md`·`VENV_GUIDE.md` 읽기. 2. `PLAY42_us_corp_embeddings/` 폴더 생성 + README.md(이 브리프 요약). 3. **트랙 A부터** (s1_returns→s2_enb) — 9종 바스켓 ENB를 먼저 숫자로 띄워 룰 §0 검증. 4. 결과 보고 후 트랙 B 진행 여부 판단.
