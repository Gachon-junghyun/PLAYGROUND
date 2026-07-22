# PLAY43 오케스트레이터 — Claude Code가 5단계를 끝까지 운전

이 문서를 Claude Code에게 주면 수집→카드화→스트레스→머지를 한 번에 운전한다.
메인(Claude)이 직접 하는 단계와 Agent/Workflow 위임 단계가 섞여 있다.

## Step 1 — INGEST (메인이 직접 Bash)
```powershell
# 국내 (신규 분류 먼저 보고, 그 다음 실제 수집)
python scripts\01_ingest.py --source naver --list-only
python scripts\01_ingest.py --source naver --pages 1 --limit 1
# 외국 (db 적재 SA 분석글)
python scripts\01_ingest.py --source seekingalpha --limit 1
```
산출 `data/inbox/<report_id>.txt`. 신규 0건이면 증분이 정상 — "최신 없음" 보고 후 다음 주기.

## Step 2 — CARDIFY (Agent 위임, 1 리포트 = 1 subagent)
입력: `data/inbox/<id>.txt` + `PLAY31/prompts/broker_reverse_distill.md` 본문 + v4 함수 인덱스.

각 inbox 리포트마다 subagent 1개:
1. `broker_reverse_distill.md` 규칙대로 리포트를 명제 단위로 뜯어 **B카드(28필드)** + **F함수 후보(16필드)** 추출.
2. 각 F후보를 v4 `functions[]`(F01~F87)와 매칭 판정: `abstract_form`+`trigger_when`이 60%+ 겹치면
   **매칭**(기존 함수 `source_cards`에 이 카드 추가, `source_card_count`+1) / 아니면 **신규 후보**(임시 ID `C-<id>-NN`).
3. 산출: `data/cards/<id>.cards.jsonl` + `data/cards/<id>.functions.jsonl`.
   신규 후보에는 `is_new: true`, 매칭분에는 `matched_to: "F<NN>"`.

> v4 함수 인덱스(id·name·abstract_form·trigger_when)는 메인이 v4 json에서 뽑아 subagent 프롬프트에 동봉.
> 카드 ID는 리포트별로 영역 분리(예: naver=`Bn-*`, SA=`Bs-*`)해 충돌 방지.

## Step 3 — STRESS TEST (Workflow)
메인이 `data/cards/*.functions.jsonl`에서 **`is_new: true` 후보만** 모아 args로 주입:
```
Workflow({
  scriptPath: "<PLAY43>/stress_test.workflow.js",
  args: { candidates: [<신규 후보들>], db_path: "<mvp/research_Mvp/news_alert.db 절대경로>" }
})
```
워크플로우가 적용(수행)→skeptic 적대검증 → `survived` / `held_single_card` / `redesign` 반환.
메인이 반환값을 파일로 떨군다:
- `survived[]` → `data/stress/survived.jsonl`
- `redesign[]` → `data/function_redesign_queue.jsonl` (append)
- 전체 `results[]` → `data/stress/stress_report.json`

## Step 4 — MERGE (메인이 직접)
```powershell
python scripts\04_merge_v4.py          # survived.jsonl → r5_v5_working.json (F88+)
python scripts\04_merge_v4.py --status # 추가분 확인
```
원본 v4 json은 절대 안 건드림. 단일 카드 후보가 전부면 "0 머지(2번째 카드 대기)"가 정상.

## Step 5 — 회고 (메인)
- 이번 주기 수집/카드/생존/보류/cut 수 1줄 요약.
- `function_redesign_queue.jsonl` 누적분 점검 — 분기 1회 R5 v5 정식 빌드 트리거.
- 다음 주기 시드: 못 채운 도메인/종목 (PLAY32 실행 프로토콜 Step F).

## 효율화 룰 (PLAY32 실행 프로토콜 §7 계승)
- news_alert.db sweep은 키워드별 1회, 결과 재활용.
- 워치리스트·키워드 alert 누적은 mvp 운영(텔레그램 봇)으로 위임.
- 카드 ID 영역 사전 분리로 병렬 subagent 충돌 0.
