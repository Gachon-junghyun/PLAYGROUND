# PLAY44_prompt_compiler

## 목적
프롬프트를 완성품이 아니라 **명제 단위 부품(records)** 으로 저장해두고, 매 요청마다 `[명령 → 변환 → 임베딩 검색 → 조립 → 실행]` 으로 컴파일하는 실험. v1 코퍼스는 **금융 사고카드 클러스터**(PLAY13/28 R4 카드 + PLAY43 R5 v4 함수 + 계산-레이어 도구 카드)로 한정한다.

## 왜 이 코퍼스인가 (스코프 결정)
PLAYGROUND 43개 PLAY 중 *명제 단위 지식*이 실제로 들어있는 건 두 덩어리뿐이다 — 금융 사고카드(13·28·29·31·32·43)와 사고 플레이북(34·37·38·40·41). 나머지(TTS·서버·리포트·sync 등)는 tool_card 한 장이거나 추출할 명제가 0이라, 같은 record pool에 부으면 trigger 충돌·검색 노이즈만 늘고 **컴파일러가 망해도 아키텍처 결함인지 코퍼스 오염인지 분리 진단이 불가능**해진다. 그래서 v1은 가장 익은 한 클러스터(금융 사고카드)만 씨앗으로 쓴다. "전 PLAY 통합"은 v1이 깨끗하게 검증된 *다음* aspect/namespace를 도메인별로 분리해 붙이는 스트레스 테스트로 미룬다.

결정적 이점: 이 코퍼스는 **이미 명제+트리거 구조**다. 카드의 `reasoning_move`(사고 무브)+`trigger_conditions`(상황), 함수의 `abstract_form`+`trigger_when`("~할 때" 문체)이 컴파일러 레코드 필드에 그대로 떨어진다. 그래서 Part A의 추출은 *구조 매핑*이지 백지 추출이 아니다.

## 디렉토리 구조
```
PLAY44_prompt_compiler/
├─ README.md                     # 이 파일 (계약서)
├─ requirements.txt              # Part B 의존성
├─ knowledge/
│  ├─ build_records.py           # Part A: 기존 카드/함수 코퍼스 → records.jsonl 어댑터 (stdlib만)
│  ├─ build_viewer.py            # records.jsonl → 자기완결 viewer.html 생성 (stdlib만)
│  ├─ viewer.html                # [산출] 브라우저 뷰어: 대시보드+카드 브라우저+검색 시뮬레이터
│  ├─ records.jsonl              # [산출] 레코드 1개 = 1줄
│  ├─ inventory.md               # [산출] 모듈 인벤토리
│  └─ extraction_report.md       # [산출] 타입 분포·금지문 스캔·trigger 적합·conflict 검사
└─ compiler/                     # Part B: 컴파일 파이프라인
   ├─ embed_store.py             # B1 적재: trigger 임베딩 → SQLite(records/vec_triggers/meta)
   ├─ transform.py               # B2 변환: 원명령 → 측면별 행동 키(Haiku, 무키 시 폴백)
   ├─ retrieve.py                # B3 검색: dense+BM25 → RRF(k=60), 측면 네임스페이스, 타입별 예산
   ├─ assemble.py                # B4 조립(순수 코드): core+conflict 생존+순서+usage_count
   ├─ run.py                     # B5 실행기 + 4단계 진단 로그
   ├─ smoke.py                   # B6 스모크: stub 백엔드로 키 없이 검색/조립 검증
   ├─ store.db                   # [산출] 적재 DB
   └─ logs/                      # [산출] 요청별 진단 로그 + smoke_report.md
```

## 실행법
```powershell
# --- Part A: 레코드 빌드 (의존성 없음, stdlib만, 몇 초) ---
python PLAY44_prompt_compiler/knowledge/build_records.py
#  → knowledge/records.jsonl + inventory.md + extraction_report.md 생성

# --- 사고 레코드 뷰어 (눈으로 검증용, 의존성 0) ---
python PLAY44_prompt_compiler/knowledge/build_viewer.py
#  → knowledge/viewer.html 생성. 더블클릭(또는 `start viewer.html`)으로 브라우저에서 열면:
#     상단 대시보드 / 측면·타입·tier·소스 필터 + 검색 / "이 상황이면 무엇이 발동하나" BM25 시뮬레이터

# --- Part B 스모크: 키 없이 오프라인 검증 (stub 백엔드, 의존성 0) ---
cd PLAY44_prompt_compiler/compiler
$env:EMBED_BACKEND="stub"; python smoke.py    # → logs/smoke_report.md (검색/조립/예산/순서 검증)

# --- Part B 실제 사용: Gemini 임베딩 + Anthropic ---
pip install -r ../requirements.txt            # 사전 설치(실행 경로에 두지 말 것)
$env:EMBED_BACKEND="gemini"                    # 기본. openai / bge 도 가능
$env:GEMINI_API_KEY="..."                      # 임베딩 (aistudio.google.com/apikey)
$env:ANTHROPIC_API_KEY="..."                   # 변환(Haiku) + 실행
python embed_store.py                          # 적재(trigger 임베딩)
python run.py --dry-run "현대차 3분기 실적 적대적으로 검토해줘"   # 조립만
python run.py "현대차 3분기 실적 적대적으로 검토해줘"            # 조립 + 실행
# off-domain 오발동을 막으려면 floor 를 튠: $env:MIN_DENSE="0.4" (Gemini 스코어 기준)
```

## 입력 / 출력
- **입력 (Part A):** 같은 리포에 이미 있는 카드/함수 파일 — `PLAY28/.../r4_all_cards.jsonl`, `r4_new_cards.jsonl`, `PLAY13/.../r4_all_cards.jsonl`, `PLAY43/data/v4_index.json`. 인자 없음 (경로는 스크립트에 박혀 있음).
- **출력 (Part A):** `knowledge/records.jsonl` (레코드), `inventory.md`, `extraction_report.md`.
- **레코드 스키마:** `{"id","type","text","aspect","trigger","tier","conflict_group","source","usage_count"}` — `type ∈ {proposition, procedure, tool_card, exemplar}`, `aspect ∈ {작업유형, 사고스타일, 출력형식, 도메인규칙}`, `tier ∈ {core, contextual}`. embedding 필드는 두지 않음(Part B 적재 때 trigger를 임베딩).

## 가정 & 제약
- **스코프:** v1은 금융 사고카드 클러스터 한정. 다른 PLAY 코드를 import 하지 않으며, 카드 파일은 *읽기 전용*으로 복사만 한다(원본 불변).
- **PLAY13 vs PLAY28 중복:** PLAY28은 PLAY13의 v2다. 카드는 `card_id` 기준 dedup, PLAY28(r4_new → r4_all) 우선, 그다음 PLAY13. 함수는 PLAY43의 v4_index(87개, 최신)만 사용.
- **trigger 합성 (정직하게 적는 한계):** 함수의 `trigger_when`은 이미 "~할 때" 문체라 그대로 쓴다. 카드는 `trigger_conditions`가 구체 *뉴스 이벤트*라 컴파일러 trigger(상황 서술)와 문체가 다르다 → labels+framework로 "~판단할 때" 템플릿을 합성한다. **이 템플릿 trigger는 기계적이라, 품질을 올리려면 Haiku 1회 폴리시 패스(`transform_records.py`, ANTHROPIC_API_KEY 필요)가 권장된다.** v1 records.jsonl은 그 패스 없이도 검색은 돌지만, 카드 trigger의 변별력은 함수만 못하다.
- **긍정 명령형 변환:** 스크립트는 금지문(`마라/말 것/금지/피하라/절대/하지 마`)을 스캔해 `extraction_report.md`에 *건수와 목록*을 남긴다. 원본 `reasoning_move`는 대부분 서술형(금지문 아님)이라 자동 합격이지만, 걸린 레코드는 LLM 폴리시 패스에서 명령형으로 바꿔야 셀프체크(금지문 0건)를 완전히 통과한다. 현재 상태는 report에 명시.
- **core tier:** 계산레이어/권유레이어 분리 같은 mvp 보편 원칙 소수만 core로(전체의 10% 이하 목표). 실측 4/192 = 2.1%.

### Part B 설계·검증 메모
- **임베딩 백엔드 = Gemini 기본.** `gemini-embedding-001`은 호스티드 옵션 중 한국어(MTEB multilingual) 1등이고, task_type 비대칭(trigger=`RETRIEVAL_DOCUMENT` 저장 / 행동 키=`RETRIEVAL_QUERY` 검색)이 이 설계와 정확히 맞물린다. 이 규모(192레코드)에선 비용 ~$0.002, 다운로드 없음. `EMBED_BACKEND`로 `openai`(3-small)·`bge`(로컬 ~2GB)·`stub`(무키 검증용) 전환.
- **stub 백엔드:** 결정론적 해시 임베더. 키·외부패키지 없이 검색→조립→예산→로그 배관을 오프라인 검증하려고 넣었다(CLAUDE.md "끝낼 때 실행 가능"). 의미 품질은 실제 백엔드(Gemini)가 낸다.
- **CLAUDE.md 우선 적용한 의존성 결정:** 원 스펙은 sqlite-vec/rank-bm25를 요구하나, "stdlib 우선 + 끝낼 때 실행 가능"에 맞춰 dense(cosine)·BM25·RRF를 **순수 파이썬**으로 구현해 stub면 패키지 0으로 돈다. sqlite-vec는 *있으면* 가속에 쓰는 선택지로 강등. 벡터는 SQLite에 JSON으로 저장.
- **transform 은 Haiku 필요.** `ANTHROPIC_API_KEY` 없으면 원명령을 작업유형 단일 키로 폴백(스펙대로) → 파이프라인은 돌지만 교차측면 검색은 안 됨. 그래서 스모크는 행동 키를 직접 주입해 stage 2~4를 검증한다.
- **모델 불일치 가드:** 적재 모델명을 DB meta에 박고, 다른 모델로 검색 시 즉시 에러. 백엔드 바꾸면 `embed_store.py` 재적재 필요.
- **토큰 카운트는 근사**(글자수/2). 예산 컷 용도라 충분하나 정밀 회계는 아님.
- **스모크 관찰(`logs/smoke_report.md`):** on-domain 2건(종목분석·매매플랜)은 직관 적중 — "가격 시계열"→`t-001`, "밸류 트랩"→`f-084`(절대밸류 카드), "손익 계산"→`t-002`. 예산·순서·exemplar top-1 컷 정상. **off-domain 1건(연애편지)이 설계 갭을 노출**: dense 절대 하한이 없어 낮은 점수로도 top-3를 채운다 → `MIN_DENSE` floor 훅 추가(기본 0.0). **Gemini 연결 후 첫 튜닝 대상**: off-domain은 떨어지고 on-domain은 사는 floor 값을 스모크로 찾을 것.
- **알려진 한계:** ① 카드 trigger 템플릿은 변별력이 함수 trigger_when보다 약함(폴리시 패스로 개선). ② `작업유형` aspect 레코드가 core 1개뿐이라, 작업유형 키로 검색하면 거의 안 걸림 — 코퍼스가 사고스타일에 쏠림. ③ conflict_group은 현재 전부 null(의미 모순 그룹핑은 적재 후 임베딩 근접쌍으로 부여 예정) — 생존 로직 자체는 구현·동작.

## 현재 상태 (스테이징)
- [x] **Part A** — `build_records.py` 어댑터 + records.jsonl(192)/inventory/report. 셀프체크 통과(금지문 0, core 2.1%).
- [x] **Part B 코드 + 오프라인 검증** — 5모듈 + smoke.py. stub 백엔드로 검색/RRF/예산/conflict/순서/진단로그 전부 검증. 중복채택 버그 fix, MIN_DENSE floor 훅 추가.
- [ ] **Part B 실측** — Gemini+Anthropic 키로 실제 임베딩/변환/실행 1회 + MIN_DENSE 튜닝. (TODO: 키 들어오면 `embed_store.py`(gemini) 재적재 → smoke로 floor 튠 → README 이 줄 갱신)
- [ ] **v1 검증 후** — 사고 플레이북 클러스터를 별도 namespace로 추가하는 스코프 확장 스트레스 테스트.

## 변경 이력
- 2026-06-12 — `build_viewer.py` 추가. records.jsonl → 자기완결 `viewer.html`(대시보드+카드 브라우저+검색·필터+BM25 발동 시뮬레이터). 의존성 0, 더블클릭 실행. 사고 레코드 내용을 눈으로 검증하는 용도.
- 2026-06-12 — 최초 생성. Part A(금융 카드/함수 → records.jsonl 192개) + Part B 5모듈 구현. stub 백엔드로 키 없이 오프라인 스모크 검증 완료(중복채택 버그 fix, off-domain floor 훅 추가). 임베딩 기본 백엔드는 Gemini(한국어 1등 + task_type 비대칭 적합). 실측(Gemini 키)·floor 튜닝은 다음 단계.
