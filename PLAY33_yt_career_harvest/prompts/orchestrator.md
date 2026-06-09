# PLAY33 오케스트레이터 — Claude Code가 직접 읽고 전체를 지휘하는 prompt

> 이 파일은 **메인 컨텍스트의 Claude Code**가 읽는다.
> 목적: 키워드 하나로 [채널 발견 → 다운로드 → Whisper 전사 → subagent 정리 → 리포트]를 끝까지 자동 운전.
> 작업 디렉토리는 항상 `PLAY33_yt_career_harvest/` 기준.

---

## 0. 전제 / 환경

- Windows + PowerShell. 의존성(`yt-dlp`, `faster-whisper`, `ffmpeg`)은 **미리 설치돼 있다고 가정** (README 실행법 참조). 설치를 코드 실행 경로에 넣지 마라.
- LLM 호출은 **로컬 ollama만** 쓴다 (외부 API 금지 — 사용자 메모리 룰). 단, 이 PLAY의 "정리/팁/사고방식/리포트"는 **너(Claude) 자신과 subagent가 직접** 수행하므로 별도 LLM 호출이 없다.
- Whisper(03단계)는 무겁다. 디스패치(Bash 45초)에서는 `_REFERENCE/long_running.md` 패턴으로 background 실행.

---

## 1. 파이프라인 전체 흐름

```
키워드
  │  python scripts/01_discover.py "키워드" --min-subs 120000
  ▼
data/channels.jsonl   {channel_id, name, url, subscribers}
  │  python scripts/02_fetch.py --from-channels data/channels.jsonl -n 8
  ▼
data/queue.jsonl      {video_id, title, url, channel}   (이미 본 영상은 seen.json으로 제외)
  │  python -u scripts/03_pipeline.py > data/run.log 2>&1   (background)
  ▼
data/transcripts/<video_id>.txt  +  data/manifest.jsonl
  │  ← 여기서부터 너(Claude)가 subagent를 띄워 처리
  ▼
data/cards/<batch>.jsonl   (팁 + 사고방식 카드)
  │  너가 종합
  ▼
data/reports/career_report.md   (최종 산출물)
```

---

## 2. 단계별 실행 지침

### Step 1 — 채널 발견
```powershell
python scripts/01_discover.py "<사용자 키워드>" --min-subs 120000 --search 50
```
결과 `data/channels.jsonl` 를 Read 해서 채널 목록을 사용자에게 한 번 보여줘라. 키워드가 넓어 뉴스 채널만 잡히면 키워드를 좁혀 재실행 제안.

### Step 2 — 신규 영상 큐
```powershell
python scripts/02_fetch.py --from-channels data/channels.jsonl -n 8
```
`data/queue.jsonl` 의 줄 수 = 이번에 전사할 영상 수. seen.json 덕에 **두 번째 실행부터는 신규만** 잡힌다. 0개면 "새 영상 없음"이라 보고하고 멈춰라.

### Step 3 — 다운로드 + 전사 (background)
큐가 크면(>3) 반드시 background:
```powershell
python -u scripts/03_pipeline.py > data/run.log 2>&1
```
Bash 툴 `run_in_background: true` 로 띄우고, 별도 background Bash로
`until grep -qE "^(DONE|FAILED)" data/run.log; do sleep 5; done` 폴링.
끝나면 `data/run.log` 와 `data/manifest.jsonl` 을 Read 로 확인.
단건 빠른 검증은 `--url "..."`.

### Step 4 — subagent로 정리 / 팁 / 사고방식 추출
1. `data/manifest.jsonl` 을 Read → 전사된 영상 목록 확보.
2. 영상을 **채널별 또는 4~6개 묶음**으로 batch 분할 (한 subagent 컨텍스트가 감당할 양).
3. 각 batch마다 **Agent 툴로 subagent를 병렬 호출**. 각 subagent에는:
   - `prompts/subagent_distill.md` 의 내용을 그대로 전달 (격리 컨텍스트라 이 파일을 못 보므로 본문을 프롬프트에 넣어라).
   - 처리할 `txt_path` 목록과 출력 경로 `data/cards/<batch_id>.jsonl`, 카드 ID 시작값(겹치지 않게 batch마다 영역 예약: B1=T001~, B2=T101~ …)을 인자로 줘라.
4. subagent들이 각자 `data/cards/<batch_id>.jsonl` 에 카드를 쓰고 300단어 이내로 보고.

### Step 5 — 최종 리포트
모든 `data/cards/*.jsonl` 을 Read 해서 너가 직접 종합 → `data/reports/career_report.md` 작성:
- **주제별 팁 종합** (이력서 / 코딩테스트 / 면접 / 포트폴리오 / 직무이해 / 대기업 vs 스타트업 …)
- **사고방식 종합** — 여러 화자가 공유하는 취업/커리어 사고 패턴 (예: "스펙이 아니라 문제정의 능력을 본다")
- **채널별 특징 한 줄**
- **출처** — 각 주장 옆에 `(video_id, 채널)` 표기
리포트 작성 후 README "변경 이력"에 오늘 날짜 + 한 줄 append.

---

## 3. 카드 스키마 (subagent 산출물, 참조용)

```jsonc
{
  "card_id": "T001",
  "source_video": {"video_id": "xxxx", "channel": "노마드 코더", "title_hint": "..."},
  "topic": "이력서 | 코딩테스트 | 면접 | 포트폴리오 | 직무이해 | 커리어전략 | 회사문화",
  "tips": ["실행 가능한 구체 팁 1~5개 (추상론 금지)"],
  "thinking_pattern": "화자가 취업/커리어를 바라보는 사고방식 한 줄",
  "evidence_quote": "자막에서 직접 인용 1~2줄",
  "applies_to": ["신입","경력","대기업","스타트업"],
  "confidence": "high|medium|low — 사유 (화자 수·근거)"
}
```

---

## 4. 하지 마라
- 무거운 의존성 설치를 코드 실행 경로에 넣기 (README 사전설치로 분리).
- 03단계를 foreground로 큰 큐에 돌리기 (45초 잘림).
- 자막에 없는 팁/사고방식 창작. evidence_quote 없는 카드 금지.
- 리포트만 쓰고 README "변경 이력" 갱신 안 하기.
- 다른 PLAY 디렉토리 건드리기.
