# PLAY28_insight_distill_v2

> **PLAY13_insight_distill의 v2 (incremental 업데이트 레이어)**
> 2026-05-27 시작. PLAY13의 자산(r4/r5/r6/r8 64장 카드 + 44함수 + 카탈로그 + 13산업 매핑)을 그대로 복사하고, **채널에 새로 올라온 영상**과 **자막 있는데 R4 미사용 영상**을 추출하는 `scripts/discover_new_videos.py`를 추가했다. PLAY13는 박제 보관용, PLAY28에서 신규 영상만 점진 누적.

## 목적
HAN_LAB의 1,060개 propositions를 80~120장 "사고회로 카드"로 농축해 RAG 코퍼스로 만든다. 나중에 AI(=Claude)가 뉴스를 받았을 때 비슷한 상황의 카드를 검색해서 4명 화자의 사고 회로를 빌릴 수 있게.

## v2 신규 — incremental 업데이트

**핵심 원칙: "과거에 한 거 또 하지 않는다."**

R4가 batch input으로 *입력 받은 적 있는* 영상은 카드 채택 여부와 무관하게 "이미 본 영상"이다. R4가 잡담 토크쇼라서 카드 채택 안 한 영상이라도 다시 돌리면 같은 결과 (HANDOFF §9.2). 따라서 default 출력은 **R4 batch input에 들어가지도 않은 영상**만 포함한다.

```
[discover_new_videos]  list.txt × r4_inputs/ × r4_all_cards × transcripts 4겹 diff
       ↓
data/missing_videos.jsonl   (1줄=1영상, reason 분류)
       ↓
(다음 라운드 R4) — Agent 호출 입력으로 사용
```

**스크립트:**
- `scripts/discover_new_videos.py` — 신규 영상 발견기 (4겹 diff, default는 미입력 영상만)
- `scripts/_channel_fetch.py` — HAN_LAB `channel_fetch.py` 복사본 (PLAY 독립)

**사용:**
```powershell
cd PLAY28_insight_distill_v2

# 5채널 전체 fetch + 진짜 안 본 영상만 (default --limit 30 영상/채널, ~75초)
python scripts/discover_new_videos.py

# 외부 fetch 생략 — list.txt만 비교
python scripts/discover_new_videos.py --no-fetch

# 특정 채널만 (한국어 채널명, list.txt 헤더와 정확히 일치)
python scripts/discover_new_videos.py --channels 머니코믹스,김단테 월가아재

# R4가 봤지만 카드 채택 안 한 영상도 포함 (재호출 낭비 위험, 디버그용)
python scripts/discover_new_videos.py --include-seen

# stats만 보기
python scripts/discover_new_videos.py --dry-run
```

**출력 (`data/missing_videos.jsonl`) 스키마:**
```json
{"video_id": "xxx11", "channel": "머니코믹스", "url": "https://...",
 "reason": "new_after_baseline", "has_transcript": false, "detected_at": "2026-05-27"}
```

**reason 분류:**
| reason | 정의 | default 포함 |
|---|---|---|
| `new_after_baseline` | fetch에서 *마지막 baseline 영상 인덱스 이내*의 미등록 (= baseline 작성 후 새로 올라온 진짜 신규). 인덱스 그 이후 미등록은 baseline 작성 시점 limit cap에 잘린 옛 영상이라 발굴 제외 | ✅ |
| `r4_unseen` | list.txt 등록됐지만 r4_inputs/ batch input 어느 것에도 안 들어감 | ✅ |
| `r4_seen_not_carded` | r4_inputs/에 들어갔지만 r4_all_cards source_videos에 없음 (R4가 봤지만 카드 채택 안 함) | ⛔ `--include-seen` 필요 |

**현재 PLAY13 자산 기준 stats (2026-05-27):**
- list.txt 80영상 = r4_inputs 80영상 → `r4_unseen = 0`
- r4_inputs 80 - r4_source 59 = `r4_seen_not_carded = 21` (default 출력에서 제외됨)
- 즉 PLAY28의 missing_videos.jsonl 가치는 거의 전부 **`new_after_baseline`(시간 흐름 누적)**에서 나온다.

**의존:** yt-dlp (이미 HAN_LAB venv에 설치돼 있음). 채널 핸들 직매칭 실패 시 `_resolve_via_search` 폴백 (검색 1건 → 채널 ID 역추출) 자동 동작.

## (이하 PLAY13 원본 내용)


## 데이터 흐름
```
HAN_LAB/.../propositions.jsonl  (1,060건)
    ↓ s1_filter.py            (룰 기반 노이즈 컷, LLM 없음)
data/s1_clean.jsonl           (~400건 예상)
    ↓ s2_cluster.py           (ollama 임베딩 + HDBSCAN/KMeans)
data/s2_clusters.jsonl        (~40 클러스터)
    ↓ s3_synthesize.py        (ollama로 클러스터 → 카드 1장씩 합성)
data/s3_cards.jsonl           (80~120장, 메인 산출물)
data/s3_cards.md              (사람용 요약)
    ↓ s4_embed_cards.py       (카드 search_blurb 임베딩)
data/embeddings.npy + card_index.jsonl
    ↓ query.py                (데모: 뉴스 문장 → top-k 카드)
```

각 stage는 독립 실행 가능. 산출물이 다음 stage의 입력. 중간에 결과 보고 룰/프롬프트 튜닝.

## 실행법
```powershell
# 0. 의존성 (S1만 쓸 거면 표준 라이브러리로 충분)
# S2~S4는 ollama + numpy 필요
pip install numpy

# ollama (S2 이후)
# bge-m3 (한국어 임베딩) 또는 nomic-embed-text 권장
ollama pull bge-m3
ollama serve  # 별도 창

# 1. S1: 노이즈 컷
python s1_filter.py

# 2. S2: 임베딩 + 클러스터 (TODO)
# 3. S3: 카드 합성 (TODO)
# 4. S4: 검색 인덱스 (TODO)
```

## 입력 / 출력
- **입력:** `C:/Users/fivep/OneDrive/Desktop/HAN_LAB/experiments/insight_pipeline/data/propositions.jsonl` (절대경로 고정)
- **S1 출력:** `data/s1_clean.jsonl` + 콘솔 통계 (입력/출력 건수, 제거 이유별 카운트)
- **최종 출력 (S3/S4):** 80~120장 카드. 카드 스키마는 아래 참조.

## 카드 스키마 (S3 산출물)
```jsonc
{
  "card_id": "C0007",
  "title": "고용·물가 강세 → 연준 금리 동결 기대",
  "trigger_conditions": ["미국 고용 지표 강세", "에너지 가격 상승"],
  "speakers_view": {
    "오선의 미국 증시 라이프": "연말까지 금리 동결 전망에 무게",
    "김단테 월가아재": "동결 + 점도표가 시장 충격 트리거 가능"
  },
  "causal_chain": "[고용 강세 + 에너지↑] → [인플레 끈적] → [연준 동결]",
  "expected_direction": "neutral_to_bearish_short",
  "time_horizon": "short",
  "confidence_meta": "medium — 화자 2명 일치, 근거 public_fact 1건",
  "source_propositions": ["P0123", "P0456"],
  "search_blurb": "고용 강세 에너지 가격 상승 연준 금리 동결 점도표 단기 변동성"
}
```

## 가정 & 제약

1. **S1은 룰 기반.** LLM 없이 통과시킬 명제 결정. `is_promotional`/`is_meta_remark`/광고타입 제거, 인과·예측·조건부예측·사실 진술 중 적어도 1개 라벨 있어야 통과, proposition 길이 < 15자 컷, raw_quote↔proposition jaccard ≥ 0.85면 동어반복으로 컷. **실측: 958/1060 통과 (90%)**. 예상(30~40%)과 크게 다름 — 룰이 잡는 노이즈(광고/메타/유형불명)는 1차 라벨링 단계에서 이미 잘 분리돼 있었고, "의미 빈약" 명제는 룰로 안 잡힘. 다음 stage(임베딩 클러스터링)에서 작은 클러스터로 빠질 거란 가설.

2. **시간축 정보 없음.** propositions에는 영상 게시일이 없다. 따라서 "이 카드가 언제 시점의 사고인가"는 일단 모름. 향후 youtube_whisper 메타로 보강 예정 (현 PLAY 범위 밖).

3. **카드 80~120장 목표.** S2 클러스터 30~50개로 잡고, 큰 클러스터는 2~3 카드로 분할, 작은 클러스터는 묶어서 1 카드. 정확한 수는 S2 결과 보고 조정.

4. **화자 보존.** `speakers_view`는 화자 4명 모두 익명화하지 않는다. 4명뿐이라 일반화 위험보다 "누구 시선인가" 정보 가치가 큼.

5. **LLM은 ollama만.** 사용자 메모리 룰. S3 합성·S4 임베딩 전부 로컬. S3는 카드 1장당 1회 호출이라 100회 ≈ 수십 분 예상 — long_running 패턴 따름.

6. **검증 안 한 부분**: S1의 동어반복 jaccard 임계 0.85가 적절한지 미검증. S1 결과 본 후 조정.

## 변경 이력
- 2026-05-18 — 최초 생성. README + S1 룰 필터.
- 2026-05-18 — S1 실측 결과 반영. 통과 958/1060 (90%). 룰만으론 의미 빈약 명제 못 잡음 — S2에서 흡수 예정.
- 2026-05-18 — 파이프라인 변경: S2(임베딩+클러스터)를 Claude 기반 토픽 라벨링(R1)으로 대체. ollama 임베딩 단계 제거. R1 완료: 25개 라벨 사전 + 958건 라벨링. noise 0건 (인색 원칙). 채널별 성격이 라벨 분포에 그대로 드러남.
- 2026-05-18 — R1은 실제로는 키워드 매칭 룰 기반(`scripts/r1_label.py`)으로 처리됨 — Read 도구 25K 토큰 출력 한도 때문에 Agent가 명제 본문을 다 못 읽고 우회. R2에서 의미 이해 보정하기로 결정.
- 2026-05-18 — R2a 매크로 영역 완료. 4 호출로 분할(oil / us_equity+emerging / fed+inflation+employment / china+korea). 카드 16장 (C001~C016). 각 호출은 일반화 프롬프트 `prompts/r2_card_synthesis.md`와 사전 분할된 라벨별 입력 파일(`data/r2a_macro_by_label/`) 사용. R1 노이즈는 R2에서 의미 이해로 자연 제외됨(특히 emerging_markets의 머니코믹스 잡담 45%).
- 2026-05-18 — R2b/c/d 7개 호출 병렬 처리. 카드 31장 추가 (C017~C047). 전체 카드 47장. ID 충돌 없음 (영역 예약 방식 성공).
- 2026-05-18 — R3-A 통합 완료. `r2_all_cards.jsonl` (47장) + 사람용 md 요약 + 메타 통계. 검수 이슈 0건. 단일 화자 51%, 2명 카드 47%, 4명 카드 1장(C044). direction에 mixed 11장 — 화자 시각 차이 보존 잘 됨. source 중복 명제 81건 — cross-reference 시드로 활용 가능.
- 2026-05-18 — **편향 발견**: R2 47장이 80영상 중 18영상에서만 도출됨(활용률 22%). extract_status.jsonl 보니 1601 청크 중 202개(12.6%)만 ollama gemma2 처리, 나머지 중단. 지식부장관 채널 16영상 전부 누락.
- 2026-05-18 — **R0 자막→카드 직접 합성 라운드 추가**. propositions 단계 우회. 6 Agent 병렬(머니그라피 4+4+8 / 머니코믹스 16 / 김단테+오선 24 / 지식부장관 16). 신규 카드 40장 (D001~D040). 의외 발견: 머니그라피 큰 영상 4개 중 3개가 잡담 토크쇼(연애상담/책토크), 지식부장관이 매크로/지정학 해설 밀도 최고. R0 카드는 게스트 화자 다수 등장(백찬규/유정수/남세동/이재용/김민기). source_videos 필드 사용.
- 2026-05-18 — R3-A 재실행. C+D 통합 87장. 검수 이슈 0건. direction mixed 17장, confidence high 12장 (R0가 데이터 강한 카드 7장 추가). 화자 3명 카드 3장 신규 (cross-cluster).
- 2026-05-18 — **R4 인수인계 작성** (`HANDOFF_R4.md`). 사용자가 외부에서 만든 `data/reverse_distillation_cards.json`의 핵심 4개 필드(attention_hook/implicit_question/reasoning_move/matched_thinking_pattern)가 자동 템플릿이라 판명. 자막 원본부터 다시 → Agent 5~6 병렬 → 진짜 사고 경로 카드 80~120장(E001~) 목표. 다음 세션은 `HANDOFF_R4.md` 정독 후 R4-prep부터 시작.
- 2026-05-18 — **R4-prep + R4-prompt 완료**. `scripts/prepare_r4_inputs.py` (R0 분할 정책 그대로, 출력 `data/r4_inputs/`) 작성·실행. 80영상 471K 토큰을 A1~A6 batch로 분할, 카드 ID 영역 E001~E066 사전 할당. `prompts/r4_reverse_distill.md` 작성 — R0 프롬프트 기반 + R4 핵심(4필드 자유 합성·금지 패턴 7개·자가 검수·framework 사전 16개+카드별 차별화·26필드 스키마·insight_quality 자체 평가). 자동 템플릿 실물 C001/C002에서 확인.
- 2026-05-18 — **R4 9 Agent 병렬 호출 완료**. 분할안 6→9개로 사용자 변경(채널/화자 경계 존중, 컨텍스트 부담↓). A1~A6b 9 Agent 동시 호출 → 카드 64장 (E001~E065, E032/E066 빈자리). A1 E002 JSON 줄바꿈 깨짐 1건 발견 → join 패치. R4 본질(raw_quote 기반 진짜 사고 경로)이 9 Agent 모두 보고 샘플에서 확인.
- 2026-05-18 — **R4-audit + R4-consolidate 완료**. `scripts/r4_audit_templates.py` — 금지 패턴 7개 정규식 + reverse_distillation_cards.json의 framework 사전 16개 완전일치 검사. **64장 전수 위반 0건 ✅**. `scripts/r4_consolidate.py` → `r4_all_cards.jsonl` (276KB) + `r4_all_cards.md` (사람용, 카드별 4 핵심 필드 풀) + `r4_all_stats.md` (메타 통계). 평균 7.14/10, high 21장·medium 43장. framework top5: regime_shift 12·platform_shift 10·decoupling 5·adoption_curve 5·second_order_effect 5. 단일 화자 44장, video_id 중복 18개. 검수 이슈 0건.
- 2026-05-18 — **medium 43장 애널리스트 페르소나 업그레이드 완료**. `data/r4_backup_20260518/` 백업 후 진행. 메인이 E010/E029 시범 2장 직접(`scripts/r4_upgrade_samples.py`) → 패턴 정립 → 5 Agent(U1~U5) 병렬로 41장 분담 처리. **신규 6 필드**(consensus_gap·bull_case·bear_case·monitoring_signals·analyst_view·cross_reference_cards) 추가, implicit_question을 함수 수준(시점·임계·형태)으로 정밀화, causal_chain 4~5단계 확장. 기존 4 핵심 필드의 raw_quote 진정성 보존. audit 재통과(위반 0). **평균 7.14→8.00, grade=high 64/64장**(medium 0). jsonl 276KB→426KB. direction에 conditional 계열 27장(/64). 다음: R5(임베딩+RAG / 실제 뉴스 적용 테스트).
- 2026-05-18 — **R5-X 사고 함수 추상화 레이어 생성**. R4 카드가 *사건 paraphrase + 사고 함수* 한 묶음이라 시점 종속(2개월 뒤 호르무즈 5장 outdated). matched_thinking_pattern + reasoning_move + implicit_question 함수 부분만 추출해 시점 독립 사고 함수 라이브러리 합성. 출력 `data/r5_thinking_functions.json` — **44개 함수** (시드 12개 → 정밀화·확장·단일카드 보존). 11필드 스키마: function_id·name·abstract_form·trigger_when·verification_questions·anti_signal·source_cards·source_card_count·framework_resonance·applies_to_domain·example_application·related_functions. **카드 커버리지 64/64장**, 평균 1.27 함수/카드, 단일 카드 함수 24개(강제 클러스터링 거부 원칙). 자가 검수: 금지 패턴 7개 위반 0건, 핵심 필드(name/abstract_form/trigger_when)에 시점 종속 고유명사(트럼프·호르무즈·시트리니·이란·터키·이집트 등) 0건. example_application은 R4 카드에 *없는* 외부 도메인 적용 예시로 시점 독립 증명.
- 2026-05-18 — **R6 Agent C1: 데이터 소스 카탈로그 박제**. 출력 `data/r6_data_sources.json` (mvp 동기 사본). **34 sources** — mvp_internal 10 / external_free 12 / external_paid 5 / websearch_pattern 7. 12필드 스키마: source_id·name·category·access_method·endpoint_url·auth_required·data_format·update_frequency·typical_use·linked_indicators·cost·limitations·related_R4_cards·related_R5_functions. mvp_internal top R5 cross-ref: NEWS_ALERT_DB(F=8)·MODULE_DISCLOSURE(6)·VALUATION(6)·EMBEDDING(6)·SCENARIO_DB(6). external_paid 5건은 endpoint_url=null + "접근 가정 없음" 명시 (WebSearch 우회).
- 2026-05-18 — **R6 Agent C2: KPI 카탈로그 박제**. R4 64장 monitoring_signals/bull/bear/triggers/keep_as_fact + R5 44함수 verification_questions에서 *실제 등장하는* 정량 지표를 표준화. 출력 `data/r6_indicators.json` (mvp/research_Mvp/insight_corpus/r6_indicators.json 동기 사본). **61개 KPI** — macro 12, industry_supply_chain 15, company_financial 18, market_sentiment 8, policy_regulation 8. 12필드 스키마: indicator_id·name·category·formula·unit·frequency·thresholds·threshold_rationale·data_sources·interpretation_direction·related_R4_cards·related_R5_functions(+anti_signal_note). thresholds는 R4 본문 실제 수치(92%·1.19조·1,900억·18거래일 등)만 사용, 임의 임계 0건. 정보 공백 KPI 2개(임계 빈 객체 + 수동 보강 메모). 빈도 top R4: E045·E050·E051·E024·E027 / top R5: F28·F08·F24·F02·F23. data_sources는 Agent C1 예상 ID(`DS_DART_QUARTERLY` 등) placeholder — R5 cross-ref 단계에서 정합.
- 2026-05-18 — **R6 Agent C3: 액션 템플릿 카탈로그 박제**. 출력 `data/r6_action_templates.json` (mvp 동기 사본). **22 액션** — watch 4·warn 5·critical 4·cross_ref 5·backtest 4. 12필드 스키마: action_id·name·severity·category·trigger_condition_pattern·executable_steps·expected_output·tooling·user_action_required·applicable_R5_functions·applicable_to_severity·anti_pattern. user_action_required=false 18개(82%, autonomous 적합) / true 4개(WATCHLIST_ADD·USER_DISPATCH·NEW_THESIS_TRIGGER·FUNCTION_REDESIGN). **매수/매도/비중 권유 단어 grep 0건** (R4 핵심 원칙 계승, "관망/추적/확인/재검증"으로만). executable_steps는 mvp CLI 호출 형태(`python -m module_disclosure $code --days 90` 등)로 추상 표현 0.
- 2026-05-18 — **R6 Phase B: R5 v1→v2 실행 가능 layer 합성**. `scripts/r6_phase_b_apply.py`로 44함수에 4 신규 필드(`data_sources`/`indicators`/`action_at_trigger`/`backtest_log`) 추가, 기존 11필드 1자도 변경 안 함. 매핑: r6_data_sources의 `related_R5_functions` 역방향 + 도메인 fallback(F17/F36/F39/F40/F41/F42 등 카탈로그 미커버 함수용), r6_indicators 동일 룰, action은 severity 5단계 공통+macro/regime_shift/single-card 분기. 카탈로그 ID cross-ref 검증 **위반 0건**. 출력 `data/r5_thinking_functions.json` v2 (73KB→133KB) 및 mvp/research_Mvp/insight_corpus 동기 사본. 단일 카드 함수 24개 모두 backtest에 `ACT_FUNCTION_REDESIGN_CANDIDATE` 추가. DS top: NEWS_ALERT_DB 15·CONSUMER_TRENDS 10·KOSTAT 8·DISCLOSURE 8·VALUATION 8. IND top: KOLMAR/REZONING/30S_ACCOUNTS 각 4. 액션 빈도: ACT_WATCHLIST_ADD/MONITORING_SIGNAL/T2_PROMOTION/WEBSEARCH_AUTO_QUERY/TELEGRAM_ALERT 등 공통 액션 44/44.
- 2026-05-19 — **R7-B Agent 2: R5 44함수 indicators 필드 Tier 1 재매핑 완료**. 진단: F03/F06 등 카드 source가 한국콜마/세븐스타즈 등 *case_specific* 사례 KPI에 종속돼 외부 도메인(예: AI 코딩 스타트업) 적용 시 무용. 처리: 기존 14필드 동결 + `indicators` 필드만 갱신(case_specific 71건 → 그 abstract_parent로 승격) + `indicators_examples_specific` 신규 필드로 case_specific 71건 모두 보존 분리. 메타 v2→v3, schema_change → schema_change_history 리스트화. 빈약 함수(<=2 Tier1) 18개를 도메인 매칭 abstract KPI로 보강(28건 추가). 결과: avg 2.70 Tier1/func, min 2, max 5 / 37/44 함수가 examples_specific 보유. 검증: orphan 0·case_specific leak in indicators 0·indicators↔examples_specific 중복 0·전 ID r6 v2 실재. 출력 `data/r5_thinking_functions.json` v3 (143KB) + mvp/research_Mvp/insight_corpus 동기. F03 예: indicators=[TOP_N_CUSTOMER_CONCENTRATION·DOMAIN_EXPORT_YOY·LAND_USE_POLICY_DESIGNATION_COUNT] / examples_specific=[KOLMAR_CLIENT_CONCENTRATION·KOREA_COSMETICS_EXPORT_YOY·SEOUL_REZONING_DESIGNATION]. F05 예: indicators=[BILATERAL_STRATEGIC_AGREEMENT_PROGRESS·SOURCE_REGION_DEPENDENCY_RATIO·SOURCE_DIVERSIFICATION_FLOW] / examples_specific=[US_UAE_SECURITY_MOU]. 외부 도메인 적용성 회복.
- 2026-05-18 — **R6 전체 통합 검증 통과**. 5개 파일(r4_all_cards.jsonl·r5_thinking_functions.json v2·r6_data_sources.json·r6_indicators.json·r6_action_templates.json) 무결성·byte 동기 OK. (a) r4_all_cards 백업과 byte-identical (변질 0). (b) r5 v2 카탈로그 ID cross-ref 위반 0건 (34 DS·61 IND·22 ACT 모두 실재 ID). (c) R4 자동 템플릿 금지 패턴 7개를 r5 v2에도 grep — 0건 (revival 방지). (d) PLAY13 master ↔ mvp/insight_corpus 동기 5/5 OK. (e) 단일 카드 함수 24/24 backtest에 ACT_FUNCTION_REDESIGN_CANDIDATE 추가. (f) r5.source_cards orphan 0 (모두 r4에 실재). 백업 `data/backup_pre_r6_20260518_2337/`.
- 2026-05-19 — **R8: 산업별 R5/R6 자산 매핑표 박제 완료**. 출력 `data/r6_industry_function_map.json` (112KB) + mvp/research_Mvp/insight_corpus 동기 사본. **13개 산업** (POWER_INFRA·DEFENSE·SEMICONDUCTOR_AI·BIOTECH·SHIPBUILDING_SHIPPING·AUTOMOTIVE_EV·CONSUMER_K_BRAND·GAME_CONTENT·ENERGY_COMMODITIES·FINANCE_BANK·REAL_ESTATE_CONSTRUCTION·MACRO_GLOBAL·PLATFORM_INTERNET) — 각 산업당 ranked_functions(평균 7.0), priority_indicators(평균 6.46), recommended_action_chain(4~6 step), first_questions(5~8), anti_signals_to_watch(3~5), industry_specific_r4_cards(6~15장). 한국 KOSPI relevance: high 8 / medium 5. industry_threshold_override 6/84 KPI(7.1%)에 적용 — 한국 맥락 미세조정. POWER_INFRA는 POWER_INFRA_REPORT_PROTOCOL.md §1 표(E024·E053·E048·E008·E060·E018·E036·E037·E038·E044·E057·E022·E027·E041·E051) 정확히 박제. first_questions는 함수 ID 인용(F08·F20 등)으로 사고 회로 trace 가능. 검증: r5_ids/r6_ind_ids/r6_act_ids/r4_ids cross-ref orphan **0건**. 데이터 창작 0건(실재 ID + 실재 KOSPI 종목코드만). 산업 input → R5 함수 + R6 KPI/actions + R4 카드 자동 매핑 1차 사전 완성.
- 2026-05-27 — **medium 20장 애널리스트 페르소나 업그레이드 완료 (U1~U4 4 Agent 병렬)**. 1차 R4 라운드 패턴(`scripts/r4_upgrade_u1.py`) 그대로 적용. `data/r4_cards_new_backup_pre_upgrade/` 백업 후 진행. 분담: U1 지식부 4장 (E067/E069/E070/E073), U2 오선 6장 (E077~E082), U3 머니코믹스 5장 (E085/E087/E088/E089/E090, E086 보존), U4 김단테 5장 (E094/E095/E096/E098/E099, E092/E093/E097 보존). 신규 6 필드 추가 — consensus_gap·bull_case·bear_case·monitoring_signals(5~6개씩)·analyst_view·cross_reference_cards. implicit_question을 *시점·임계·형태* 함수로 정밀화, causal_chain 4~8단계 확장. 기존 4 핵심 필드 raw_quote 진정성 보존. 각 Agent가 자체 자가 검수(7 금지 패턴) 통과 + 재실행 스크립트 (`r4_upgrade_u1_jisikbu.py`, `r4_upgrade_u2.py`, `r4_upgrade_u3.py`, `r4_upgrade_u4.py`) 생성. **재검증 통과: 자동 템플릿 위반 0건 / 검수 이슈 0건 / 평균 7.21→8.03 / grade high 29/29 (medium 0)**. jsonl 140KB→242KB (1차 R4 276→426 비율과 유사 1.7배). 핵심 추가 발견: E099(호르무즈→채권 동조)에 김단테 F01 시그니처 후속 정식 적용 + E095 funding mix 시 자막에 머스크/테슬라 부재 정직 보고 + E073(필리핀 정치)를 2028 대선 후보 자격 함수 lead indicator로 재정의 + E079(시게이트 CapEx 거절)에서 발언 주체와 수혜 종목 분리 함수 도입.
- 2026-05-27 — **신규 28건 자막 다운로드 + R4 합성 + 검증 완료 (자율 모드)**. (1) HAN_LAB `pipeline.py` cuda+large-v3+ko로 28건 다운로드/전사. 전부 성공 28/28. (2) `prepare_r4_inputs_new.py` → A7~A10 4 batch 분할 (지식부 9 / 오선 8 / 머니코믹스 7 / 김단테 4). 카드 ID 영역 E067~E099 사전 할당. (3) Agent 4개 *병렬* 호출, `prompts/r4_reverse_distill.md` 그대로 사용. **카드 29장 생성** (A7: 9 / A8: 6 / A9: 6 / A10: 8). A9 머니코믹스에서 잡담·광고 2영상 스킵 (HANDOFF §9.2 패턴 그대로). (4) `r4_audit_templates_new.py` + `r4_consolidate_new.py` 자율 검증: **자동 템플릿 위반 0건 / 필수 필드 검수 이슈 0건**. 평균 7.21/10, grade high 9 + medium 20. framework top: regime_shift 4 / decoupling 4 / bottleneck 4 / multiple_rerating 3 / second_order_effect 3 / platform_shift 3 (1차 라운드와 분포 다름 — 신규 영상은 거시·기술 변화 위주). 김단테 시그니처 함수 F01(공식 narrative보다 깨질 조건의 물리적 구성으로 재평가)이 신규 4영상 중 3곳에 일관 적용 — 사고 패턴 안정성 확인. 신규 함수 후보 발견: E093(LTA·선급금=cyclical breaker, 계약 형식을 변수로 추가), E097(KV cache → NAND 가상메모리화, 기술 디테일로 인접 부품 수요 재구성). 산출물: `data/r4_new_cards.jsonl` (140KB), `r4_new_cards.md`, `r4_new_stats.md`, `r4_audit_new.md`. **기존 `r4_all_cards.jsonl` 변질 없음**. medium 20장 애널리스트 페르소나 업그레이드는 별도 라운드로 (1차 R4 라운드와 동일 패턴, 사용자 결정 후 진행).
- 2026-05-27 — **신규 영상 추출 로직 정밀화**. 1차 fetch(limit 50)에서 5채널이 *정확히 34건씩 균등*으로 잡혀 의심 → 머니코믹스 fetch top 50을 list.txt와 직접 대조한 결과: top 50에 baseline 16개가 인덱스 8~23번에 그대로 들어있고, 인덱스 1~7은 baseline 작성 *이후* 신규, 인덱스 24~50은 baseline 작성 *이전*의 옛 영상 (당시 _build_list.py가 limit=16에 cap). 즉 "baseline 미등록 = 신규"는 거짓이고, 옛 영상 27편씩이 노이즈로 섞이고 있었음. 로직 변경: fetch 결과에서 *마지막 baseline 영상 인덱스 이내*의 미등록만 `new_after_baseline`으로 추출 (핀 고정 영상 robust). reason 명칭 `new_in_channel` → `new_after_baseline`. 재실행 결과 28건 (지식부장관 9 / 오선 8 / 머니코믹스 7 / 김단테 4 / 머니그라피 0) — 채널 활동 빈도와 12일 누적에 맞는 자연 분포. 또한 채널 ID 캐시 `data/channel_ids.json` 추가 (한국어 핸들 404 → 검색 폴백 우회).
- 2026-05-27 — **PLAY28_insight_distill_v2 분기 생성**. PLAY13 전체 (자산 + 스크립트 + 프롬프트) 그대로 복사. 신규 `scripts/discover_new_videos.py` 추가: list.txt × r4_inputs/ × r4_all_cards × transcripts/ **4겹 diff**로 영상 분류. 초기 설계는 3겹(source_videos 기준)이었으나 사용자 지적("과거에 한 거 또 하면 안 됨")으로 r4_inputs/ 기준 재설계 — `r4_all_cards.source_videos`에 없어도 batch input엔 들어갔으면 "이미 본" 영상으로 간주 (잡담 토크쇼처럼 카드 채택 안 된 케이스 = 재호출 낭비). reason 3종: `new_in_channel`/`r4_unseen`/`r4_seen_not_carded` (마지막은 default 제외, `--include-seen` 필요). fetch 백엔드는 HAN_LAB `channel_fetch.py`를 `scripts/_channel_fetch.py`로 복사 (PLAY 독립). 초기 stats: list.txt 80 = r4_inputs 80 → `r4_unseen = 0` (PLAY13 완결성 확인됨). 자막은 80개 다 보유 (HANDOFF 시점 옛 정보 outdated). 머니코믹스 1채널 limit 30 테스트 시 `new_in_channel` 14건 발견 (5/18~5/27 9일 누적). 5채널 전체 fetch는 ~75초라 background 권장.
