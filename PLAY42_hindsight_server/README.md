# PLAY42_hindsight_server

## 목적
macOS 화면 라이프로그(Hindsight)의 **서버** — 맥이 보낸 화면 텍스트를 받아 쌓고, **규칙 기반(LLM 0토큰)** 으로 **앱/주제/시간 분리 + '과거 동일내용 링크'** 를 붙여 돌려준다. 요약·질문 같은 '생각'은 점심·저녁에 접근하는 Claude 루틴이 한다.

> **아키텍처:** FastAPI + SQLite **뿐**. torch·임베딩·Qdrant·Ollama·Docker **전부 없음.** 24h 무인 가동에 가볍고 안정적.
>
> **저장 모델 = content interning + segment.** 같은 텍스트는 `contents` 에 딱 한 번 저장(중복 제거), 등장은 `segments`(언제·얼마나 봤나)로만 가리킨다. 화면에 계속 떠 있어 반복 잡히는 '지속'은 한 세그먼트에 `count` 로 접히고(라이브 데이터 기준 텍스트 **82% 절감**), 갭(기본 3분)을 넘긴 '재방문'은 새 세그먼트가 된다. `count`×캡처간격 ≈ 그 내용을 본 시간(dwell).

---

## 실행법

### 1) 의존성 (가벼움 — 디스패치 가능 수준)
```powershell
cd PLAY42_hindsight_server
pip install -r requirements.txt   # fastapi, uvicorn, requests
```

### 2) 토큰 설정 (필수, 맥과 동일 값)
```powershell
$env:HINDSIGHT_TOKEN = "여기에-긴-무작위-토큰"
```

### 3) 서버 기동
```powershell
.\run.ps1
# 또는: python -m uvicorn server:app --host 0.0.0.0 --port 8000
```

### 4) 동작 확인
```powershell
python send_dummy.py        # 더미 5건 업로드 + 멱등 + breakdown/search/history 출력
```

### 5) 맥에서 연결 (이 서버의 Tailscale IP = `100.118.139.82`)
```bash
# 맥 터미널에서 헬스 확인
curl -H "Authorization: Bearer <토큰>" http://100.118.139.82:8000/health
```
- 맥 클라이언트의 서버 주소를 `http://100.118.139.82:8000`, 토큰을 위와 **같은 값**으로 설정.
- 처음 안 붙으면 **Windows 방화벽**에서 8000 인바운드 1회 허용:
  ```powershell
  New-NetFirewallRule -DisplayName "Hindsight 8000" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow
  ```

---

## 입력 / 출력

모든 엔드포인트 `Authorization: Bearer <HINDSIGHT_TOKEN>` 필요. 응답은 UTF-8 JSON.

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/captures` | 배치 수신·**멱등** 저장 (맥 클라이언트가 쓰는 유일한 엔드포인트) |
| GET | `/timeline?date=&from=&to=&app=&topic=&limit=` | 윈도우 **세그먼트**를 시간순 + 앱/주제/시간/재방문/dwell 태그. 루틴 주력 |
| GET | `/breakdown?date=&from=&to=` | 윈도우 집계: 앱별·주제별·시간대별 + 재방문 비율 (+접기 전후 규모) |
| GET | `/search?q=&app=&topic=&from=&to=&limit=` | 키워드(LIKE) 검색 + 필터 + 등장 정보 |
| GET | `/history?q=&limit=` | 그 내용이 과거 언제·얼마나 보였는지(그래프 노드 이력) |
| POST | `/reload-rules` | rules.json 무중단 재적용 |
| GET | `/health` | 카운트(중복 제거 전후)·기간·버킷/주제 목록 |

- **윈도우 인자:** `date=YYYY-MM-DD`(로컬 하루) 우선 → 없으면 `from`/`to`(epoch 초, `[from,to)`) → 둘 다 없으면 **오늘(로컬)**.
- **세그먼트 태그(timeline/search 결과):** `first`/`last`(로컬), `duration_sec`, `count`(관측수=dwell), `period`, `app`(원본 front_app), `bucket`(앱 버킷), `topic`, `recall:{first_seen, times_seen, total_count, revisit}`. (한 세그먼트 = 한 내용이 갭 없이 떠 있던 구간)
- **분류 규칙:** `rules.json` 에서 편집. 앱 버킷은 `front_app` 또는 텍스트 단서(Gmail처럼 브라우저 안 앱)로. 주제는 **세그먼트 단위 점수**로 — 활성앱 prior + 텍스트 키워드 출현수의 argmax(아래 "분류 방식" 참고). **LLM 안 씀.**

### 응답 예시 (요약)
```jsonc
// GET /health  — 중복 제거 효과가 바로 보임
{"status":"ok","captures":424,"contents":3747,"segments":4681,
 "observations":20781,"text_dedup_ratio":0.82, ...}

// GET /breakdown
{"segments":120,"observations":3100,           // 등장 수 / 접기 전 관측 수
 "by_app":{"Claude":70,"Word":30,"KakaoTalk":20},
 "by_topic":{"바이브코딩":70,"학교공부":30,"수산나":15,"기타":5},
 "by_period":{"저녁":120},"revisit_segments":12,"revisit_ratio":0.1}

// GET /history?q=수산나  — 같은 content 의 세그먼트 = 등장 이력
{"nodes":[{"text":"수산나디자인 작업방 4","times_seen":3,"total_count":14,
  "first_seen":"2026-06-09 16:51","last_seen":"2026-06-09 18:12",
  "occurrences":[{"first":"...","last":"16:58","count":8,"period":"오후","app":"KakaoTalk"}, ...]}]}
```

### 환경변수
| 이름 | 기본값 | 비고 |
|------|--------|------|
| `HINDSIGHT_TOKEN` | (없음, **필수**) | 미설정 시 모든 엔드포인트 503 |
| `HINDSIGHT_DB` | `hindsight.db` | SQLite 경로 |
| `HINDSIGHT_RULES` | `rules.json` | 분류 규칙 파일 |
| `HINDSIGHT_TZ_OFFSET_HOURS` | `9` | 로컬 하루·시간대 기준(KST) |
| `HINDSIGHT_HOST` / `HINDSIGHT_PORT` | `0.0.0.0` / `8000` | |

`SEGMENT_GAP_SEC`(기본 180) 등 저장/상한 상수는 `config.py` 에 있다 — 같은 내용이 이 갭 안에 또 잡히면 '지속'으로 합치고, 넘기면 '재방문'으로 새 세그먼트.

---

## 가정 & 제약

- **검증:** 전 엔드포인트를 in-process TestClient 로 검증 완료 — 멱등 저장, **세그먼트 접기(지속 5회→세그먼트 1·count 5)**, **재방문 분리(갭 초과→새 세그먼트)**, 앱/주제 분리, 시간/dwell 태그, `/history` 등장 이력, reload-rules 통과. **라이브 데이터(관측 20,781)로 마이그레이션 검증** → contents 3,747 + segments 4,681, text_dedup_ratio 0.82.
- **저장 = content interning + segment (핵심):** 텍스트는 `contents`(norm UNIQUE)에 한 번만. 등장은 `segments(content_id, app, first_ts, last_ts, count)`. 같은 (내용,앱)이 `SEGMENT_GAP_SEC`(기본 180초) 안에 또 오면 새 행 없이 그 세그먼트 `count`+1·`last_ts` 갱신('지속'); 갭 넘으면 새 세그먼트('재방문'). → 저장량 폭락 + `count`(=dwell) 신호 획득.
  - **무엇을 잃나(의도):** 프레임 단위 raw(매 캡처의 개별 행)는 보관하지 않는다 — 지속은 `count`로 요약된다. 정확한 per-frame 타임스탬프가 필요하면 그건 맥 클라 쪽에서 원본을 따로 보관해야 함. 라이프로그 다이제스트 목적엔 세그먼트로 충분.
- **LLM 미사용(의도):** 분류·연결은 전부 규칙/문자열 매칭이라 토큰 0. 요약/판단이 필요하면 Claude 루틴이 `/timeline`·`/breakdown`(이미 중복 제거·분리된) 결과 위에서만 하면 된다.
- **'내용 거의 같음' 링크 방식:** 임베딩 없이 **정규화 텍스트(`norm` = 소문자화 + 영숫자/한글만 남기고 기호 제거 + 공백 접기)** 가 곧 interning 키다. 기호 제거 덕에 "작업방 4"와 "작업방 4|" 는 같은 content. 카톡 재열람처럼 **글자가 그대로 다시 잡히는 경우**를 노린 설계 — 정확히/거의 같은 건 묶이지만 **표현만 다르고 의미가 같은** 건 못 잡는다(임베딩 영역, 의도적으로 뺌). 너무 짧은 줄(<6자)은 `tagging.MIN_LINK_LEN` 으로 `/history` 노드에서만 제외(저장은 됨).
  - `recall.revisit` = 등장 이벤트가 2회 이상(`times_seen>1`) 또는 윈도우 이전부터 있던 내용. `/breakdown` 의 `revisit_segments` = 윈도우 **이전**부터 있던(=옛날 것 다시 봄) 세그먼트만 — 둘은 정의가 다름(의도).
- **마이그레이션:** `db.py` 의 `SCHEMA_VERSION`(현재 3). 구 `lines` 모델 DB는 기동 시 1회 자동 변환(`PRAGMA user_version`). 과거 데이터는 (내용,앱)별로 한 세그먼트로 **합쳐서** 옮기므로 과거의 갭 분할(재방문 횟수)은 근사이고 **신규 데이터부터 정확**. `normalize()`/`SCHEMA_VERSION` 을 올리면 다음 기동에 재적용.
- **키워드 검색:** FTS5 대신 **LIKE 부분일치**(공백 split → AND) on `contents.text`. interning 덕에 검색 대상이 고유 내용(수천)뿐이라 빠름. 관련도 랭킹 없고 최신 등장순.
- **분류 방식 (세그먼트 단위 점수):** 주제는 세그먼트(=한 내용)마다 `(app, text)` 로 정한다. 점수 = `min(키워드 출현수, KW_CAP=20)` + 활성앱이 그 주제의 앱이면 `APP_PRIOR=8`. argmax, 전부 0이면 `기타`. 설계 의도:
  - **활성 앱이 가장 강한 신호** — Word=학교공부, Claude=바이브코딩 prior. 앱 prior 가 높아서(8) 사실상 앱이 주제를 정하고, 한 내용의 키워드가 압도적일 때만 뒤집힌다(예전 '화면 단위 상속'과 같은 효과를 더 단순하게 달성).
  - **교차앱 가드(`CROSS_APP_MIN=4`)** — 특정 앱에 매인 주제(학교공부→Word)는 *다른* 앱 화면을 약한 키워드(<4개)로 가로채지 못한다. 카톡에 "정답" 한 번 떴다고 학교공부로 새지 않게.
  - **이름 기반 주제(수산나)** 는 앱에 안 매여서 어느 앱에서든 이름이 나오면 발화.
  - 이 값들(`APP_PRIOR`/`KW_CAP`/`CROSS_APP_MIN`)은 `tagging.py` 상단, 키워드는 `rules.json`. 둘 다 휴리스틱이라 오분류 가능 → 다듬고 `/reload-rules`(키워드) 또는 재시작(상수).
  - **알려진 한계:** 한 앱을 여러 목적으로 쓰면(예: Claude로 코딩 vs Claude로 통계 공부) 화면 내용으로만 구분 → 화면에 두 주제 텍스트가 섞이면 우세한 쪽으로 쏠림. Gmail은 브라우저 안이라 텍스트 단서(`받은편지함` 등)가 화면에 없으면 `기타`로 빠질 수 있음.
- **시간/타임존:** 저장 `ts` 는 UTC epoch. `date`·`period`·표시 시각은 `HINDSIGHT_TZ_OFFSET_HOURS`(기본 KST +9)로 로컬 변환. 서버가 다른 타임존이면 이 값 조정.
- **멱등성:** `captures.client_capture_id` UNIQUE + `INSERT OR IGNORE`. 단 `client_capture_id` 가 `null` 이면 SQLite NULL distinct 라 매번 새로 저장(클라가 항상 id 를 보낸다는 계약 가정).
- **API 변경 범위:** 맥 클라이언트는 `/captures` 만 쓰므로 그 입력 시그니처는 그대로. `/captures` 응답은 `{received, stored, stored_lines(처리한 OCR 줄수), new_segments, duplicates_skipped}` — 클라가 2xx 만 보면 무관. 나머지(`/search`·`/timeline`·`/breakdown`·`/history`)는 줄→**세그먼트** 모델로 재설계됨(`segments` 키, `count`/`duration_sec` 추가).
- **반복(24h 가동) 대응:** 서버는 위 interning+세그먼트로 중복을 흡수하지만, **가장 큰 절감은 맥 클라가 직전 캡처 대비 '바뀐 줄만' 업로드(line-diff)** 하는 것 — 원천에서 90%를 막는다. 서버는 그 위 안전망. (맥 클라 코드는 이 PLAY 밖)
- **상한:** `/timeline`·`/breakdown` 세그먼트 5000/10만, 텍스트 40k자, `/history` content 30개·발생 200개 캡. 넘으면 `truncated`/캡 표시. `config.py` 에서 조정.
- **OS:** Windows + PowerShell(`run.ps1`). 콘솔에서 한글이 깨져 보여도 저장/응답은 UTF-8 정상(cp949 출력 문제일 뿐).

---

## 변경 이력
- 2026-06-09 — 최초 생성. (초안) FastAPI + BGE-M3 임베딩 + Qdrant + Ollama RAG 서버.
- 2026-06-09 — **방향 전환:** 로컬 LLM/임베딩/Qdrant/Docker 전부 제거. FastAPI+SQLite 데이터화 서버로 재작성 — 규칙 기반 앱(KakaoTalk/Gmail/Claude/Word)·주제(수산나/바이브코딩/학교공부) 분리, 로컬 시간/시간대 태그, 정규화-텍스트 기반 과거 동일내용 링크. 요약/질의응답은 Claude 루틴이 담당.
- 2026-06-09 — **분류 정확도 개선:** 주제 분류를 화면 단위 점수로(앱 prior 8 + 교차앱 가드 4), `normalize()` 기호 제거로 사소한 OCR 차이 병합.
- 2026-06-09 — **저장 모델 재작성(content interning + segment):** 같은 텍스트는 `contents` 에 1번만, 등장은 `segments(count/first_ts/last_ts)` 로. '지속'은 한 세그먼트로 접고 '재방문'(갭 초과)은 새 세그먼트. 24h 가동 시 폭증하던 중복 저장 해소(라이브 데이터 텍스트 **82% 절감** 실측) + `count`=dwell 신호 획득. `SCHEMA_VERSION=3` 기동 마이그레이션으로 구 `lines` → contents+segments 자동 변환. 전 엔드포인트(줄→세그먼트) 재작성 및 TestClient/라이브복사본 검증 완료. **적용하려면 서버 재시작 필요.**
- 2026-06-09 — **분류 정확도 개선(라이브 9,920줄로 검증):** 주제 분류를 줄 단위→**화면(capture) 단위 점수**로 전환(앱 prior 8 + 키워드, 교차앱 가드 4). 줄 단위일 때 일반 문장이 전부 `기타`(2,607)로 빠지던 문제 해소 → `기타` 거의 0. `normalize()` 에 기호 제거 추가로 사소한 OCR 차이 병합("작업방 4"≡"작업방 4|", x8+x6→x14). `NORM_VERSION` 마이그레이션(`PRAGMA user_version`)으로 기존 데이터 소급 재인덱싱. 통계 키워드 `function` 오매칭 등 키워드 정리. **적용하려면 서버 재시작 필요**(태깅은 조회 시점, norm 은 기동 시 재계산).
