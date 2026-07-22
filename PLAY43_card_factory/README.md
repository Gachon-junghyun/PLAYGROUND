# PLAY43_card_factory

## 목적
최신 **인사이트 리포트**(국내 증권사·외국 애널리스트·IB·애널리스트 유튜브)를 계속 가져와
→ 사고 카드/함수로 증류 → **스트레스 테스트**로 검증 → 통과분만 R5 v4 라이브러리에 진화시키는
반복 루프. 흩어진 부품(PLAY30/31/32/33 + PLAY23·manhood)을 하나로 묶는 **오케스트레이션 레이어**.

핵심 원칙: **사건(event)이 아니라 인사이트(insight)** 를 모은다. 일반 뉴스·1차 공시(SEC)는
카드 소스가 아니라 데이터 anchor로만. 분석가의 *사고 경로*가 담긴 것만 카드화 (PLAY31 본질 계승).

원본 불변: PLAY30/31/32/33·mvp는 절대경로로 **호출만**. v4 라이브러리도 `data/r5_v5_working.json`
작업사본에만 머지 — 사용자가 받아본 뒤 교체 결정.

## 5단계 파이프라인 (orchestrator.md가 운전)

```
1. INGEST   python scripts/01_ingest.py --source <naver|seekingalpha|inbox|youtube_*>
            → data/inbox/<report_id>.txt (신규만, seen_reports.json 증분)
2. CARDIFY  Agent 위임 (PLAY31 broker_reverse_distill.md) → data/cards/<id>.cards.jsonl + .functions.jsonl
            신규 F후보를 v4 functions[]와 매칭(60%+ 겹침=매칭 / 아니면 신규)
3. STRESS   Workflow stress_test.workflow.js (후보를 args로 주입)
            적용(수행)→skeptic 적대검증 → survived / rejected / redesign_queue
4. MERGE    python scripts/04_merge_v4.py → data/r5_v5_working.json (F88+, 원본 불변)
5. PROMOTE  (다음 턴) r5_v5_working → mvp module_thinking_cards + /schedule cron — HANDOFF.md
```

## 소스 어댑터 (`--source`)

| source | 소스 | 신규 판정 | 인사이트 필터 | 상태 |
|---|---|---|---|---|
| `naver` | PLAY30 산업분석 PDF | sha1(broker\|title\|date) | 증권 리포트=태생적 인사이트 | 작동 |
| `seekingalpha` | mvp news_alert.db SA 본문 | url_hash | 본문>1500자 + 이벤트 헤드라인 제외 | 작동 |
| `inbox` | data/inbox_pdf/ 수동 PDF·txt | sha1(filename) | 사람이 고른 IB 리포트 | 골격 |
| `youtube_kr/en` | PLAY33 애널리스트·리서치 채널 | video_id(seen.json) | 채널 화이트리스트+제목필터 | 골격(GPU 필요) |

## 빠른 시작
```powershell
pip install pdfminer.six requests beautifulsoup4   # 한 번만

# 국내
python scripts\01_ingest.py --source naver --list-only          # 목록/신규 분류
python scripts\01_ingest.py --source naver --pages 1 --limit 1   # 신규 1건 PDF→txt
# 외국 (라이브 스크래핑 0 — db 적재분만)
python scripts\01_ingest.py --source seekingalpha --limit 1

# 카드화·스트레스·머지는 Claude(orchestrator.md)가 Agent/Workflow로 운전
python scripts\04_merge_v4.py --status                          # 작업사본 현황
```

## 입력 / 출력
- **입력(불변):** PLAY30 코드 / mvp news_alert.db / PLAY31 프롬프트 / PLAY32 v4 json·프로토콜.
- **출력(이 PLAY 안에만):** `data/inbox/` `data/cards/` `data/stress/` `data/r5_v5_working.json`
  `data/seen_reports.json` `data/function_redesign_queue.jsonl`.

## 가정 & 제약
- 스트레스 통과 게이트 = **적대검증 생존 AND source_card_count≥2** (PLAY31/32 승격 기준).
  단일 카드 후보는 생존해도 보류(2번째 카드가 보강할 때까지) — 정상 동작.
- 유튜브 전사·정식모듈 승격·cron은 골격/문서만(다음 턴, GPU Whisper 필요).
- Seeking Alpha 인사이트 필터는 휴리스틱(본문 길이+헤드라인) — best-effort.
- 워크플로우는 파일 접근 불가 → 후보 함수는 메인이 `args.candidates`로 주입(서브에이전트는 Bash로 db 접근 가능).

## 인터페이스 + 스킬
- **타임라인 뷰어**: `python scripts\build_timeline.py` → `viewer\timeline.html` (자체완결, 더블클릭).
  세 시대(① 유튜브 기원 E시리즈 / ② 증권 리포트 부트스트랩 26건 B시리즈 / ③ 라이브 신규)를 한 화면에,
  각 리포트가 카드·신규함수·매칭·스트레스 결과를 어떻게 더했는지 배지로 표시. 소스 토글 필터.
- **`/card-factory` 스킬** (`~/.claude/skills/card-factory/`): 쓰면 신규 전체 수집→카드화→스트레스→머지→
  타임라인 갱신 후 diff 보고. 모드: `update`(전체, 비용) / `timeline`(무료) / `ingest`(무료). 숫자=카드화 상한.

## 변경 이력
- 2026-06-12 — 최초 생성. 증분추적(`ingest_state`)+소스 어댑터(`01_ingest`: naver·seekingalpha 작동,
  inbox·youtube 골격)+스트레스 워크플로우+머지(`04_merge_v4`, v5 작업사본). 국내+외국 1건씩 end-to-end 증명.
- 2026-06-12 — 타임라인 뷰어(`build_timeline.py`→`viewer/timeline.html`) + `/card-factory` 스킬 추가.
  코퍼스 3시대(기원 유튜브 / 부트스트랩 26 / 라이브) 시각화, 스킬로 업데이트 자동화.
