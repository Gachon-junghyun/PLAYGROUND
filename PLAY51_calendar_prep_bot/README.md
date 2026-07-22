# PLAY51_calendar_prep_bot

## 목적
텔레그램 하나로 대화하는 개인 비서 봇. iCloud 캘린더 일정 1시간 전에 준비를 물어보고
(버튼: 같이/혼자 진행/사용자가 진행/대기), 평소엔 자연어로 말하면 **도구 플러그인**(웹검색·일정조회·기억 등)을
써서 처리한다. **"이거 기억해줘" 하면 저장해뒀다가 이후 일정 준비·대화에 자동으로 참고** — 그래서 일정에 단어
몇 개뿐이어도 기억+제목으로 추론해 '일단 진행'한다. "혼자 진행"을 누르면 그 일정 전용 **작업자(worker) 세션**으로
전환되고 `/up` 으로 빠져나온다. 두뇌는 무료 NVIDIA NIM LLM — 실행 엔진에 돈이 안 든다.

## 실행법
```powershell
# 1) 의존성
pip install caldav requests playwright openai
# (playwright 는 이미 떠있는 크롬에 CDP로만 붙는 용도 — `playwright install` 불필요)

# 2) 시크릿 파일 5종 (이 폴더 안, 전부 git 무시됨, 각 파일에 값 한 줄)
#    nvapi_key.local.txt            NVIDIA API 키 (PLAY50 것 재사용 가능)
#    tg_bot_token.local.txt         텔레그램 봇 토큰 (BotFather)
#    tg_chat_id.local.txt           메시지 받을 챗 ID
#    icloud_id.local.txt            Apple ID 이메일
#    icloud_app_password.local.txt  앱 전용 암호 (appleid.apple.com → 보안 → 앱 암호)

# 3) 검증 (무한루프 없이 짧게 끝남)
python bot.py --list-events            # CalDAV 연결 + 일정 확인
python bot.py --test-telegram "테스트"  # 텔레그램 연결 확인
python bot.py --check-once             # 캘린더 알림 로직 1회

# 4) 상시 가동 (이 터미널 계속 띄워둬야 함, Ctrl+C 종료)
python bot.py
```

### 텔레그램 명령어
- 그냥 말하면 → 현재 세션(오케스트레이터/작업자)이 처리 (필요하면 도구 사용)
- **"이거 기억해줘" / "~ 참고해둬"** → 핵심 사실을 뽑아 저장, 이후 자동 참고
- `/memories` — 기억 목록  ·  `/forget <번호>` — 기억 삭제
- `/who` — 지금 누구랑 대화 중인지 (🧭 오케스트레이터 / 🔧 작업자)
- `/tools` — 등록된 도구 목록  ·  `/reload` — 도구 새로고침(봇 재시작 없이)
- `/up` — 작업자 → 오케스트레이터 복귀  ·  `/help` — 사용법

### 도구(툴) 추가하는 법 — 이게 핵심 확장 포인트
`tools/_TEMPLATE.py` 를 `tools/<이름>.py` 로 복사하고 `META`(dict) + `run(**kwargs) -> str` 만 채우면 끝.
텔레그램에서 `/reload` 하면 봇 재시작 없이 바로 붙는다. 규격은 `tools/__init__.py` 참고.
```python
META = {"name": "이름", "description": "언제 쓰는지", "params": {"인자": "설명"}}
def run(인자: str) -> str:
    return "결과 문자열"
```
현재 등록된 도구: `web_search`(크롬 9222 CDP 검색), `list_events`(iCloud 일정 조회), `remember`(사실 저장), `recall`(기억 검색).

## 입력 / 출력
- **입력:** iCloud 캘린더 이벤트(제목·시작시각·메모), 텔레그램 버튼 클릭 / 자연어 메시지 / 명령어.
- **출력:** 텔레그램 메시지 — 일정 준비 제안+버튼, 도구 실행 알림(🔧), 세션별 응답(🧭/🔧), 명령어 응답.
  상태는 `state.local.db`(sqlite)에 저장(이벤트 처리상태 + 현재 세션 mode/task + 텔레그램 offset). 재시작해도 이어짐.

## 가정 & 제약
- **아키텍처:** 오케스트레이터 ⇄ 작업자 2모드 세션 라우터. 두 모드 다 같은 에이전트 루프(`run_agent`)를 쓰고,
  system 프롬프트와 대화기록(`HISTORIES`)만 다르다. 대화기록은 **메모리에만** 있어 봇 재시작 시 초기화됨(세션 mode/task 자체는 DB에 남음). 단일 사용자 전제.
- **지속 기억(비서의 핵심 덕목):** `memory` 테이블(sqlite, 재시작해도 유지)에 사실을 저장하고, **모든 에이전트 턴·일정 준비 제안의 system 프롬프트에 전체 기억(최근 60개, ~3000자)을 자동 주입**한다. 규모가 개인용이라 키워드 매칭 없이 통째로 넣고 LLM 이 관련성을 판단하는 방식. `ASSISTANT_PRINCIPLES`(기억 활용/추정 표시/간결/막힐 때만 질문)를 함께 주입해 비서답게 동작시킨다.
- **'기억해줘'는 결정론적으로 처리:** LLM 도구호출(`remember`)에 맡기면 "기억했다"고 말만 하고 실제 저장을 자주 빼먹어서, `maybe_remember` 가 키워드(기억해/참고해둬 등)를 먼저 잡아 LLM 으로 핵심 사실만 추출→저장한다(추출 실패 시 원문 저장). `remember` 도구는 에이전트가 작업 중 스스로 유용한 사실을 저장할 때 쓴다.
- **터스(빈약한) 일정도 '딱 진행':** 메모가 없어도 되묻지 않고, 기억+제목으로 준비안을 추론해 버튼과 함께 제시(추정한 부분은 '(추정)' 표시). 예전의 "메모 없으면 되묻기(awaiting_notes)" 플로우는 제거.
- **에이전트 루프는 ReAct-lite:** LLM 이 도구가 필요하면 `CALL <도구> {json}` 한 줄을 뱉고, 봇이 실행해 결과를 되먹인다(최대 `AGENT_MAX_STEPS`=4회). 도구 호출 파싱은 **관대하게**(`parse_tool_call`) — 모델이 JSON 규약을 자주 안 지켜서, `CALL web_search "문자열"` 이나 `CALL list_events 48` 같은 맨 값도 도구의 첫 인자에 매핑한다.
- **NVIDIA 무료티어 flakiness 대응(중요):** 무료티어는 (a) 가끔 빈 응답 (b) 과부하 시 타임아웃/500 이 잦다(실측: 평소 3~4s 이 congestion 때 12~30s, 간헐 500). 그래서 (1) `ask_llm_messages` 는 예외/빈응답을 잡아 2회 재시도하고, 끝내 실패하면 **예외를 던지지 않고** 사용자에게 "⚠ LLM 응답 지연/실패, 잠시 후 다시" 안내 (2) 도구 결과는 있는데 최종답이 비면 강제 요약 폴백 (3) `handle_update` 전체를 감싸 어떤 에러든 사용자에게 알린다. **어떤 실패도 조용한 침묵으로 끝나지 않는 게 핵심**(사용자 지적 반영). 타임아웃 상한 45s.
- **직관화(즉시 피드백):** 메시지 받는 즉시 (느린 LLM 호출 '전에') 구체적 접수 메시지("🧭 받았어요 — 처리 중… 🤔")를 먼저 쏘고 `typing…` 표시, 도구 실행 시 "🔧 도구 실행: …" 를 먼저 보내고, 응답 앞에 🧭/🔧 로 현재 화자를 표시. `/who` 로 상태 확인. 콘솔(run.log)에도 수신 메시지·도구 호출·에러를 전부 로깅.
- **"혼자 진행" = 작업자 세션 오픈.** 그 일정+메모로 시드된 worker 로 전환하고 초기 준비 1패스를 돌린 뒤, 이어서 대화 가능. **"같이"는 봇이 아무것도 안 함**(실제 협업은 사용자가 직접 세션 여는 것 — 사용자 원문 "내가 트리거 역할" 반영).
- **worker 의 두뇌는 현재 무료 NVIDIA LLM + 우리가 만든 도구뿐.** 진짜 Claude Code 에이전트로 위임하는 건 (실행마다 과금이라) 아직 안 붙였다 — 나중에 `tools/escalate_to_claude.py` 같은 도구로 추가하면 되고, **그게 과금 시작 지점이라 붙일 때 별도 확인 필요**.
- **캘린더 catch-up:** CalDAV 는 이미 끝난 이벤트를 안 돌려줘서, 조회를 `now - CATCHUP_LOOKBACK_HOURS`(24h)까지 뒤로 연다. 트리거 시점 지났지만 못 보낸 알림은 잡되, **이미 시작한 일정은 알림 없이 `expired` 처리**(2026-07-01 DACON 예선 누락 버그로 발견·수정).
- **CalDAV 파싱은 `ev.icalendar_component`**(caldav 3.x, vobject 미번들). 종일 일정은 자정 UTC 취급.
- **NVIDIA 모델 `qwen/qwen3.5-122b-a10b` 고정**(PLAY50 실측상 사고과정 없이 바로 답함). `bot.py` 의 `NVIDIA_MODEL` 로 교체 가능.
- **튜닝 상수**(리드타임 1h, 폴링 15m, 스누즈 20m, catch-up 24h, agent 4스텝, history 10개)는 전부 `bot.py` 상단.
- **긴 LLM 호출은 getUpdates 루프를 잠깐 블록**(도구 여러 번이면 수십 초). 단일 사용자라 문제 없다고 판단.
- **무한 루프 프로세스**라 터미널 계속 띄워둬야 하고 재부팅 시 자동 재시작 안 됨(원하면 Task Scheduler 등록, 이번 범위 밖).
- **더미 검증 불가**(실제 계정 대상). 이 세션에서 CalDAV 연결·텔레그램 송수신·도구 호출 에이전트 루프(list_events)·날짜추론은 실측 검증했고, 텔레그램 버튼 실시간 4분기와 web_search 라이브(크롬 9222)는 사용자 실기기 테스트가 남아있다.

## 변경 이력
- 2026-07-01 — 최초 생성. iCloud CalDAV + 텔레그램 인라인 버튼 + 크롬 9222 CDP 검색 + NVIDIA LLM 일정 준비 봇.
- 2026-07-01 — 실계정 검증: 텔레그램 봇 연결, CalDAV `vobject`→`icalendar_component` 교체, NVIDIA 키 PLAY50 재사용.
- 2026-07-01 — 버그픽스 2건: (1) `answerCallbackQuery` 실패가 버튼 로직 전체를 막던 것 → ack 실패 무시. (2) 과거 이벤트가 조회에서 영구 누락(DACON 예선) → catch-up lookback + `expired` 처리.
- 2026-07-01 — **아키텍처 확장:** 단순 알림봇 → 개인 오케스트레이터. `tools/` 도구 플러그인 프레임워크(META+run, 자동발견, `/reload` 핫리로드) + 오케스트레이터/작업자 세션 라우터(`/up`,`/who`,`/tools`) + ReAct-lite 에이전트 루프(도구 호출, 빈응답 재시도·폴백) + 즉시 피드백(typing·🔧·🧭) + 현재시각 주입. 도구 2종(web_search, list_events). worker 는 무료 NVIDIA LLM 기반, 진짜 Claude 위임은 과금이라 미연결(추후 도구로).
- 2026-07-01 — 사용자 지적("검색하라니까 5초간 무반응 = 피드백 없음") 후 견고화: (1) 입력 즉시 구체적 접수 메시지 전송(느린 LLM 전에). (2) NVIDIA 타임아웃/500/빈응답을 잡아 재시도하고 끝내 실패 시 사용자에게 안내(전엔 에러가 루프에 삼켜져 침묵). (3) 도구 호출 파싱을 관대하게(`parse_tool_call`) — 모델이 `CALL web_search "문자열"` 처럼 JSON 안 지켜도 인식(이 버그로 CALL 문장이 그대로 사용자에게 갔었음). (4) run.log 처리 로깅 추가. web_search→NVDA 실시세 요약까지 실측 검증 완료.
- 2026-07-02 — **비서 업그레이드(지속 기억):** `memory` 테이블 + 전체 기억 자동 주입 + `ASSISTANT_PRINCIPLES`. "기억해줘"를 결정론적으로 잡는 `maybe_remember`, 기억 도구 2종(`remember`/`recall`), `/memories`·`/forget` 명령. 터스 일정은 되묻지 않고 기억+제목으로 추론해 진행(awaiting_notes 제거). 실측 검증: "DACON…팀명 오이야 기억해줘" → 저장 → 메모 없는 'DACON 중간 점검' 일정 제안에 팀명·대회성격 반영 + '(추정)' 표시 확인.
