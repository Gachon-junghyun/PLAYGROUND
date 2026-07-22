# PLAY50_nvidia_model_arena

## 목적
build.nvidia.com(무료 NVIDIA NIM API)이 OpenAI 호환으로 열어둔 100+ LLM을 하네스로 삼는다. 두 갈래:
1. **`arena.py`** — 같은 프롬프트를 여러 모델(Llama·gpt-oss·Qwen·DeepSeek·Nemotron)에 병렬로 던져 답을 나란히 비교하는 CLI.
2. **뉴스 다이제스트 스케줄러 (`digest.py` + `scheduler.py`)** — 4시간마다 mvp의 `news_alert.db`에서 최근 뉴스를 랜덤 35% 샘플 → NVIDIA LLM이 중요 뉴스 선별 → 그 기사 본문 + `watchlist.db` + yfinance 텍스트차트를 재료로, **"무슨 일이 일어났고·배경은·왜 중요한가"를 풀어 설명하는 한국어 뉴스·시사 해설 브리핑**을 뽑는 서비스. 합성은 **가장 강한 모델(mistral-large-3 675B)** 로, 선별(스크리닝)은 빠른 모델로 역할을 나눈다.

---
## A. 뉴스 다이제스트 스케줄러

### 구성
| 파일 | 역할 |
|---|---|
| `nv_client.py` | NVIDIA 하네스 — 강한 모델 하나로 호출, 실패 시 모델 폴백(`arena.py`의 키/클라이언트 재사용) |
| `sources.py` | mvp `research_Mvp`의 DB·차트를 **read-only** 로 연결 (뉴스 샘플링/본문/워치리스트/텍스트차트) |
| `digest.py` | 파이프라인 1회 = 샘플→**무손실 청크 스크리닝**→본문→워치리스트+차트→LLM 합성(스트리밍)→리포트 저장 |
| `scheduler.py` | 4시간 주기로 `digest.run_once()` 반복 (백그라운드 로그 + sentinel) |
| `gui.py` | **Tkinter GUI** — 파이프라인이 돌아가는 로그 + 리포트가 실시간 스트리밍으로 써지는 걸 보는 창 |

### 실행법
**더블클릭 실행(.bat):** `run_gui.bat`(GUI 창) · `run_once.bat`(1회, 뒤에 `--dry-run`/`--frac 1.0` 등 붙여도 됨) · `run_scheduler.bat`(4시간 주기, Ctrl-C 종료). 셋 다 UTF-8 콘솔 + 폴더 자동이동.

```powershell
pip install openai yfinance pandas numpy   # arena 는 openai 만, 다이제스트는 차트용 추가
# GUI(gui.py)의 tkinter 는 파이썬 표준 라이브러리 — 별도 설치 없음

# (0) GUI — 돌아가는 로그 + 리포트 실시간 스트리밍을 창으로 본다 (또는 run_gui.bat 더블클릭)
python gui.py

# (1) 배관 검증 — LLM 미호출(크레딧 0), 키워드 스크리닝만. 재료를 reports/ 에 덤프
python -u digest.py --once --dry-run --chart-tickers 2

# (2) 1회 실제 실행 — 스크리닝(여러 청크)+합성 LLM 호출, reports/report_YYYYMMDD_HHMM.md 저장
python -u digest.py --once

#     진짜 무손실(35% 대신 전체 100%):
python -u digest.py --once --frac 1.0

# (3) 스케줄러 — 4시간마다 무한 반복 (Ctrl-C 종료)
python -u scheduler.py

#     백그라운드로 로그 남기며:
Start-Process -NoNewWindow python "-u scheduler.py" -RedirectStandardOutput run.log -RedirectStandardError run.err

#     검증용: 1시간 간격 2사이클만
python -u scheduler.py --interval-hours 1 --max-cycles 2 --dry-run
```

### 입력 / 출력
- **입력(읽기 전용):** `%MVP_DIR%\news_alert.db`(`seen_news` 제목/summary, `article_contents` 본문), `%MVP_DIR%\watchlist.db`(`watchlist` open/partial), yfinance(워치리스트 티커의 OHLCV → `module_text_chart`). 기본 `MVP_DIR = C:\Users\fivep\OneDrive\Desktop\mvp\research_Mvp`, 환경변수로 덮어쓰기.
- **주요 인자:** `--window-hours`(기본 4) `--frac`(0.35, `1.0`=전체) `--chunk-size`(200, 스크리닝 청크당 제목 수) `--important-k`(15, 본문 읽을 상위 수) `--chart-tickers`(6) `--seed` `--screen-model`/`--synth-model`(모델 고정) `--dry-run`.
- **출력:** `reports/report_YYYYMMDD_HHMM.md`(+ `reports/latest.md` 갱신), `state.json`(마지막 실행 시각). 리포트 구성(**해설 중심**): 한 줄 요약 / **오늘의 핵심 이슈**(이슈별 무슨 일→배경·맥락→왜 중요한가·파급) / 흐름과 맥락 / 내 관심사(워치리스트)와의 연결 / 차트 한눈에 / 지금 눈여겨볼 것.

### 가정 & 제약 (다이제스트)
- **정보 누락 제로(무손실 스크리닝).** 예전엔 35% 샘플을 `title-cap` 150으로 잘라 2,300여 건이 *LLM 눈에 닿기도 전에* 버려졌다. 지금은 샘플된 제목 **전부**를 `--chunk-size`(기본 100)씩 배치로 나눠 LLM 스크리닝에 통과시킨다(map-reduce). 사전 절단 없음. 최종적으로 빠지는 건 'LLM 이 보고 안 중요하다 판단한 것'뿐이고, '본 적 없이 잘린 것'은 없다. 진행 로그에 청크 n/N 과 누적 중요 건수를 찍는다.
- **"랜덤 35%"는 사용자 원설계의 표본 비율.** 4h 배치가 ~7,250건이라 기본 35%면 ~2,500건을 ~26청크로 스크리닝(LLM 호출 ~26회, 무료 40 RPM 안, 4h 간격이라 시간 무관). 완전 무손실을 원하면 `--frac 1.0`.
- **GUI(`gui.py`):** 왼쪽=진행 로그(돌아가는 거), 오른쪽=리포트 실시간 스트리밍(생각하는 거, 추론모델의 reasoning 은 회색). 파이프라인은 백그라운드 스레드, 이벤트는 Queue 로 넘어와 메인 스레드에서만 위젯 갱신(Tkinter 규칙). `■ 중단`은 청크/스테이지 경계에서 협조적으로 멈춘다(LLM 호출 1건 도중엔 못 끊음).
- **뉴스 윈도우 = "최근 N시간 안에 `fetched_at` 된 뉴스".** 수집 크론이 배치로 넣어서 한 배치가 통째로 들어온다. 스케줄러는 기본적으로 윈도우 = 실행 간격(4h)으로 맞춘다.
- **중요도 선별은 LLM이 한다.** 워치리스트 티커/키워드를 가중치로 주고 "가격 움직일 실질 정보"만 고르게 한다. LLM 랭킹이 실패하면 **워치리스트 용어가 제목에 등장하는지**로 폴백(휴리스틱). `--dry-run`은 항상 이 휴리스틱을 쓴다.
- **한국 종목코드(6자리)는 거래소를 몰라서** yfinance `.KS`(코스피)→`.KQ`(코스닥) 순으로 시도한다. 둘 다 데이터 없으면 그 종목 차트는 조용히 생략(파이프라인은 계속). US 티커는 그대로.
- **모델 = 역할 분리(스크리닝=빠름 / 합성=최고품질), 스트리밍 실측 기반(2026-07-09).** **reasoning 모델(deepseek·nemotron-super·gpt-oss)은 답 전에 오래 생각해 첫 토큰까지 13~44초 걸리고 조각도 뭉텅이라 "스트리밍이 안 되는 것처럼" 보인다.**
  - **스크리닝(제목 필터, 수 청크 반복 호출):** 빠른 non-reasoning 체인 — `ministral-14b`(TTFT 0.4s·토큰단위) → `nemotron-nano-9b` → `step-3.7-flash` → `qwen3-next-80b-a3b`(2026-07-22, 구 qwen3.5-122b-a10b 퇴역으로 교체, 실측 1.0s) → `deepseek`. `--screen-model` 로 고정 가능.
  - **합성(리포트 작성, 1회):** **가장 강한 모델 우선** `SYNTH_CHAIN` — `mistralai/mistral-large-3-675b-instruct-2512`(675B 플래그십, 실측 TTFT 0.4s·토큰단위·최상급 품질) → `deepseek-v4-pro`(강한 추론, 느림) → `ministral-14b`(최후 보루). `--synth-model` 로 고정 가능. (후보였던 qwen3.5-397b·nemotron-ultra-253b 는 timeout/404 라 제외.)
  - 실측(기본 35%, 953건): 전량 스크리닝 25s · 합성 TTFT ~4s · 3,400여 조각 매끄러운 토큰 스트림 · 전체 ~68s. ID stale 시 `python arena.py --list`.
- **지어낸 수치 방지(중요).** '해설' 초점이라 강한 모델이 배경을 풍부히 쓰다가 재료에 없는 구체 수치(환율·가격·인명)를 지어낼 수 있다. system 프롬프트로 **"구체 수치·날짜·인명은 재료에 있는 것만 인용, 없으면 정성적으로 쓰거나 생략, 확인 안 된 최신 사실은 '~로 알려져 있다'로 구분, 사실과 해석 분리"** 를 강제한다. 검증에서 이전 버전이 만들던 'Kevin Warsh/EUR-USD 1.14/WTI 74달러' 류가 제거됨을 확인. 그래도 배경 문단의 일반 상식성 서술은 재료 밖 지식일 수 있으니, **수치가 걸린 판단은 원문 기사로 재확인**할 것.
- **스크리닝 속도:** 청크당 200제목(`--chunk-size`)씩 ministral 로 통과 → 35%(~950건)면 ~5청크·25초. reasoning 모델로 청크를 돌리면 청크당 24초씩 걸려 수 분~10분이 되니(그래서 기본을 non-reasoning 으로) 바꾸지 말 것.
- **본문은 `article_contents`의 `ok`/`short` 상태만**, 앞 1,200자로 절단. `error`나 미수집 기사는 제목/summary만 쓴다.
- **mvp에 절대 쓰지 않는다.** 모든 DB 접근은 `mode=ro` URI(순수 조회). 리포트/상태는 이 PLAY 폴더 안에만 저장.
- **검증 완료(2026-07-09):** 합성=mistral-large-3(675B)로 기본 35%(953건) 전량 무손실 스크리닝 25s, 합성 TTFT ~4s, delta 3,400여 개(토큰단위 매끄러운 스트림), 전체 ~68s. 리포트는 이란-호르무즈·Fed 분열·AI반도체 상품화를 '무슨 일→배경→파급'으로 해설하고 한국 경제/워치리스트로 연결. 가드레일 후 지어낸 수치(Kevin Warsh/EUR-USD 1.14 등) 제거 확인. dry-run(크레딧 0) 무손실 확인, GUI 위젯 생성/렌더 OK, bat 실행 OK.
- **비용/속도:** 무료 티어 ~40 RPM 안. 한 사이클 = LLM 2회. 합성 모델이 느리면(deepseek 100s+) 사이클이 수 분 걸릴 수 있으나 4h 간격이라 무관. `--important-k`/`--chart-tickers`를 줄이면 토큰·시간 절약.
- **전달 채널은 로컬 마크다운 파일만.** 텔레그램(mvp `alert_bot`) 등 외부 발송은 '나가는 액션'이라 자동화하지 않음 — 원하면 별도 요청. `reports/latest.md`를 보면 최신 리포트.

---
## B. arena.py — 멀티모델 병렬 비교

같은 프롬프트를 여러 모델에 병렬로 던져 응답·지연시간·토큰 사용량을 한 화면에서 본다.

## 실행법
```powershell
# 1) 의존성 (openai SDK 하나면 끝 — build.nvidia.com 이 OpenAI 호환이라)
pip install openai

# 2) 무료 API 키 발급 (카드 불필요)
#    - https://build.nvidia.com 가입
#    - 아무 모델 페이지 열고 우측 'Get API Key' 클릭 → nvapi-... 키 복사
# 3) 키 넣기 — 둘 중 하나 (스크립트가 알아서 찾음: 환경변수 우선, 없으면 로컬 파일)
#    (A) 권장: 이 폴더에 nvapi_key.local.txt 만들고 키 한 줄 붙여넣기 (git 무시됨)
#    (B) 또는 환경변수:  setx NVIDIA_API_KEY "nvapi-xxxx"  (새 창부터 적용)

# 4) 실행
python arena.py "블랙홀을 5살한테 설명해줘"

# 지금 이 키로 쓸 수 있는 모델 전체 ID 보기 (ID 확인용)
python arena.py --list

# 모델 직접 지정
python arena.py "이 코드 리뷰해줘: ..." --models "meta/llama-3.3-70b-instruct,qwen/qwen3.5-122b-a10b"

# 추론(reasoning) 모델은 토큰을 넉넉히 줘야 최종답이 나옴
python arena.py "1+1은?" --max-tokens 400

# 크레딧 아끼려면 출력 토큰 제한
python arena.py "한 줄 요약해줘" --max-tokens 128
```

## 입력 / 출력
- **입력:**
  - 위치 인자 `prompt` (생략 시 기본 프롬프트) — 모든 모델에 던질 하나의 프롬프트
  - `--models` 쉼표구분 모델 ID 목록 (기본 5개 세트 덮어쓰기)
  - `--max-tokens` (기본 512), `--temperature` (기본 0.4), `--wrap` (출력 폭)
  - `--timeout` 모델당 응답 대기 상한 초 (기본 60) — 초과 시 그 모델만 실패 처리
  - `--list` 이 키로 호출 가능한 전체 모델 ID 출력하고 종료
  - 키: 환경변수 `NVIDIA_API_KEY` → 없으면 옆의 `nvapi_key.local.txt` 순으로 읽음. 둘 다 없으면 안내 후 종료.
- **출력:** 콘솔에 모델별 블록 — `[지연초 · 토큰수]` + 응답 본문. 마지막에 성공 N/M, 최속 모델 요약. 파일 출력 없음.

## 가정 & 제약
- **사용자 API 키가 반드시 필요.** 키는 코드에 안 박는다. 우선순위: 환경변수 `NVIDIA_API_KEY` → 같은 폴더의 `nvapi_key.local.txt`(루트 `.gitignore`에 등재돼 커밋 안 됨). 둘 다 없으면 발급 안내만 출력하고 종료(정상).
- **무료 티어 한도(2026-07-01 기준):** 가입 시 1,000 인퍼런스 크레딧(요청 시 최대 5,000), **~40 RPM(모든 모델 호출 합산 공유 한도)**. 카드·GPU 불필요. 대시보드에서 무료로 ~200 RPM 상향 신청 가능. 기본 5개 동시 호출은 40 RPM 안. 크레딧 소진/한도 초과 시 해당 모델만 `[실패]`, 나머지는 계속(전체가 안 죽음).
- **모델 세트는 2026-07-01 에 `/v1/models`(121개 반환)로 실재 확인하고, 기본 5개는 실제 호출까지 검증했다.** 결과: `openai/gpt-oss-120b`·`qwen/qwen3.5-122b-a10b`·`deepseek-ai/deepseek-v4-pro`·`nvidia/llama-3.3-nemotron-super-49b-v1.5` 응답 OK, `meta/llama-3.3-70b-instruct`는 ID는 유효하나 그 시점 서버 과부하로 504/timeout(간헐적, fast-fail 로 처리됨). **처음 작성했던 기본 세트(nemotron-70b·qwen2.5-72b·mixtral-8x22b·deepseek-r1)는 전부 404/410 EOL 로 죽어 있어 현행 ID 로 교체함.** ID 는 계속 바뀌니 stale 이면 `python arena.py --list` 로 확인 후 `--models` 로 넘겨라.
- **2026-07-22 재검증(`--list` 118개 반환):** `qwen/qwen3.5-122b-a10b` 가 그새 퇴역(목록에서 사라짐) 확인. 대체 후보 `qwen/qwen3.5-397b-a17b` 는 실제 호출해보니 30s+ 타임아웃(너무 무거움, SYNTH_CHAIN 후보 테스트 때와 동일 증상)이라 기각하고, 실측 1.0s 로 응답하는 `qwen/qwen3-next-80b-a3b-instruct` 로 최종 교체(`DEFAULT_MODELS`·`nv_client.DEFAULT_CHAIN` 둘 다). 나머지 4개는 이번에도 `/v1/models` 목록에 살아있음을 재확인(`meta/llama-3.3-70b-instruct` 는 이번 실측에서도 동일하게 간헐적 504/timeout — 신규 이슈 아님).
- **추론(reasoning) 모델 주의:** `openai/gpt-oss-120b`, `nvidia/...nemotron-super...` 등은 답을 `content` 가 아니라 `reasoning_content` 에 넣고, `--max-tokens` 가 작으면 사고만 하다 최종답 없이 잘린다. 스크립트는 `content` 가 비면 `reasoning_content` 를 대신 보여준다(그래도 비면 max-tokens 를 키워라).
- **fast-fail:** openai SDK 는 504 등에서 기본으로 몇 분씩 재시도한다(초기 검증 때 llama 하나가 908초 매달림). 그래서 `max_retries=0` + `--timeout`(기본 60s)으로 느린/죽은 모델이 전체를 붙잡지 못하게 했다.
- **인코딩:** Windows 콘솔(cp949)에서 유니코드 구분선이 죽던 문제 때문에 시작 시 `stdout` 을 UTF-8 로 reconfigure 하고, 구분선은 ASCII 로 바꿨다.
- **Chrome 캡처 없음:** 원래 계획은 Chrome MCP 로 build.nvidia.com UI 를 직접 캡처하는 것이었으나 이 세션에서 확장이 연결되지 않아(수 회 재시도 실패) `/v1/models` API + WebSearch 로 대체했다. 확인된 사실: base_url `https://integrate.api.nvidia.com/v1`, OpenAI 호환, 키 형식 `nvapi-`. (참고: 베이스 URL 을 브라우저로 GET 하면 404 가 뜨는 게 정상 — 실제 엔드포인트는 `POST /v1/chat/completions`.)
- 병렬 호출은 `ThreadPoolExecutor`(표준 라이브러리). 외부 의존성은 `openai` 하나뿐. Windows PowerShell 기준.
- 디스패치 45초 제약: `pip install openai` 만 필요, 무거운 다운로드 없음. 호출 시간은 모델 속도에 달렸으니(수 초~수십 초) 검증용은 `--max-tokens` 작게 + `--timeout` 짧게.

## 변경 이력
- 2026-07-22 — **Qwen 모델 ID 퇴역 대응 교체.** `python arena.py --list`(118개)로 재검증한 결과 `qwen/qwen3.5-122b-a10b`가 카탈로그에서 사라짐을 확인. 대체로 넣어본 `qwen/qwen3.5-397b-a17b`는 실호출 30s+ 타임아웃이라 기각, 실측 1.0s로 정상 응답한 `qwen/qwen3-next-80b-a3b-instruct`로 최종 교체(`arena.py DEFAULT_MODELS`, `nv_client.py DEFAULT_CHAIN` 둘 다). 나머지 4개 모델 ID(`gpt-oss-120b`·`deepseek-v4-pro`·`llama-3.3-70b-instruct`·`llama-3.3-nemotron-super-49b-v1.5`)는 여전히 생존 확인. `arena.py "1+1?" --max-tokens 64 --timeout 30`으로 5개 전체 스모크 테스트 통과(4/5 성공, `llama-3.3-70b-instruct`만 기존에 문서화된 간헐적 서버 과부하로 타임아웃 — 신규 문제 아님).
- 2026-07-09 — **최고 품질 모델 + 뉴스·시사 해설 초점 업그레이드**. 합성 전용 `SYNTH_CHAIN`(mistral-large-3 675B 우선, deepseek·ministral 폴백) 분리 — 스크리닝은 빠른 모델, 합성은 최강 모델. 최상급 5개 모델 실측 후 mistral-large-3 선정(TTFT 0.4s·토큰단위, qwen-397b·nemotron-ultra 는 timeout/404). 리포트를 트레이딩 데스크형에서 **해설형(오늘의 핵심 이슈: 무슨 일→배경→왜 중요/오늘의 흐름/관심사 연결)** 으로 재작성, 스크리닝도 '가격 변동'에서 '시사적 중요도'로 확대. 지어낸 수치 방지 가드레일 추가(구체 수치는 재료에 있는 것만). max_tokens 3500.
- 2026-07-09 — **스트리밍 안 되던 문제 수정(모델 교체)**. 원인: 기본 합성 모델 deepseek-v4-pro 가 reasoning 모델이라 첫 토큰까지 13~44초 침묵 + 뭉텅이 출력이라 스트리밍이 안 보였고, reasoning 모델로 청크 스크리닝 시 청크당 24초로 35%가 ~10분 걸림. 5개 모델 스트리밍 실측 후 기본 체인을 non-reasoning 우선(`ministral-14b` head)으로 교체 → 스크리닝 25s·합성 TTFT 3s·1,961조각 매끄러운 토큰 스트림·전체 58s. `--chunk-size` 기본 200, `--screen-model`/`--synth-model` 오버라이드 추가. GUI 에 '첫 토큰 대기' 표시.
- 2026-07-09 — **무손실 스크리닝 + Tkinter GUI**. `title-cap` 사전절단(정보 유실)을 제거하고, 샘플 전체를 청크로 나눠 전량 LLM 스크리닝(map-reduce, `--chunk-size`). 합성을 스트리밍으로 바꿔 `gui.py`(진행 로그 + 리포트 실시간 스트리밍, 추론=회색, Stop=협조적 중단) 추가. nv_client 에 스트리밍/on_delta, digest 에 on_event 콜백·should_stop 추가. `--frac 1.0`=완전 무손실.
- 2026-07-09 — **뉴스 다이제스트 스케줄러 추가**(`nv_client.py`·`sources.py`·`digest.py`·`scheduler.py`). NVIDIA LLM을 하네스로, mvp `news_alert.db`(랜덤 35% 샘플→중요 본문)+`watchlist.db`+yfinance 텍스트차트를 4시간마다 종합해 한국어 데스크 브리핑 마크다운 생성. DB는 전부 read-only, 리포트는 `reports/`. dry-run·라이브 1회 검증 통과.
- 2026-07-01 — 최초 생성. NVIDIA NIM 무료 API 멀티모델 병렬 비교 CLI(`arena.py`). Chrome 미연결로 UI 캡처는 생략.
- 2026-07-01 — 실제 키로 검증하며 대폭 수정: (1) 기본 모델 5개가 전부 stale(404/410) 이라 `/v1/models` 로 확인한 현행 ID 로 교체, (2) 추론 모델용 `reasoning_content` 처리 추가, (3) `max_retries=0`+`--timeout` fast-fail(908초 매달림 버그 수정), (4) cp949 유니코드 크래시 수정(UTF-8 reconfigure + ASCII 구분선), (5) `--list` 추가, (6) 키를 `nvapi_key.local.txt`(gitignore)에서도 읽게 함.
