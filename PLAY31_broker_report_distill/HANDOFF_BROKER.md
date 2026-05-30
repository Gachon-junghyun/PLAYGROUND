# PLAY31 인수인계 — 증권사 리포트 → 사고 회로 카드

> **다음 Claude Code 세션은 이 문서 + `README.md` + `prompts/broker_reverse_distill.md` 3개만 읽으면 즉시 시작 가능.**
> 작성일: 2026-05-27

---

## TL;DR (30초)

- PLAY13/28의 R4 카드는 **유튜브 자막 5채널** 기반 (64장 + 28건 신규 진행 중)
- PLAY31는 **증권사 분석가 리포트** 기반 R4 카드 + R5 함수 신규 추출
- 출력은 PLAY13/28과 **호환 스키마** (카드 26필드 + 함수 11필드)
- 카드 ID prefix `B시리즈` (B001~), R5 함수 ID `F045~` (기존 F001~F044 다음)
- **사용자 강조 룰 2개**:
  1. 리포트 본문 *끝까지 다 읽기* (페이지 임의 컷 절대 금지)
  2. 명제 하나하나 (사실/해석/추론/예측) 분리 후 사고 함수 *역추출*

---

## 1. PLAY13/28과의 본질적 차이

| 측면 | PLAY13/28 (유튜브 자막) | PLAY31 (증권사 리포트) |
|---|---|---|
| 입력 소스 | Whisper STT 자막 .txt | 분석가 리포트 PDF (텍스트 추출 .txt) |
| 화자 | 4~5명 다중 화자, 발화 raw_quote | 분석가 1명, 분석가 view 일관 |
| 정량 데이터 | 거의 없음 (정성 발화) | 풍부 (EPS/매출/마진/멀티플) |
| 결론 형태 | 비공식 의견, 시나리오 | BUY/HOLD + 목표주가, 명시적 |
| 차별화 지점 | 화자 시각 차이 ("내 생각은…") | **컨센 대비 stance** (above/below/inline) |
| `speaker_views` 필드 | 화자 dict | `report_attribution` 메타 + `analyst_view` 한 줄 |
| 명제 단위 분해 | 한정적 (발화는 비구조적) | **필수** — 리포트는 주장-근거 구조 명확 |

### 핵심 질문 (R4 핵심 질문의 증권사 버전)
PLAY13:
> "이 뉴스에서 인사이트 좋은 사람이라면 무엇을 *이상하게* 봤을까?"

PLAY31:
> **"이 리포트에서 분석가는 *컨센서스/시장 반응과 무엇이 달랐는가*? *왜* 다르게 봤는가?"**

증권사 리포트는 컨센과 차별화된 view를 팔러 나옴. 컨센과 같은 view → 카드 가치 낮음. 차별화 지점이 사고 회로의 출발.

---

## 2. PLAY13/28과의 자산 공유

### 공유하는 자산 (참조 only, 변질 금지)
- `r5_thinking_functions.json` — 44 함수. PLAY31의 카드가 매칭 우선 시도.
- `r6_data_sources.json` / `r6_indicators.json` / `r6_action_templates.json` — R5 v2 실행 layer.
- `insight_storage_quality_guide.md` — 16 framework + 품질 테스트.
- `reverse_distillation_cards.json` — 자동 템플릿 7개 + framework 정의 (audit 비교용).

### 독립 자산 (PLAY31 안에서 생성)
- `data/cards/*.jsonl` — Agent batch 출력 카드
- `data/all_cards.jsonl` — 통합본
- `data/all_cards.md` / `all_stats.md` — 사람용
- `data/function_candidates.jsonl` — 신규 R5 함수 후보 (기존 44개와 매칭 안 된 카드)

### 통합 시점
PLAY31의 카드/함수가 어느 정도 쌓이면 (보수적으로 20카드/5함수 이상) `r5_thinking_functions.json`에 함수 후보 append. 이건 *수동 결정* — 자동 머지 금지.

---

## 3. 데이터 자산 (절대경로)

| 자료 | 경로 | 상태 |
|---|---|---|
| 입력 리포트 (txt) | `data/inputs/` | 사용자가 두는 곳. PDF → txt 변환은 PDF Tools MCP 또는 사용자 사전 처리 |
| Agent batch input | `data/batches/<batch_name>.jsonl` | 메인이 prepare 단계에서 생성 |
| Agent 카드 출력 | `data/cards/<batch_name>.jsonl` | subagent 출력 |
| 신규 함수 후보 | `data/cards/<batch_name>.functions.jsonl` | subagent 출력 |
| 기존 R5 함수 | `../PLAY13_insight_distill/data/r5_thinking_functions.json` 또는 PLAY28 동기 사본 | 매칭 참조 |
| 16 framework 정의 | `../PLAY13_insight_distill/data/reverse_distillation_cards.json` | audit P7 비교 |

---

## 4. 작업 절차 (5단계)

```
1. ingest       사용자가 리포트 .txt를 data/inputs/에 둠 (또는 메인이 PDF → txt 변환)
2. prepare      data/batches/<batch>.jsonl 생성 (스키마 §6)
3. synth        subagent N개 병렬 호출, prompts/broker_reverse_distill.md 사용
4. audit        자동 템플릿 검출 + 명제 누락 자가 체크 + 차별화 지점 확인
5. consolidate  data/all_cards.jsonl + .md + _stats.md 생성
```

각 단계는 독립 실행. 산출물이 다음 단계 입력. PLAY13/28의 prepare/audit/consolidate 스크립트 패턴 그대로 재활용 가능 (path만 수정).

---

## 5. Agent 호출 인자 명세

메인 컨텍스트가 subagent에게 줄 인자:

```python
# 예시 호출
Agent({
    "description": "PLAY31 broker R4 batch B1",
    "subagent_type": "general-purpose",
    "prompt": f"""
{open('PLAY31_broker_report_distill/prompts/broker_reverse_distill.md').read()}

---

## 이번 batch 호출 인자

- INPUT_LIST_FILE: PLAY31_broker_report_distill/data/batches/B1_kor_power.jsonl
- OUTPUT_CARDS_FILE: PLAY31_broker_report_distill/data/cards/B1_kor_power.jsonl
- OUTPUT_FUNCTIONS_FILE: PLAY31_broker_report_distill/data/cards/B1_kor_power.functions.jsonl
- CARD_ID_START: B001
- CARD_ID_END: B010
- FUNCTION_ID_START: F045
- EXISTING_R5_FUNCTIONS_FILE: PLAY13_insight_distill/data/r5_thinking_functions.json
- SECTOR_CONTEXT: "전력인프라 / HD현대일렉트릭·LS ELECTRIC 등 4종 / 1Q25 실적 시즌"
"""
})
```

### batch 분할 가이드

리포트 1개 = 8~30페이지 = 8K~50K 토큰. Agent 컨텍스트 200K. 즉 batch 1개당 리포트 3~6개가 안전.

분할 기준 우선순위:
1. **섹터 단위** (전력인프라 / 반도체 / 조선 / 방산 / 매크로 등) — 사고 함수 클러스터링 유리
2. **증권사 단위** (한투/미래/삼성/NH 등) — 분석가 사고 습관 비교 유리
3. **시점 단위** (분기실적 시즌 한 묶음) — 비교 가능

### 카드 ID 영역 사전 할당 (충돌 방지)

| batch | 카드 ID 영역 | 새 함수 ID 영역 | 목표 카드 |
|---|---|---|---|
| B1 | B001~B010 | F045~F050 | 5~10 |
| B2 | B011~B020 | F051~F056 | 5~10 |
| B3 | B021~B030 | F057~F062 | 5~10 |
| ... | ... | ... | ... |

영역 미리 할당해야 병렬 호출 시 ID 충돌 없음. PLAY13 R4 9 Agent 병렬 호출 패턴 동일.

---

## 6. batch jsonl 스키마

```jsonc
{
  "report_id": "rpt_001",
  "broker": "한국투자증권",
  "analyst": "홍길동",
  "publish_date": "2026-05-20",
  "target": "HD현대일렉트릭 (267260)",
  "report_type": "earnings_update",     // initiation | update | deep_dive | flash | thematic
  "file_path": "PLAY31_broker_report_distill/data/inputs/rpt_001.txt",
  "page_count": 18,
  "size_bytes": 42183
}
```

`report_id`는 사용자가 정함 (예: rpt_001) 또는 `broker_target_date` 형식 자동 생성.

---

## 7. 검수 루프

### 자동 검수 (스크립트, 사용자 무인 진행 OK)

1. **자동 템플릿 검출** — `r4_audit_templates.py` 패턴 그대로. PLAY13/28의 7 금지 패턴.
2. **명제 누락 체크** — 각 카드의 `propositions` 필드가 *최소 3개 + fact/inference/forecast 각 1개 이상* 포함되어야 함. 부족하면 재합성.
3. **차별화 지점 체크** — 카드의 `report_attribution.stance_vs_consensus`가 `inline` 또는 `n/a`면 *왜 카드인지 사유* 필요. 없으면 스킵.
4. **결론 복붙 체크** — `reasoning_move`에 "BUY", "목표주가", "EPS 추정치" 같은 결론 단어가 직접 들어가면 위반.

### 사람 검수 (사용자 위임)

- 영역별 카드 3장씩 무작위 샘플 → 사용자가 OK/NG
- NG 시 해당 batch 재호출

### 검수 실패 시 재합성 정책

- 위반 카드 1~2장이면 메인이 *해당 카드만 재합성* 요청 (subagent re-call)
- 3장 이상이면 *batch 전체 재호출* (프롬프트 자체 문제일 가능성)
- 동일 batch 재호출 3회 실패 시 멈추고 사용자에게 보고

---

## 8. 사용자 운영 룰 (PLAY13 §7 그대로)

- **코드는 Claude가 쓰고, 사용자는 방향만**. 사용자 답변은 짧은 시그널 위주.
- **정직한 진단 우선**. 차별화 지점 약함, 명제 누락 같은 문제는 즉시 보고.
- **jsonl + md 둘 다**. 기계용 + 사람용.
- **로컬 ollama 기본**. 단 "지능 사용" 명시 시 Claude OK (PLAY31의 Agent는 그 경우).
- **PLAYGROUND PLAY 규칙**: `README.md` = 계약서, 같은 턴에 갱신.
- **Agent 병렬 OK**. 단 카드 ID 영역 사전 할당.
- **HAN_LAB 100줄 룰**: 100줄 넘는 코드 한 번에 쏟기 전 (1) 파일 트리 (2) 각 파일 역할 (3) 그다음 코드.
- **자동 모드 금지**: 사용자 부재 명시 시에만 자동 진행.

---

## 9. 다음 세션 첫 동작 (체크리스트)

순서대로:

- [ ] 이 `HANDOFF_BROKER.md` 정독
- [ ] `README.md` 변경 이력 끝부분 확인
- [ ] `prompts/broker_reverse_distill.md` 정독 (Agent 프롬프트, §"작업 절차" Step 1~8)
- [ ] `data/inputs/` 비어있나? 비어있으면 사용자에게 리포트 요청
- [ ] 비어있지 않으면 `prepare_broker_inputs.py` 작성/실행 → `data/batches/`
- [ ] batch 분할안 + 카드 ID 영역 + 첫 호출 OK 사용자 확인
- [ ] Agent N개 병렬 호출 (B1~Bn)
- [ ] `r4_audit_templates_new.py` 패턴으로 audit (broker 변종 스크립트)
- [ ] `r4_consolidate_new.py` 패턴으로 consolidate
- [ ] 사용자 검수 → 통과 카드만 최종본으로 확정

---

## 10. 알려진 위험 / 함정

1. **PDF → txt 변환 품질**. 표·차트가 본문 사이에 박혀 텍스트 추출이 깨지면 정량 근거 누락. PDF Tools MCP의 `read_pdf_content` 사용 권장.
2. **분석가 1명 view라 화자 다양성 0**. R4의 "화자 시각 차이"가 없음. 대신 **컨센 대비 stance**가 차별화 지점.
3. **결론 복붙 유혹**. 리포트는 결론(BUY/목표주가)이 표지에 명시돼 있어 Agent가 그걸 그대로 카드에 복붙할 위험 큼. 프롬프트 §Step 7 C에서 명시 차단.
4. **컨센 데이터 부재**. 분석가가 "컨센은 X, 우리는 Y"라고 명시했으면 OK. 안 했으면 차별화 지점 모호 → 카드 가치 낮음 → 스킵 OK.
5. **리포트 페이지 임의 컷 위험**. Agent 컨텍스트 토큰 절약 본능. 프롬프트 §Step 2에서 *모든 페이지 읽기* 명시 + Step 7 A에서 자가 체크.
6. **F045~ 신규 함수 폭증 위험**. 새 함수를 너무 쉽게 발행하면 R5 라이브러리 노이즈. 매칭 60% 기준 + source_card_count ≥ 2 이상일 때만 정식 함수로 승격 (단일 카드 함수는 후보로 두되 R5에 머지하지 말 것).
7. **시점 종속**. R4/R5의 시점 독립 원칙 그대로. 새 함수의 `name`/`abstract_form`/`trigger_when`에 종목명/이벤트명 박지 말 것.
8. **batch ID 충돌**. PLAY13/28의 E시리즈, R5의 F001~F044와 절대 겹치지 말 것. B001~ 카드 + F045~ 함수.

---

## 11. 한 줄 정리

**"증권사 리포트의 결론(BUY/목표주가)은 메타다. *컨센과 어긋난 지점*, *분석가가 추가로 끼워 넣은 변수*, *반증 조건과 함께 던진 시나리오* — 이게 사고 회로다. 명제 단위로 뜯어서 역추출하라. 페이지 임의 컷 절대 금지."**
