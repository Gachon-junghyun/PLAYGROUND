# PLAY29_broker_report_distill

## 목적
증권사 분석가 리포트(PDF→txt)에서 **분석가가 컨센서스/시장 반응과 *어떻게 다르게 봤는가*** 를 역추출해 사고 회로 카드(B시리즈)와 신규 R5 사고 함수(F045~)로 만든다. PLAY13/28의 자막 R4와 *호환 스키마* — 카드 26필드 + 함수 11필드. 출력물은 PLAY13/28 자산과 같은 RAG 코퍼스에 통합 가능.

> 핵심 질문: **"이 리포트에서 분석가는 *컨센서스/시장 반응과 무엇이 달랐는가*? *왜* 다르게 봤는가?"**

## 데이터 흐름
```
[1] ingest      사용자가 리포트 .txt를 data/inputs/에 둠 (PDF는 사전 변환)
[2] prepare     data/batches/<batch>.jsonl 생성 (섹터/증권사/시점 단위 분할)
[3] synth       subagent N개 병렬 호출 (prompts/broker_reverse_distill.md)
                 → data/cards/<batch>.jsonl + data/cards/<batch>.functions.jsonl
[4] audit       자동 템플릿 7 + 명제 누락 + 차별화 지점 검수
[5] consolidate data/all_cards.jsonl + .md + _stats.md
[*] (수동) 함수 후보가 충분히 쌓이면 R5 라이브러리에 머지
```

PLAY13/28의 스크립트 패턴 그대로 재활용 (path만 변경). prepare_broker_inputs / r4_audit_templates_broker / r4_consolidate_broker 같은 변종으로 작성.

## 실행법

```powershell
cd PLAY29_broker_report_distill

# 1) 리포트 ingest (사용자 또는 메인이 PDF → txt 변환)
#    PDF Tools MCP 또는 외부 변환 도구 사용
#    출력 위치: data/inputs/<report_id>.txt

# 2) batch 분할 (prepare_broker_inputs.py 작성 필요, PLAY28 prepare_r4_inputs_new.py 패턴)
python scripts/prepare_broker_inputs.py
#   data/inputs/ 스캔 → data/batches/<batch>.jsonl 생성

# 3) Agent 병렬 호출 (메인이 호출)
#    프롬프트: prompts/broker_reverse_distill.md
#    인자: INPUT_LIST_FILE, OUTPUT_CARDS_FILE, OUTPUT_FUNCTIONS_FILE,
#          CARD_ID_START/END, FUNCTION_ID_START, EXISTING_R5_FUNCTIONS_FILE, SECTOR_CONTEXT
#    HANDOFF_BROKER.md §5 호출 인자 명세 참조

# 4) audit (r4_audit_templates_broker.py 작성 필요, PLAY28 r4_audit_templates_new.py 패턴)
python scripts/r4_audit_templates_broker.py
#   data/audit_broker.md 출력. 위반 0건 확인.

# 5) consolidate (r4_consolidate_broker.py 작성 필요, PLAY28 r4_consolidate_new.py 패턴)
python scripts/r4_consolidate_broker.py
#   data/all_cards.jsonl + all_cards.md + all_stats.md 출력
```

**의존:** 표준 라이브러리만. (LLM 호출은 메인 Claude의 Agent tool, ollama/anthropic SDK 직접 호출 X)

## 입력 / 출력

### 입력
- **리포트 .txt** — `data/inputs/<report_id>.txt`. PDF를 사용자가 사전 변환. 형식:
  ```
  [표지/메타]
  종목: HD현대일렉트릭 (267260)
  분석가: 홍길동 / 한국투자증권
  작성일: 2026-05-20
  투자의견: BUY / 목표주가: 200,000원

  [본문]
  ... (페이지/섹션 구분은 흐릿해도 됨, Agent가 처리)
  ```
- **batch jsonl** — `data/batches/<batch>.jsonl`. 스키마는 [HANDOFF_BROKER.md §6](HANDOFF_BROKER.md) 참조.

### 출력
- `data/cards/<batch>.jsonl` — Agent batch 출력 카드 (B001~)
- `data/cards/<batch>.functions.jsonl` — 신규 R5 함수 후보 (F045~)
- `data/all_cards.jsonl` — 통합 (기계용)
- `data/all_cards.md` — 사람용 (4 핵심 필드 풀)
- `data/all_stats.md` — 메타 통계 (broker/sector/grade/framework 분포)
- `data/audit_broker.md` — 자동 템플릿 검출 결과

스키마 자세한 정의는 [prompts/broker_reverse_distill.md](prompts/broker_reverse_distill.md) §"카드 스키마 (B시리즈)".

## 가정 & 제약

1. **PLAY13/28과 호환 스키마.** 카드 26필드, R5 함수 11필드 동일. 단 R4의 `speaker_views`/`source_videos`가 `report_attribution`/`analyst_view`/`source_reports`로 교체.
2. **카드 ID prefix `B`, 함수 ID prefix `F` (F045~).** PLAY13/28의 E시리즈, F001~F044와 충돌 없음. 사전 영역 할당으로 병렬 호출 안전.
3. **PDF → txt 변환은 PLAY 범위 외.** 사용자 사전 처리 또는 PDF Tools MCP 활용. 변환 품질이 나쁘면 정량 근거 누락 → 카드 품질 저하. 권장: `read_pdf_content` 같은 텍스트+레이아웃 보존 추출.
4. **컨센 데이터 부재 시 차별화 지점 불명확.** 분석가가 "컨센은 X, 우리는 Y"라고 명시 안 한 리포트는 카드 가치 낮을 가능성. 프롬프트 §Step 7 D에서 스킵 허용.
5. **분석가 1명 view라 화자 다양성 0.** R4의 "화자 시각 차이" 없음. 대신 *컨센 대비 stance*가 차별화 지점.
6. **결론 복붙 유혹 큼.** 리포트는 결론(BUY/목표주가)이 표지에 명시. 프롬프트 §Step 7 C에서 명시 차단.
7. **페이지 임의 컷 위험.** Agent 컨텍스트 토큰 절약 본능. 프롬프트 §Step 2 + Step 7 A에서 *모든 페이지 읽기* 명시 + 자가 체크.
8. **신규 R5 함수 폭증 위험.** 매칭 60% 기준 + `source_card_count ≥ 2` 일 때만 정식 함수 승격. 단일 카드 함수는 후보로 두되 R5 라이브러리에 자동 머지 금지.
9. **45초 디스패치 제약:** prepare/audit/consolidate는 빠름 (수 초). Agent 호출은 리포트 5~6개 batch × N agent 병렬이면 컨텍스트 부담 OK. 단 PDF → txt 변환은 *반드시 사전*에 (사용자가).
10. **시크릿:** PLAY29 코드에 직접 박은 키 없음. Agent 호출은 메인 Claude의 도구로.

## 변경 이력
- 2026-05-27 — 최초 생성. PLAY13/28의 R4 자막 패턴을 증권사 리포트로 확장. 핵심 산출물:
  - `prompts/broker_reverse_distill.md` (Agent용 통합 R4+R5 합성 프롬프트, 명제 단위 분해 + 차별화 지점 식별 + 사고 함수 매칭/신규 후보 8단계)
  - `HANDOFF_BROKER.md` (다음 세션 인수인계, PLAY13/28과의 차이·자산 공유·작업 절차·검수 루프 명세)
  - 디렉토리: `data/inputs`, `data/batches`, `data/cards`, `prompts`
  - 카드 ID prefix `B시리즈` (B001~), 함수 ID `F045~` 할당 (PLAY13/28 충돌 방지)
- TODO: `scripts/prepare_broker_inputs.py` + `scripts/r4_audit_templates_broker.py` + `scripts/r4_consolidate_broker.py` 작성 (PLAY28 변종 패턴 그대로 path만 수정). 사용자가 첫 리포트 batch 던지면 그때 같이 작성.
- 2026-05-27 — 네이버 산업분석 29개 PDF 수집 + triage 완료(다른 세션). 인수인계: `HANDOFF_NAVER_BATCH.md` (PDF 위치·triage 등급·실행순서·미확정 결정 2건). `data/inputs/` 아직 비어있음.
