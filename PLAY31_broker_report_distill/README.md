# PLAY31_broker_report_distill

## 목적
증권사 분석가 리포트를 붙여넣으면, 결론(BUY/목표주가)이 아니라 **분석가가 그 결론에 도달한 사고 경로**를 명제 단위로 뜯어 "사고 회로 카드(B시리즈)" + "사고 함수(F045~)"로 역추출한다. PLAY13/28 distill 코퍼스와 호환 스키마.

## 현재 상태 (2026-05-27, R5 Phase 1 라운드 종료)
- 입력 리포트 **29건** 투입 완료 (`data/inputs/rpt_*.txt`).
- 11개 배치로 분배(`data/batches/B1~B10_*.jsonl`). pilot 배치(B6) 포함.
- 카드 합성 1차 완료 → 중복 정리 → 검증·업그레이드 → **R5 Phase 1 함수 추출 완료**. 현재 **카드 71 / 사고함수 66**.
- 검증 통계: 사실 불일치 **10건 검출**, 총 **40건 수정**, stance 변경 **2건**. 백업 12개(`*.jsonl.bak`) 동거.
- R5 Phase 1 통계: B1~B5/B6_steel_bank/B7 7개 배치 53장 → **52 신규 함수 추출** (B2 1건 클러스터링 외 모두 1카드:1함수 보존). 모든 함수가 시점 종속 고유명사 0건 자가검수 통과. function_id는 임시 `F45-Bx-NN` (Phase 4 통합 시 R5 v3 F44 다음으로 재할당 예정).
- **consolidate 단계 미실행.** `data/cards/all_cards.jsonl`, 사람용 `.md`, `_stats.md` 아직 없음.
- Phase 2~4 미실행: 클러스터링(≥2 정식 후보 선별) / R6 매핑(data_sources·indicators·action_at_trigger) / R7-B(indicators_examples_specific) / PLAY13 R5 v3 → v4 통합.

### 검증 라운드 핵심 발견 (수정 완료)
- **B044 (B5)**: 테스 1Q26 영업이익 표기 오류 — "22.2조" → "22.2십억원" (단위 1000배). 트리거 조건 전반 1Q26 실수로 교체.
- **B045 (B5)**: 씨엠티엑스 2026F 표기 오류 — "208억·70.3억" → "2,080억·703억" (단위 10배).
- **B068 (B7)**: 지분 주체 오기 — "현대글로비스 BD지분 20%·BD 직접 21.9%" → **"정의선 개인의 현대글로비스 20.0%·BD 직접 21.9% 지분"**. 카드 전반 일관 수정.
- **B099 (B10)**: 실적 변동성 설명 오류 — 영업이익/순이익 흑자전환 시점을 혼동했던 부분을 원문 표 기준으로 정정 (영업이익 23흑→24적→25흑전, 순이익 24흑전→25적).
- **B023 (B3)**: stance `inline`→`below`. 하나 2026F 영업이익 컨센 대비 -11%로 단기 below가 정합.
- **B077 (B8)**: stance `inline`→`below`. 네이버·카카오 AI 멀티플 자격 미충족 view 반영.

### 배치별 검증 결과 (요약)
| 배치 | 카드 | 사실 불일치 | 수정 | stance 변경 |
|---|---|---|---|---|
| B1 (rpt_07) | 7 | 0 | 3 | 0 |
| B2 (rpt_04, 10) | 10 | 0 | 3 | 0 |
| B3 (rpt_20, 23) | 6 | 5 | 7 | 1 (B023 below) |
| B4 (rpt_05, 08) | 8 | 0 | 3 | 0 |
| B5 (rpt_11, 15) | 10 | 3 | 4 | 0 |
| B6_pilot (rpt_014) | 2 | 0 | 4 | 0 |
| B6_steel_bank (rpt_12, 13) | 4 | 0 | 6 | 0 |
| B7 (rpt_02, 06, 09, 21) | 8 | 1 | 2 | 0 |
| B8 (rpt_16, 22, 25) | 6 | 0 | 2 | 1 (B077 below) |
| B9 (rpt_17, 18, 24, 29) | 6 | 0 | 2 | 0 |
| B10 (rpt_26, 27, 28) | 4 | 1 | 4 | 0 |
| **합계** | **71** | **10** | **40** | **2** |

### 처리된 리포트 (26/29)
B1 rpt_07 · B2 rpt_04 rpt_10 · B3 rpt_20 rpt_23 · B4 rpt_05 rpt_08 · B5 rpt_11 rpt_15 · B6 rpt_014 rpt_12 rpt_13 · B7 rpt_02 rpt_06 rpt_09 rpt_21 · B8 rpt_16 rpt_22 rpt_25 · B9 rpt_17 rpt_18 rpt_24 rpt_29 · B10 rpt_26 rpt_27 rpt_28

### 미처리 리포트 (3건)
- **rpt_01** — 유진 데일리(로봇/방산/조선). B7 배치엔 들어 있는데 카드 0장.
- **rpt_03** — IBK 데일리(인터넷/게임). B8 배치에 들어 있는데 카드 0장.
- **rpt_19** — 하나 SCV(지방선거 공약). B10 배치에 들어 있는데 카드 0장.

## 카드·함수 파일 인벤토리 (11 카드 / 11 함수 파일)

| 배치 | 카드 파일 | 카드 | 함수 파일 | 함수 | 함수 ID 영역 | 커버 리포트 |
|---|---|---|---|---|---|---|
| B1 | `B1_semicap.jsonl` | 7 | `B1_semicap.functions.jsonl` | 7 | F45-B1-01~07 | rpt_07 |
| B2 | `B2_energy.jsonl` | 10 | `B2_energy.functions.jsonl` | 9 | F45-B2-01~09 | rpt_04, rpt_10 |
| B3 | `B3_kenergy.jsonl` | 6 | `B3_kenergy.functions.jsonl` | 6 | F45-B3-01~06 | rpt_20, rpt_23 |
| B4 | `B4_auto.jsonl` | 8 | `B4_auto.functions.jsonl` | 8 | F45-B4-01~08 | rpt_05, rpt_08 |
| B5 | `B5_memory.jsonl` | 10 | `B5_memory.functions.jsonl` | 10 | F45-B5-01~10 | rpt_11, rpt_15 |
| B6 | `B6_pilot.jsonl` | 2 | `B6_pilot.functions.jsonl` | 2 | F045, F046 (기존) | rpt_014 |
| B6 | `B6_steel_bank.jsonl` | 4 | `B6_steel_bank.functions.jsonl` | 4 | F45-B6S-01~04 | rpt_12, rpt_13 |
| B7 | `B7_robot_def.jsonl` | 8 | `B7_robot_def.functions.jsonl` | 8 | F45-B7-01~08 | rpt_02, rpt_06, rpt_09, rpt_21 |
| B8 | `B8_internet_ent_food.jsonl` | 6 | `B8_internet_ent_food.functions.jsonl` | 4 | F093~F096 (기존) | rpt_16, rpt_22, rpt_25 |
| B9 | `B9_power_telecom_ship.jsonl` | 6 | `B9_power_telecom_ship.functions.jsonl` | 5 | F099~F103 (기존) | rpt_17, rpt_18, rpt_24, rpt_29 |
| B10 | `B10_construction_materials.jsonl` | 4 | `B10_construction_materials.functions.jsonl` | 3 | F105~F107 (기존) | rpt_26, rpt_27, rpt_28 |

**합계: 71 카드 / 66 함수 / 26개 리포트 커버.**
- 신규(Phase 1 추출, 임시 ID `F45-Bx-NN`): 52개 (B1·B2·B3·B4·B5·B6_steel_bank·B7)
- 기존(1차 합성 잔존): 14개 (B6_pilot·B8·B9·B10) — function_id가 F045/F046/F093~F107로 점프하는 상태, Phase 4에서 통일 재할당 예정

## 알려진 문제

### 1. 사고함수 파일 일부 손실 (B1~B5, B7)
중복 정리 시 verbose명 파일을 삭제했는데, 해당 배치의 함수 파일은 verbose 패스에서만 생성됐었음. 배치명 패스는 카드만 생성하고 함수는 추출하지 않았기 때문에 **B1·B2·B3·B4·B5·B7의 함수 후보(원래 16개)가 사라짐.** 정본 카드(배치명)는 그대로 있으므로 함수는 카드에서 재추출 가능.

### 2. 미처리 리포트 (3건)
- **rpt_01** — 유진 데일리(로봇/방산/조선). B7 배치엔 들어 있는데 카드 0장.
- **rpt_03** — IBK 데일리(인터넷/게임). B8 배치에 들어 있는데 카드 0장.
- **rpt_19** — 하나 SCV(지방선거 공약). B10 배치에 들어 있는데 카드 0장.

### 3. 입력 번호 오타
`rpt_014.txt` 만 3자리(다른 건 2자리). 정렬·매칭 시 사고 가능. 의도라면 그대로 두되 다음 합성 때 `rpt_14`로 정규화 고려.

## 실행법

### 신규 리포트 투입
방식 A — 채팅 붙여넣기: 메인이 `data/inputs/rpt_NNN.txt`로 저장.
방식 B — 파일 투입: PDF는 `reports/`에 두고 PDF Tools MCP로 텍스트 추출 → `data/inputs/`.

### 파이프라인 5단계 (HANDOFF_BROKER.md §4)
```
1. ingest       리포트 → data/inputs/*.txt              [완료, 29건]
2. prepare      data/batches/<batch>.jsonl 생성         [완료, 11배치]
3. synth        subagent 호출, prompts/broker_reverse_distill.md
                                                        [부분완료, 26/29건, 일부 중복]
4. audit        템플릿 검출 + 명제 누락 + 차별화 확인   [미실행]
5. consolidate  data/all_cards.jsonl + .md + _stats.md  [미실행]
```

### 다음 액션 (이 PLAY 마무리하려면)
우선순위:
1. ~~중복 정리~~ — **완료(2026-05-27).** verbose명 파일 삭제, 배치명 정본화.
2. ~~카드 검증·업그레이드~~ — **완료(2026-05-27).** 11배치 전수, 사실 10건 수정, stance 2건 변경.
3. ~~R5 Phase 1 (B1~B5/B6_steel_bank/B7 함수 추출)~~ — **완료(2026-05-27).** 52 신규 함수, 시점 종속 고유명사 0건 통과.
4. **백업 정리** — `*.jsonl.bak` 12개. 검증 결과 안정적이면 일괄 삭제.
5. **R5 Phase 2: 클러스터링** — 66 함수 후보 전체에서 비슷한 사고 패턴 묶기. `source_card_count ≥ 2` 충족 함수만 정식 등재, 나머지는 후보 보관 + `ACT_FUNCTION_REDESIGN_CANDIDATE` 액션 부여.
6. **R5 Phase 3: R6 매핑** — `data_sources` / `indicators` / `action_at_trigger` / `indicators_examples_specific` 4+1 필드 추가 (PLAY13 `data/r6_*.json` 카탈로그 참조).
7. **R5 Phase 4: PLAY13 R5 v3 → v4 통합** — function_id 재할당(F45~), 자가 검수(금지 패턴 7개 위반·고유명사 0건), `r5_thinking_functions.json` v4 산출.
8. **누락 3건(rpt_01, rpt_03, rpt_19) 추가 합성.**
9. **audit + consolidate** 실행 → `all_cards.jsonl`/`.md`/`_stats.md` 생성.

## 입력 / 출력
- **입력:** 증권사 리포트 본문(txt 또는 붙여넣기). 메타(broker/analyst/date/target/report_type)는 알면 같이, 모르면 메인이 본문에서 추출.
- **출력:** `data/cards/*.jsonl`(카드 26필드) + `data/cards/*.functions.jsonl`(신규 사고 함수 후보). 사람용 `.md`와 통합본은 consolidate 단계에서 생성 예정.

## 가정 & 제약
- **리포트 본문 끝까지 읽기 — 페이지 임의 컷 절대 금지.** (사용자 강조 룰 1)
- **명제 하나하나 분리** — fact / interpretation / inference / forecast 라벨링, 결론 한 줄 압축 금지. (사용자 강조 룰 2)
- 카드 ID는 `B001~`, 신규 함수 ID는 `F045~`. PLAY13/28의 E시리즈·F001~F044와 충돌 금지.
- **차별화 지점(컨센 대비 stance) 없는 리포트는 억지 카드화 금지** — 스킵하고 사유 보고.
- 기존 R5 함수 매칭은 `../PLAY13_insight_distill/data/r5_thinking_functions.json` 참조. 매칭 60% + source_card_count ≥ 2 일 때만 정식 함수 승격.
- **디스패치 45초 제약:** 리포트 1개 분해는 Agent 1회로 충분하지만, 다건 병렬은 카드 ID 영역을 사전 할당해야 충돌 없음(HANDOFF §5). → 이번 1차 합성에서 이 룰이 깨져 위 "이중 세트" 문제 발생한 것으로 추정.

## 변경 이력
- 2026-05-27 — 최초 생성. PLAY29 설계 자산 이관 + 명칭 PLAY31로 갱신. 리포트 투입 대기 상태.
- 2026-05-27 — 1차 합성 실행. 29건 투입, 11배치 분배, 26/29 카드 합성 완료(99 카드 라인 / 31 함수 라인). 단, **카드 파일 이중 세트 + ID 충돌, rpt_01/03/19 누락, consolidate 미실행** 상태로 종료. README는 동기화됨.
- 2026-05-27 — 중복 정리. verbose명 파일 14개 삭제 (B1_semicap_equip, B2_energy_chem, B3_kenergy_oil, B4_autos, B5_semi_memory, B6_steel, B7_robot_defense_ship의 `.jsonl`/`.functions.jsonl`). 정본은 배치명 파일로 통일. 결과 **71 카드 / 14 함수**. 부작용: B1·B2·B3·B4·B5·B7의 함수 후보 16개 손실(verbose 패스에서만 생성됐기 때문) — 카드에서 재추출 필요.
- 2026-05-27 — 검증·업그레이드 라운드. 11배치 전수 Agent 위임으로 원문 사실관계 대조 + 차별화 지점(stance) 강화. 사실 불일치 10건 수정(단위 1000배 오류 1건/10배 오류 1건/지분 주체 오기 1건/실적 변동성 시점 혼동 1건 포함), 총 40건 보강, stance 2건 below로 정정(B023·B077). 백업 12개 동거(`*.jsonl.bak`).
- 2026-05-27 — B6_steel_bank R5 사고함수 4개 추출 (`F45-B6S-01~04`). 클러스터링 없이 1카드:1함수 보존. 시점 종속 고유명사 0건 자가검수 통과 (회사·정책명·인물·국가·날짜 일반화 완료).
- 2026-05-27 — **R5 Phase 1 라운드 완료.** B1·B2·B3·B4·B5·B7 6배치 Agent 위임으로 시점 독립 사고함수 후보 추출. B1 7개 / B2 9개(B016+B018 1건 클러스터) / B3 6개 / B4 8개 / B5 10개 / B7 8개 = **신규 48개 (+ B6_steel_bank 4개) = Phase 1 합계 52개**. 전 배치 자가검수 통과(회사명·제품명·세대명·연도·국가별 정책명 0건). function_id 임시 `F45-Bx-NN` 형식, Phase 4 통합 시 R5 v3 F44 다음으로 재할당 예정. 카드 본체 무변경 확인.
