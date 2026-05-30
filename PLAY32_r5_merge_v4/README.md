# PLAY32_r5_merge_v4

## 목적
mvp의 R5 v3(44 함수)와 PLAY31의 신규 R5 후보(66 함수)를 **중복 제거 + 레벨 검증**으로 결합해 R5 **v4** 통합 라이브러리를 만든다. 원본은 불변 — 산출물은 이 PLAY 안에만.

## 두 풀

| 풀 | 위치 | 함수 수 | function_id | 특징 |
|---|---|---|---|---|
| A (기존) | `C:\Users\fivep\OneDrive\Desktop\mvp\research_Mvp\insight_corpus\r5_thinking_functions.json` (= PLAY13 R5와 md5 동일) | 44 | F01~F44 | R6 layer(data_sources/indicators/action_at_trigger) + R7-B(indicators_examples_specific) 완비 |
| B (신규) | `../PLAY31_broker_report_distill/data/cards/B*.functions.jsonl` (11 파일) | 66 | 임시 `F45-Bx-NN`, `F045`, `F046`, `F093~F107` 점프 혼재 | base 11필드만, R6/R7-B 없음. source_card_count 대부분 1 |

**합계 풀: 110 함수.**

## 산출물
- `data/pool_combined.jsonl` — 두 풀을 한 줄=한 함수로 합친 통합 작업 풀 (Phase 1)
- `data/dup_pairs.jsonl` — Phase 2에서 머지·연결 결정한 함수 쌍/그룹
- `data/level_audit.md` — Phase 3 시점 독립·금지 패턴·추상화 균형 검수 보고
- `data/r5_v4_thinking_functions.json` — 최종 v4 라이브러리 (정식 등재 + 후보 분리)
- `data/merge_report.md` — 사람용 변경 요약 (어떤 신규가 어디로 머지됐는지)

## 실행법
이 PLAY는 Agent 위임 + 메인 직접 단계가 섞여 있다. 한 번에 자동화 스크립트로 끝나지 않음 — 단계별 산출물을 보면서 진행한다.

```powershell
# Phase 1 (수집) — 메인이 직접 한 번 돌림
python PLAY32_r5_merge_v4/scripts/01_collect.py
# 결과: data/pool_combined.jsonl

# Phase 2 (클러스터링) — Agent 위임
# 입력: data/pool_combined.jsonl
# 출력: data/dup_pairs.jsonl + 클러스터 결정 보고

# Phase 3 (레벨 검증) — Agent 위임
# 입력: pool_combined.jsonl
# 출력: data/level_audit.md

# Phase 4 (v4 산출) — 메인이 적용
# 입력: pool_combined.jsonl + dup_pairs.jsonl + level_audit.md
# 출력: data/r5_v4_thinking_functions.json + data/merge_report.md
```

## 입력 / 출력
- **입력 (절대 변경 금지):**
  - `C:\Users\fivep\OneDrive\Desktop\mvp\research_Mvp\insight_corpus\r5_thinking_functions.json`
  - `../PLAY31_broker_report_distill/data/cards/*.functions.jsonl` (11 파일)
- **출력 (이 PLAY 안에만):**
  - `data/pool_combined.jsonl`
  - `data/dup_pairs.jsonl`
  - `data/level_audit.md`
  - `data/r5_v4_thinking_functions.json`
  - `data/merge_report.md`

## 가정 & 제약
- **원본 불변.** mvp 폴더와 PLAY13 R5 파일은 절대 수정하지 않는다. 사용자가 v4를 받아본 뒤 직접 교체할지 결정.
- **함수 풀이 110개라 Agent 한 번에 다 못 본다.** Phase 2 클러스터링은 의미 단위로 묶어서 분할 위임 (예: 도메인별 — geopolitics·semiconductor·energy 등).
- **중복 판정 기준은 보수적으로.** 두 함수의 `abstract_form` + `trigger_when` 본질이 같으면 머지. 미세 차이가 있으면 `related_functions`로 연결만. R5 v3 원칙 "강제 클러스터링 금지"를 이어받는다.
- **신규 함수 source_card_count=1이 대부분.** 기존 함수와 머지되어 `≥2`가 되거나, 단독 후보로 보관(R5 v3 24개도 단일 카드 함수 보존된 선례).
- **F01~F44는 보존.** 신규 정식 등재는 F45부터 순차 할당. 후보는 `candidates` 배열에 분리, function_id 없이 임시 키만.
- **R6 layer는 이 PLAY에서 추가하지 않음.** 기존 44개는 R6 완비, 신규는 base 11필드만 — Phase 4 산출물에서 신규에 R6 빈 필드(`data_sources: []` 등)만 박아두고 본격 R6 매핑은 별도 PLAY로 분리.
- **디스패치 45초 제약.** 큰 비교 작업은 Agent로 위임, 메인은 데이터 수집·재포장만 담당.

## 변경 이력
- 2026-05-27 — 최초 생성. 두 풀(mvp R5 v3 44 + PLAY31 66 = 110) 파악 완료. Phase 1~4 단계 정의, 산출물 위치 명시.
- 2026-05-27 — Phase 1 완료. `scripts/01_collect.py` + `scripts/02_compact_view.py` 실행. `data/pool_combined.jsonl` (110줄, 264KB) + `data/pool_compact.md` (101KB) 생성.
- 2026-05-27 — Phase 2 완료 (Agent 위임). 32 클러스터(merge 15 / link 17). B풀 66개 중 **19개 흡수** (A로 14, B내부 5). 가장 큰 클러스터: F13(1차→N차 점프, scc 7), F01(narrative 깨질 조건, scc 6), F08(공급 캡파 경직성, scc 5). `data/dup_pairs.jsonl` 산출.
- 2026-05-27 — Phase 3 완료 (Agent 위임). 110 함수 검수 → pass 88 / warn 16 / fail 6. **시점 종속 고유명사 본문 잔존 0건**. fail 6건은 모두 B풀이고 추론 동선·라벨링 사유 (F045·F45-B5-03·F45-B6S-04·F45-B7-04·F45-B7-07·F45-B2-09). `data/level_audit.md` 산출.
- 2026-05-27 — Phase 4 완료 (메인 직접). `scripts/04_build_v4.py` 실행 → **`data/r5_v4_thinking_functions.json` v4 생성, 정식 등재 87 함수** (F01~F87). 흡수된 B 함수 19개는 `data/absorbed.jsonl`, fail standalone 4개는 `data/rejected.jsonl`, 사람용 요약은 `data/merge_report.md`. 17필드 완비, function_id 중복 0, source_card_count 분포 1:59 / 2:13 / 3:8 / 4:3 / 5:2 / 6:1 / 7:1.
- 2026-05-27 — **Phase 5 R6 매핑 완료.** 신규 43개 함수(F45~F87)에 R6 layer 4+1 필드 적용. 도메인별 3 그룹(A_semi 17 / B_energy 15 / E_misc 11) Agent 위임. 카탈로그 DS_*/ACT_* 신규 0건(전부 기존 키 재사용), IND_ABS_* 신규 2건, IND specific 신규 약 129건(43 함수 × ~3). R6 4필드 완비 80/87 — 부분 누락 7건은 v3 원본 inherit(A 풀 F09·F10·F11·F12·F14·F29·F34의 `indicators_examples_specific` 빈 배열, 우리 작업 무관). 매핑 파일: `data/r6_mapping_{A_semi,B_energy,E_misc}.jsonl`. 적용 보고: `data/r6_apply_report.md`.
- 2026-05-27 — **샘플 리포트 3종 작성** (전력 인프라 도메인): `samples/power_infra_2026q2_thesis.md` (5 thesis 시드 카드 + v4 함수 인용 정리), `samples/power_infra_2026q2_news_update.md` (news_alert.db 14일 sweep cross-check, 시드 카드 환경 보정), `samples/power_infra_2026q2_thesis_T3_execution.md` (T3 SMP 골든 카드 깊이 실행 — F87+F75+F53 9개 검증 질문 데이터 답, anti_signal 새 무력화 조건 발견, action_at_trigger 6종 실제 발동). T3 실행 노트가 *진짜 사고 = 인용 + 검증 + 액션* 모범 사례.
- 2026-05-28 — **실행 프로토콜 작성**: `prompts/r5_v4_execution_protocol.md`. T3 사례를 일반화 → 6-Step(A unpack / B 데이터 답 / C anti_signal 판정 / D 액션 발동 / E 공백·다음 / F 메타 회고) + 4 절대 원칙(인용 금지, 데이터 우선, 라이브러리 진화, 정직) + 7 안티패턴 + 효율화 룰. R5 v4 라이브러리 운영 표준.
