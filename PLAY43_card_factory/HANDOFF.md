# PLAY43 HANDOFF — 다음 턴 작업

이번 턴 완료: 스켈레톤 + 증분추적 + 소스 어댑터(naver·seekingalpha 작동) + 스트레스 워크플로우 +
머지(v5 작업사본) + 국내·외국 1건씩 end-to-end 증명. 아래는 **골격만 깔린 다음 단계**.

## 1. 유튜브 어댑터 실전화 (애널리스트·리서치 채널)
`01_ingest.py --source youtube_en`은 현재 PLAY33 명령만 출력. 실제 배선:
```powershell
$env:PLAY33_TOPIC = 'analyst_research_en'
python <PLAY33>\scripts\01_discover.py "equity research analyst market outlook stock thesis" --min-subs 50000
python <PLAY33>\scripts\02_fetch.py --from-channels data_analyst_research_en\channels.jsonl -n 40 `
    --match "thesis,valuation,earnings,outlook,downgrade,upgrade" --keep 8
python <PLAY33>\scripts\03_pipeline.py --language en        # GPU Whisper large-v3
```
- 전사된 `data_analyst_research_en/transcripts/*.txt` 를 PLAY43 `data/inbox/`로 복사하는 브리지
  (`01_ingest.py`에 youtube 어댑터 본구현: manifest.jsonl 읽어 transcript→inbox txt + video_id를 seen_reports에).
- 국내는 `analyst_research_ko` + 한국 증권 유튜브 키워드.
- 주의: 유튜브는 "사고방식" 추출이라 broker_reverse_distill보다 PLAY33 subagent_distill 변형이 맞을 수 있음 — 카드 스키마 정합 확인.

## 2. inbox 어댑터 실전화
`data/inbox_pdf/`에 골드만·모건스탠리·노무라 영문 리서치 PDF를 드롭하면 작동(이미 구현됨).
검증만 안 됨 — 실제 IB PDF 1건으로 pdfminer 추출 품질 확인 필요.

## 3. 정식 모듈 승격 (mvp)
`data/r5_v5_working.json`이 충분히 쌓이고 안정되면:
- mvp `research_Mvp/module_thinking_cards/`로 승격 (PLAY32 v4 json을 v5로 교체할지는 **사용자 결정**).
- 승격 = 작업사본을 mvp `insight_corpus/`에 복사 + `module_*` CLI 컨벤션 맞추기.
- **원본 v4 교체는 사용자 명시 승인 필요** (PLAY32 README 룰).

## 4. Claude 스케줄링 (cron)
주 1회 1→4단계 자동 실행. `/schedule` 또는 settings.json cron:
- 수집(01_ingest naver+seekingalpha)은 결정론적 — cron이 직접 Bash.
- 카드화·스트레스는 Agent/Workflow라 Claude 세션 필요 → routine(원격 에이전트)으로 orchestrator.md 실행.
- 산출 누적이 곧 "분산 확보" — 단일 카드 보류분이 2번째 카드로 승격되는 시점을 cron이 잡는다.
- 제안 주기: 네이버 산업분석 리포트 갱신 빈도(평일 다수) 고려해 **주 2회**(화·금) 정도.

## 5. 보강 아이디어
- 카드화 매칭(60% 겹침)을 임베딩 유사도로 정량화 (mvp corp_embeddings 패턴 차용).
- Seeking Alpha 인사이트 필터를 분류기로 (현재 헤드라인 패턴 휴리스틱 → 본문 기반).
- stress_test에 PLAY23 가격 백테스트 옵션 병행(방향성 콜 있는 카드만, predictions.csv 연계).
