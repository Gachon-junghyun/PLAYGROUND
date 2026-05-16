# PLAY12_concept_corpus

## 목적
개념·도메인 키워드를 받아서 (1) 사람용 입문 보고서 `report.md` 와 (2) RAG용 코퍼스 `sources.jsonl + texts/ + chunks.jsonl` 를 같이 만든다. 뉴스가 아니라 evergreen한 자료(서베이/표준/교과서/위키/핵심 논문) 중심.

## 의존
이 PLAY는 **외부에 설치된 `crawling` 패키지의 `agent.fetch` fetcher들** + **PLAY12 자체 `local_fetchers/`**를 같이 사용한다. 모든 fetcher가 `search(query, limit, **kw) -> List[Dict{url,title,body,source,fetched_at}]` 통일 인터페이스.

**agent.fetch (crawling 패키지)**

| backend             | 백엔드 종류                  | 키 필요? |
|---------------------|------------------------------|---------|
| `wikipedia:ko/en`   | Wikipedia                    | X       |
| `openalex`          | OpenAlex (학술 메타·인용)     | X       |
| `semantic_scholar`  | Semantic Scholar             | X       |
| `reddit`            | Reddit 검색                   | X       |
| `stackexchange`     | StackExchange (Q&A)          | X       |
| `dart`              | 금감원 전자공시 DART          | O (.env) |
| `sec_edgar`         | 미국 SEC EDGAR 공시           | X (UA 식별만) |
| `kosis`             | 통계청 KOSIS                  | O (.env) |
| `bok_ecos`          | 한국은행 ECOS                 | O (.env) |
| `gdelt`             | GDELT (글로벌 뉴스 이벤트)    | X       |
| `rss`               | RSS                          | X       |
| `youtube`           | YouTube                      | X       |

**local_fetchers (PLAY12 자체)**

| backend     | 백엔드 종류                                         | 키 필요? |
|-------------|------------------------------------------------------|---------|
| `arxiv`     | arxiv.org Atom API (영문 학술)                       | X       |
| `crossref`  | Crossref REST API (DOI 기반 학술 메타)               | X       |
| `scholar`   | Google Scholar — SerpAPI 또는 scholarly              | SERPAPI_KEY 또는 `pip install scholarly` |
| `dbpia`     | DBpia (best-effort) — KCI Open API 우선               | KCI_OPEN_API_KEY (있으면 안정) |

## 파이프라인 한눈에

```
[1] discover    →  raw_hits.jsonl                (agent.fetch + local_fetchers, query variants)
[2] aggregate   →  concepts.jsonl / sources.jsonl / hierarchy.json
[3] enrich      →  texts/*.full.txt / *.digest.txt  (raw_body 재활용 + HTML 페치)
[4] render      →  reports/<topic>.md             (메타 + 본문 인라인 + Mermaid + 도메인별)
[5] chunk       →  chunks.jsonl                   (RAG 색인용 청크)
[6] compose     →  reports/<topic>_full.md        (★ map-reduce: batch 요약 → 한 권짜리 입문서)
[*] synthesize  →  report.md 끝에 짧은 LLM 합성 섹션 (단발성, compose의 가벼운 버전)
```

`render`(4)는 **자료를 정리해서 보여주는 카탈로그**, `compose`(6)는 **자료를 읽어서 합성한 입문서**다. 둘은 산출물이 다르고 둘 다 필요.

모든 단계 산출물은 `data/<topic_slug>/` 안에 모인다. 같은 토픽 다시 돌리면 누적·갱신.

## 실행법

```powershell
# Python 3.10+. crawling 패키지가 같은 venv에 설치돼 있어야 함 (이미 설치됨).
# Windows에서 enrich 시 SSL 인증서 못 잡으면 --insecure.

cd PLAY12_concept_corpus

# 1) 수집 — 도메인별로 백엔드 묶어서 호출
python discover.py "전력 인프라 변압기" --domains tech,academic,policy_kr,industry_kr
#   --domains 가능: academic, tech, industry_kr, industry_us, policy_kr, community, events, all
#   --domains all    : 모든 도메인 (키 없는 백엔드는 자동 실패·무시)
#   --backends openalex,reddit,wikipedia:ko   : 도메인 우회, 백엔드 직접 지정
#   --limit 10                                  : 백엔드당 결과 개수
#   --list-domains                              : 도메인 정의만 보기
#   --sample / --validate                       : 오프라인 더미 / 형식 검증

# 2) 정규화: raw_hits → concepts/sources/hierarchy
python aggregate.py "전력 인프라 변압기"
#   --aliases "Power Transformer,electric transformer"   : 한·영 양쪽 매칭

# 3) 본문 보강 — mode 선택
python enrich.py "전력 인프라 변압기" --mode hybrid --fallback-abstract --insecure
#   --mode full|digest|hybrid       : 전부 통원문 / 전부 발췌 / authority=high만 full
#   --only src_001 src_007          : 특정 id만
#   --where authority=high           : 필터
#   --force                          : 이미 enrich된 것도 덮어씀
#   --fallback-abstract              : fetch 실패 시 abstract를 본문으로
#   --dry-run                        : 외부 fetch 없이 시연
#   --insecure                       : SSL 검증 우회 (Windows에서 CA 못 잡을 때)

# 4) 보고서 합성
python render_report.py "전력 인프라 변압기"

# 5) (선택) RAG용 청크 생성
python chunk_for_rag.py "전력 인프라 변압기" --chunk-size 800 --overlap 100

# 6) (핵심) batch 요약 → 한 권짜리 입문서 합성 (map-reduce)
python compose.py "전력 인프라 변압기" --batch-size 6
#   LLM 있으면 자동, 없으면 --provider claude_inline 으로 prompt 파일 dump
#
# claude_inline 흐름:
#   1) python compose.py "토픽" --provider claude_inline --clean
#      → data/<slug>/_compose/batch_NN.prompt.md 들 생성
#   2) Claude Code 세션(또는 사람)이 각 batch_NN.prompt.md 읽고
#      같은 자리에 batch_NN.response.md 로 한국어 요약 저장
#   3) python compose.py "토픽" --collect
#      → compose.prompt.md 생성 (batch 요약 묶음 + 합성 지시)
#   4) Claude/사람이 compose.response.md 로 최종 입문서 저장
#   5) python compose.py "토픽" --finalize
#      → reports/<slug>_full.md 완성

# 7) (선택) report.md 끝에 짧은 LLM 합성 섹션 append (synthesize는 단발성, compose는 본격적)
python synthesize.py "전력 인프라 변압기" --max-sources 10
#   --provider auto|ollama|anthropic|gemini   (auto: ollama → anthropic → gemini)
#   --model gemma3              : Ollama 모델명. Anthropic 기본은 claude-sonnet-4-6
#
# 필요 자격증명 (하나만 있으면 됨):
#   Ollama:    localhost:11434 서버 떠 있어야 함 (모델 미리 pull)
#   Anthropic: ANTHROPIC_API_KEY 환경변수
#   Gemini:    GEMINI_API_KEY / GOOGLE_API_KEY (crawling/.env 또는 환경변수)
```

## 도메인 프로파일

| 도메인         | 묶인 백엔드                                                     |
|---------------|----------------------------------------------------------------|
| `academic`    | openalex, semantic_scholar, **arxiv**, **crossref**, **scholar**, wikipedia:en |
| `academic_kr` | **dbpia** (KCI Open API 키 있으면 안정)                          |
| `tech`        | wikipedia:ko, wikipedia:en, stackexchange                       |
| `industry_kr` | dart, rss                                                       |
| `industry_us` | sec_edgar, rss                                                  |
| `policy_kr`   | kosis, bok_ecos                                                 |
| `community`   | reddit, stackexchange, youtube                                  |
| `events`      | gdelt, rss                                                      |

`all` 지정 시 위 전부. 키 필요한 백엔드는 키 없으면 빈 결과 + 나머지 계속.

## 토픽 별칭 (`--aliases`)

한국어 토픽인데 영문 자료도 잘 잡고 싶으면 aggregate에 `--aliases`를 준다. 각 alias는 독립 token group으로 평가돼 매칭 폭이 넓어진다 (alias 그룹 하나라도 매칭하면 적합).

```powershell
python aggregate.py "피지컬 AI" --aliases "Physical AI,Embodied AI,physical intelligence"
```

## 입력 / 출력
- **입력:** 토픽 문자열 (한국어/영어). 슬러그는 자동 생성 (공백·특수문자 → `_`).
- **출력:**
  - `data/<slug>/raw_hits.jsonl` — 수집 원본 (1줄=1 hit)
  - `data/<slug>/concepts.jsonl` — 개념 정의 (term, definition, parent, related, sources)
  - `data/<slug>/sources.jsonl` — 자료 메타 (url, type, authority, year, abstract, text_path, text_mode)
  - `data/<slug>/hierarchy.json` — 개념 트리
  - `data/<slug>/texts/<src_id>.{full|digest}.txt` — 원문 본문
  - `data/<slug>/chunks.jsonl` — RAG 청크 (source_id, text_mode, offset, text)
  - `reports/<slug>.md` — 사람용 입문 보고서

스키마 자세한 정의는 [schema.md](schema.md), 디스패치 시 검색 지침은 [PROMPT.md](PROMPT.md).

## 가정 & 제약
- **`crawling` 패키지(`agent.fetch`)가 같은 Python 환경에 설치돼 있어야 함.** 사용자의 `~/Desktop/crawling`에 `pyproject.toml` 있고 editable install된 상태를 가정. import 실패하면 discover가 죽음.
- **PLAY 간 의존 금지 룰의 예외.** `crawling`은 PLAY가 아니라 별개 패키지라 import 허용.
- **각 백엔드가 raw_hit의 `concepts`/`parent_concept`을 풍부하게 채우진 않는다.** 어댑터가 단순히 `[topic]` 하나만 넣음. 그래서 hierarchy가 얕다. 깊이 있는 트리를 원하면 디스패치 환경의 Claude가 PROMPT.md 따라 raw_hits에 손으로 append하면서 `concepts`/`parent_concept` 정성껏 채우는 보강 단계를 더해야 한다.
- **키 필요한 백엔드(DART/KOSIS/BOK_ECOS)는 `crawling` 패키지 쪽 `.env`에 자격증명 박혀 있어야 동작.** 없으면 해당 백엔드 호출이 raise되거나 빈 결과. PLAY12 코드에선 try/except로 잡고 나머지 진행.
- **`enrich` HTML 페치는 `urllib` + `html.parser` 기반 간이 추출.** PDF·JS 렌더·로그인 페이지는 실패. `--fallback-abstract`로 abstract 대체 가능.
- **권위(authority) 분류는 source.type 기반 단순 규칙** (survey/standard/textbook=high, paper/wiki=medium, blog/news=low). 자료 자체의 평가가 아니라 type 기반 휴리스틱.
- **PLAY4_news_retrieval과 결이 다름.** PLAY4는 사건 중심. 여긴 개념 중심·누적. 같은 토픽이라도 두 PLAY는 보완재.
- **45초 디스패치 제약:** discover 도메인 한두 개(백엔드 3~5개) × limit 10 ≈ 5~20초. `--domains all`은 10+ 백엔드라 30초 넘을 수 있으니 부분 도메인을 권장.
- **시크릿:** PLAY12 코드에 직접 박은 키 없음. agent.fetch 모듈들이 알아서 자기 `.env`에서 읽음.

## compose 단계 — claude_inline 자세히

LLM 인프라(Ollama/Anthropic/Gemini) 없이도 Claude Code 같은 인터랙티브 세션에서 합성 가능. 디렉토리 구조:

```
data/<slug>/_compose/
├── batch_01.prompt.md       # batch 1의 system + user prompt
├── batch_01.response.md     # ← Claude/사람이 채워야 할 자리
├── batch_02.prompt.md
├── batch_02.response.md
├── ...
├── compose.prompt.md        # 최종 합성 prompt (--collect로 생성)
└── compose.response.md      # ← 최종 입문서 응답
```

prompt 파일은 `<!-- SYSTEM -->`/`<!-- USER -->` 마커로 system/user를 분리해 명시. Claude Code 세션에서는 그냥 "이 파일 읽고 response.md로 저장해줘" 라고 시키면 한 batch씩 처리 가능.

### batch 설계 옵션
- `--batch-size 6` — batch당 source 개수 (기본 8). 너무 크면 토큰 초과, 너무 작으면 batch 수 폭발.
- `--max-chars 4000` — source당 본문 cap (batch 컨텍스트 폭주 방지).
- `--clean` — `_compose/` 디렉토리 비우고 처음부터.

## 변경 이력
- 2026-05-15 — 최초 생성. 5단계 파이프라인 + mode-aware enrich + 더미 샘플 한 사이클.
- 2026-05-15 — discover에 실제 백엔드 추가 (wiki:ko, wiki:en, arxiv, tavily). enrich에 `--fallback-abstract` 옵션.
- 2026-05-15 — discover를 `crawling`의 `agent.fetch`로 통합. 자체 wiki/arxiv 코드 폐기. 도메인 프로파일 도입 (academic/tech/industry_kr/industry_us/policy_kr/community/events). Reddit·OpenAlex·Semantic Scholar·StackExchange·DART·SEC EDGAR·KOSIS·BOK ECOS·GDELT·RSS·YouTube 사용 가능.
- 2026-05-15 — 대규모 개선 패스:
  - discover: 쿼리 multi-variant (도메인별 suffix), rate-limit backoff, raw_body 보존
  - aggregate: type 자동 격상(survey/review/standard 인식), citations/upvotes 기반 authority 재계산, body 키워드 추출로 concept 보강
  - enrich: raw_body 재활용 (이중 fetch 회피), `--reuse-threshold` 옵션
  - render: mermaid 트리 다이어그램, 도메인별 자료 섹션, score(citations·upvotes) 기반 정렬, 출처 인덱스에 도메인·score 컬럼
  - synthesize.py 신규: Ollama/Anthropic/Gemini로 보고서 LLM 합성 섹션 추가 (자동 fallback)
  - 검증: "large language model" 토픽으로 108 hits, 45 concepts, full 37/digest 71, 605라인 보고서, 560 chunks
- 2026-05-15 — **compose.py 신설 (map-reduce 입문서 합성)**:
  - render는 "자료 카탈로그"고 진짜 "보고서"가 아니라는 사용자 지적에 대응
  - batch별로 source 묶어 LLM에 요약 시키고 (map), 요약을 모아 통합 입문서 작성 (reduce)
  - claude_inline 모드: LLM 인프라 없을 때 prompt 파일들을 디스크에 dump → Claude Code 세션이나 사람이 응답을 채워 넣음 → `--collect` → 최종 합성 prompt → `--finalize` → `reports/<slug>_full.md`
  - 자동 fallback: ollama → anthropic → gemini → claude_inline
  - 검증: "피지컬 AI" 토픽 30 source(ontopic) → 5 batch × 6 source. 이 Claude Code 세션이 batch 5건 + 최종 합성을 직접 작성해 `reports/피지컬_ai_full.md` (5582 chars) 생성. 진짜 입문서(정의/범위/핵심 기술/주요 플레이어/연구·학술 동향/산업·시장·정책/비판·논쟁/학습 경로) 완성.
- 2026-05-15 — 학술 백엔드 복원 + 노이즈 필터링:
  - `local_fetchers/` 신설: arxiv·crossref·scholar(SerpAPI/scholarly)·dbpia(KCI Open API 우선) 4종
  - `academic` 도메인에 arxiv·crossref·scholar 합류, `academic_kr` 도메인 신설(dbpia)
  - aggregate에 토픽 관련성 필터(`_hit_relevant`) — fuzzy match로 들어온 무관 hit은 sources에 남기되 `offtopic=true`로 표시, concept 등록 제외
  - aggregate에 `--aliases` 옵션: 한·영 표기 동시 매칭(독립 token group)
  - 강화된 stopwords(한·영) + 1-token 최소 8자 + noise concept 정규식(연도, "List of...", "X in Y") 필터
  - render: 핵심 개념·트리 모두 support≥2 또는 자식 있는 것만 노출, "토픽 무관 자동 분류" 섹션으로 분리 표시
  - 검증: "피지컬 AI" + aliases로 34 hits, 7 concepts, full 4/digest 30/오프토픽 10, 153라인 보고서. 학술 16건(KCI 한국 논문 포함), 한국 피지컬 AI 기업·인물(LG CNS, 디에스엠, 로보티즈, 씨메스, 김병수) 자동 추출.
