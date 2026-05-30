# 인수인계 — 네이버 산업분석 29개 리포트 → broker distill 투입

> 작성일: 2026-05-27. 이전 세션(Cowork)에서 PDF 수집 + triage까지 끝냄. 이 문서는 **다음 세션이 바로 이어받기 위한 프롬프트**다.
> 함께 읽을 것(이미 존재, 정독 필수): `README.md`, `HANDOFF_BROKER.md`, `prompts/broker_reverse_distill.md`.

---

## 0. 미션 한 줄
네이버 금융 산업분석에서 받은 증권사 리포트 29개를 `broker_reverse_distill` 파이프라인에 태워 사고회로 카드(B시리즈) + 신규 R5 함수(F045~)로 역추출한다. **결론(BUY/목표주가)이 아니라 "분석가가 컨센과 어디서·왜 다르게 봤는가"를 명제 단위로 뜯는 게 목적.**

## 1. 지금까지 된 것 (이전 세션)
- 네이버 금융 산업분석 1페이지 PDF **29개 다운로드 완료**.
  - 위치: `C:\Users\fivep\OneDrive\Desktop\PLAYGROUND\PLAY29_naver_research_dl\naver_research_reports\`
  - 파일명: `01_*.pdf` ~ `29_*.pdf` (제목_증권사 형식)
  - 다운로더 코드: `PLAY29_naver_research_dl\naver_research_dl.py` (requests+bs4, `--selftest` 통과). 로컬에서 `run.bat`로 받음.
  - **전부 디지털 PDF(텍스트 레이어 있음)** — pymupdf로 깨끗이 추출됨. OCR 불필요.
- 29개 triage 완료 (아래 §3).
- `broker_report_distill` 스펙 3종(README/HANDOFF_BROKER/prompt) 정독 완료.

## 2. 아직 안 된 것 (= 다음 세션 할 일)
파이프라인은 **설계만 돼 있고 공장은 안 지어짐.** 빠진 조각 3개:
1. **PDF→txt 브리지** — `data/inputs/`가 **비어 있음**. 29개(또는 선별분)를 txt로 추출해 적재해야 함. 스펙은 이걸 "PLAY 범위 외"로 두지만, 텍스트 레이어가 살아 있으니 pymupdf로 바로 가능:
   ```python
   import fitz  # pip install pymupdf --break-system-packages
   d = fitz.open(pdf_path); txt = "".join(p.get_text() for p in d)
   ```
   추출 시 표지 메타(종목/분석가/증권사/작성일/투자의견)를 헤더로 붙이면 batch jsonl 채우기 쉬움(§prompt 입력형식 참고).
2. **스크립트 3개 작성 (전부 TODO):** `scripts/prepare_broker_inputs.py`, `scripts/r4_audit_templates_broker.py`, `scripts/r4_consolidate_broker.py`. PLAY28의 `prepare_r4_inputs_new.py` / `r4_audit_templates_new.py` / `r4_consolidate_new.py` 변종으로 path만 바꿔 작성(HANDOFF_BROKER §4).
3. **Agent 병렬 합성** — 메인 Claude가 `prompts/broker_reverse_distill.md` + batch별 호출인자로 subagent 호출(HANDOFF_BROKER §5). 카드 ID 영역 사전할당 필수.

## 3. 29개 triage 결과 (차별화 신호 = 컨센/시장은/우려/편견/재평가 등 키워드 빈도)

**고가치 (deep + 신호 강함) — 우선 처리:**
| # | 제목 | 증권사 | 쪽 | 신호 |
|---|---|---|---|---|
| 05 | 중국 자동차에 편견을 걷어내야 할 때 | iM증권 | 45 | 49 |
| 09 | 중요한 건 아직 꺾이지 않은 실적 업사이클 | 하나증권 | 17 | 26 |
| 20 | K-Energy, 재평가의 서막 | 하나증권 | 43 | 25 |
| 10 | 단기 투자선호도 태양광/정유화학 | 하나증권 | 47 | 17 |
| 28 | 같은 궤도, 다른 속도 | 하나증권 | 16 | 13 |
| 15 | 메모리 가격 상승을 견인하는 Nvidia | 하나증권 | 31 | 12 |
| 07 | 타오르는 시장에 솟구치는 투자 | 현대차증권 | 72 | 11 |
| 22 | 모든 우려가 선 반영된 주가 | 하나증권 | 17 | 10 |

**중간 (deep, 신호 약함) — 명제 분해는 가능:** 11, 13(중국 철강), 14, 17, 18(반도체 장비), 21(로봇 2H26), 23(K-Energy 요약본?), 24(호르무즈), 25, 26(전망포럼), 27, 29(산유국)

**저가치 / 스킵 권고 (daily·short·시황 weekly, 신호 0~약):** 01 데일리(1p), 03 IBKS 데일리(1p), 06 핵잠(3p), 19 지방선거공약(3p), 02·04·08·16 weekly

## 4. 알려진 함정 / 판단 필요
- **20 vs 23 중복 의심**: 둘 다 "K-Energy 재평가의 서막"(20=43p·신호25, 23=29p·신호4). 풀버전 vs 요약본일 가능성. dedup 또는 둘 중 하나만 투입할지 확인.
- **PLAY 번호 충돌**: 다운로더가 `PLAY29_naver_research_dl`로 이 `PLAY29_broker_report_distill`과 번호 겹침. CLAUDE.md 명명규칙상 다운로더를 **`PLAY30_naver_research_dl`로 rename** 권장(README 변경이력도 같이).
- **산업/테마 리포트라 단일종목 아님**: 스펙 카드 예시는 종목 실적 기준이지만 이 29개는 대부분 산업/테마. `report_type`=thematic/deep_dive, `target`=섹터로 매핑하면 그대로 맞음.
- 한글 공백 누락 PDF(예: 01번 "당사는자료작성일...")은 글리프 문제 — 후처리로 정리 가능, OCR 아님.

## 5. 실행 순서 (5단계)
1. **ingest**: 선별분 PDF→txt → `data/inputs/<report_id>.txt` (report_id 예: `iM_china_auto_20260527` 또는 `rpt_05`).
2. **prepare**: `prepare_broker_inputs.py`로 `data/inputs/` 스캔 → 섹터 단위 `data/batches/<batch>.jsonl`. 섹터 분할안: **자동차 / 에너지·정유화학(04·10·20·24·29) / 반도체·소재(13·15·18) / 방산·조선·로봇(01·02·06·21) / 전략·매크로(07·09·14·17·22·25·26·27·28) / 기타(03·12·19)**.
3. **synth**: batch별 카드 ID 영역 사전할당(B1=B001~B010·F045~, B2=B011~…) 후 Agent 병렬 호출.
4. **audit**: `r4_audit_templates_broker.py`로 자동템플릿 7패턴 + 명제 누락 + 차별화 지점 검출.
5. **consolidate**: `r4_consolidate_broker.py`로 `data/all_cards.jsonl` + `.md` + `_stats.md`.

## 6. 사용자에게 받아야 할 결정 (이전 세션에서 질문 도구가 죽어 미확정)
- **처리 범위**: (A) 고가치 deep 8건만 / (B) daily·short·weekly 제외한 deep ~20건 / (C) 29건 전부. → 이전 세션 추천은 **A**(품질↑, Agent 비용↓).
- **실행 깊이**: (1) 인프라+첫 batch까지 Agent 합성해 카드 샘플까지 / (2) 인프라(txt적재+스크립트 3개)만 / (3) 계획만.

## 7. 운영 룰 (HANDOFF_BROKER §8 요약)
- 코드는 Claude가 쓰고 사용자는 방향만. 정직한 진단 우선(차별화 약함/명제 누락 즉시 보고).
- jsonl + md 둘 다 출력. 표준 라이브러리만(LLM 직접 SDK 호출 X, 합성은 메인의 Agent tool).
- PLAYGROUND 규칙: README = 계약서, 같은 턴에 갱신. 100줄+ 코드는 (파일트리→역할→코드) 순.
- Agent 병렬 OK, 단 카드 ID 영역 사전할당. 사용자 부재 명시 시에만 자동 진행.
- **45초 디스패치 제약**: PDF→txt·prepare·audit·consolidate는 가볍게. 큰 리포트(07=72p, 10=47p, 05=45p) 추출은 batch로 쪼개 시간 초과 주의.

## 8. 핵심 경로 모음
- 다운된 PDF: `PLAY29_naver_research_dl\naver_research_reports\*.pdf`
- distill 작업폴더: `PLAY29_broker_report_distill\` (data/inputs·batches·cards, prompts/, scripts/[미생성])
- 기존 R5 함수(매칭 참조): `PLAY13_insight_distill\data\r5_thinking_functions.json` (44개, F001~F044)
- framework 정의(audit 비교): `PLAY13_insight_distill\data\reverse_distillation_cards.json`
- bash 마운트: PLAYGROUND → `/sessions/<id>/mnt/PLAYGROUND/` (각 세션 id 다름, 시작 시 확인)
