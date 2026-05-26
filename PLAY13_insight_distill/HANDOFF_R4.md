# R4 인수인계 — 진짜 인사이트 역증류 라운드

> **다음 Claude Code 세션은 이 문서 + `README.md` + `data/인사이트_역증류_프로젝트_인수인계.md` 3개만 읽으면 R4 즉시 시작 가능.**
> 작성일: 2026-05-18

---

## TL;DR (30초)

- PLAY13는 5채널 80영상 자막 → 사용자가 "뉴스 받으면 RAG로 빌려 쓸 사고 회로 카드" 만드는 프로젝트
- 지금까지 카드 87장 (`r2_all_cards.jsonl` C001~C047 + D001~D040) 만듦
- 사용자가 외부에서 reverse distillation 메타 추가한 `reverse_distillation_cards.json`이 있는데 **핵심 4개 필드(attention_hook, implicit_question, reasoning_move, matched_thinking_pattern)가 자동 템플릿이라 가짜**
- **R4 = 자막 원본부터 다시 → Agent 5~6 병렬 → 진짜 사고 경로 카드 80~120장**

---

## 1. 프로젝트 본질 (반드시 이해할 것)

### 핵심 질문 (모든 작업의 출발점)
> **"이 뉴스에서 인사이트 좋은 사람이라면 무엇을 *이상하게* 봤을까?"**

### 원칙 (사용자 원본 인수인계 §핵심 원칙)
- 뉴스에 없는 사실 확정 금지
- 결론 복붙 금지
- 좋다/나쁘다 즉답 금지
- **원초 데이터 / 해석 / 추론 / 예측 분리**
- 추론은 조건부 + 반증 조건 함께
- **결론보다 사고 경로 저장**

### 본질 한 줄
"좋은 투자 의견 생성기"가 아니라 **"좋은 투자 의견이 *만들어지는 사고 경로* 저장소"**다.

---

## 2. 데이터 자산 (절대경로)

| 자료 | 경로 | 상태 |
|---|---|---|
| **자막 원본** (72개 .txt) | `C:\Users\fivep\OneDrive\Desktop\HAN_LAB\experiments\youtube_whisper\transcripts\` | 1.8MB, ~460K 토큰 |
| 채널 매핑 | `C:\Users\fivep\OneDrive\Desktop\HAN_LAB\experiments\youtube_whisper\list.txt` | video_id ↔ 채널명 |
| propositions (raw_quote 자료) | `C:\Users\fivep\OneDrive\Desktop\HAN_LAB\experiments\insight_pipeline\data\propositions.jsonl` | 1,060건, 단 18영상만 |
| 기존 R2 카드 (참고용) | `data\r2_all_cards.jsonl` | 87장 통합본 |
| 기존 reverse distillation (가짜 정본) | `data\reverse_distillation_cards.json` | 521KB, 자동 템플릿 판명 |
| 사용자 원본 인수인계 | `data\인사이트_역증류_프로젝트_인수인계.md` | **필독** |
| 품질 가이드 | `data\insight_storage_quality_guide.md` | 프레임 16개별 품질 테스트 + 핵심 질문 |
| 전력인프라 산업 프롬프트 예시 | `data\전력인프라_역증류_리서치_프롬프트.md` | R4 후속(R5) 산업 프롬프트 작성 참고 |

### 5채널 영상 분포 (자막 .txt 기준)
| 채널 | 영상 | 자막 KB | 추정 토큰 |
|---|---|---|---|
| 머니그라피 | 16 | 929 | ~232K (영상당 ~14K) |
| 머니코믹스 | 16 | 473 | ~118K |
| 김단테 월가아재 | 14 (16중 2 누락) | 213 | ~53K |
| 지식부장관 | 16 | 189 | ~47K |
| 오선의 미국 증시 라이프 | 10 (16중 6 누락) | 33 | ~8K |

**총 72영상 ~458K 토큰.** 영상별 batch로 나누면 Agent 컨텍스트 200K 안에 들어감.

---

## 3. 지금까지 무슨 일이 있었나 (Phase 1~4 요약)

### Phase 1: propositions → R2 카드 47장 (C001~C047)
- ollama gemma2로 자막 → 명제 추출 (HAN_LAB insight_pipeline). **단 1,601 청크 중 202개만 처리하고 중단** (한 청크당 127초)
- 그 18영상의 propositions를 영역별 Agent로 카드화 (R2a/b/c/d, 8 호출)
- 출력: `data/r2a_cards/`, `r2b_cards/`, `r2c_cards/`, `r2d_cards/`

### Phase 2: 자막 → R0 카드 40장 (D001~D040)
- 채널 편향 보정 (R2가 18영상 22% 활용에 그침)
- 자막 원본 → Claude Agent로 직접 카드 합성 (propositions 단계 우회)
- Agent 6 병렬 (머니그라피 4+4+8 / 머니코믹스 16 / 김단테+오선 24 / 지식부장관 16)
- 출력: `data/r0_cards/`

### Phase 3: R3-A 통합 → 87장 합본
- `data/r2_all_cards.jsonl` (193KB) + `r2_all_cards.md` (사람용) + `r2_all_stats.md`
- 검수 0건. direction mixed 17장 / confidence high 12장

### Phase 4: 외부 reverse distillation (가짜)
- 사용자가 별도 환경에서 87장 + reverse distillation 메타 필드 추가
- 출력: `data/reverse_distillation_cards.json` (87장 × 26필드)
- **진단 결과 핵심 4개 필드가 자동 템플릿** (§4 참조)

---

## 4. 진단: 왜 R4가 필요한가

### 자동 템플릿 4종 (모든 카드 공통)

`reverse_distillation_cards.json`의 카드 본문을 직접 보면 다음 패턴이 87장 모두에 동일하게 박혀 있다:

**(1) attention_hook**:
```
"'{X}'라는 표면 신호가 실제로는 '{Y}'로 이어지는 조건부 전이 신호인지 확인한다."
```
X, Y는 그냥 카드 `title`을 "→" 기준으로 split. 화자의 진짜 *의아함* 없음.

**(2) implicit_question**:
```
"왜 지금 '{X}'가 나타났고, 어떤 조건에서 '{Y}'로 확장되는가?"
```
또 title split.

**(3) reasoning_move**:
```
"원초 신호를 곧바로 호재/악재로 판정하지 않고, {framework} 프레임으로 1차 영향과 2차 수혜/피해 대상을 분리한다. 카드의 기존 사고 점프는 {causal_chain}이다."
```
causal_chain을 그대로 복붙. 진짜 사고 점프 없음.

**(4) matched_thinking_pattern**:
프레임당 고정 문장 (예: `regime_shift` = "자금 흐름·정책·산업 질서의 장기 레짐 전환 가능성을 보는 사고"). 카드별 차이 없음.

### 진짜 인사이트는 어디서 오나

화자의 raw_quote 안에 있다. C001 (이란 협상) 예시:

김단테 raw_quote (propositions.jsonl 원본):
> *"미국이 우라늄 농축 양보한 게 의아하며 이란어/영어 휴전안 문구 차이로 트럼프가 트집 잡아 협상 엎어질 가능성"*

진짜 reverse distillation:
- **attention_hook**: "미국이 *왜* 우라늄 농축을 양보했지? 트럼프가 나중에 뒤집을 빌미를 일부러 남긴 거 아닌가?"
- **implicit_question**: "휴전안 *언어판본 차이*가 의도된 모호함이라면, 이 협상은 시간 끌기 아닌가?"
- **reasoning_move**: "헤드라인=휴전 합의 → 보통 bullish. 김단테는 *합의문 문구 모호함*에 주목 → 트럼프 SNS 변덕을 함수에 넣고 결렬 시나리오를 더 무겁게."

→ raw_quote를 봐야 나온다. 자동 템플릿은 본 적이 없다.

---

## 5. R4 작업 지시

### 5.1 작업 흐름 5단계

```
R4-prep      자막 batch 분할 + 카드 ID 영역 할당
   ↓
R4-prompt    Agent용 일반화 프롬프트 작성 (prompts/r4_reverse_distill.md)
   ↓
R4-synth     Agent 5~6 병렬 호출 (영역별 자막 → 카드 직접)
   ↓
R4-audit     자동 템플릿 4종 정규식 검출 + 사람 검수
   ↓
R4-consolidate  영역별 jsonl → 통합본 + md 요약 + 메타 통계
```

### 5.2 카드 스키마 (reverse_distillation_cards.json의 26필드 유지 + 4개 진짜 합성)

**유지 (자동 추출/계산 OK)**:
- `card_id` (E001~ 또는 원하는 prefix)
- `title`, `labels` (R1 라벨 사전 25개 + framework)
- `source_origin`, `source_quality`
- `framework_used` (16개 사전 중 1개)
- `original_signal` (트리거 사건/지표/발언, 원본 충실)
- `causal_chain` (`[원인] → [중간] → [결과]` 최소 3단계)
- `expected_direction`, `time_horizon`
- `confidence`, `evidence_type`, `abstraction_level`, `technical_depth`, `quant_support`
- `trigger_conditions` (뉴스 헤드라인 매칭 가능 신호)
- `speaker_views` (화자별 시각, 발화 있는 화자만)
- `search_blurb` (RAG 임베딩 대상, 한/영 키워드)
- `source_references` (`video_id:line_num` 또는 `video_id:chunk:sent`)
- `insight_quality` (`score_0_to_10`, `grade`, `score_reasons`, `quality_test`, `missing_to_upgrade`)
- `storage_guidance` (`keep_as_fact` / `keep_as_inference` / `must_not_store_as_fact`)

**핵심 4개 — 자동 템플릿 금지, 화자 raw_quote 기반 진짜 합성**:

| 필드 | 정의 | 예시 |
|---|---|---|
| `attention_hook` | 화자가 *실제로 의아해한 지점* (자유 형식 1~2문장) | "왜 미국이 우라늄 농축을 양보했지? 트럼프가 뒤집을 빌미를 일부러 남긴 거 아닌가?" |
| `implicit_question` | 화자가 *던졌을 법한 진짜 질문* | "휴전안 언어판본 차이가 의도된 모호함이라면, 이 협상은 시간 끌기 아닌가?" |
| `reasoning_move` | 화자가 *어떻게 1차 인과를 거부하고 다른 방향으로 점프했나* (구체 사고 점프) | "헤드라인=휴전→bullish인데, 김단테는 합의문 문구 모호함에 주목 → 트럼프 SNS 변덕을 함수에 넣고 결렬 시나리오를 더 무겁게" |
| `matched_thinking_pattern` | *이 카드의 화자가 보인 사고 습관* (카드별 차별화) | "공식 합의문보다 *합의가 깨질 조건*에서 가격을 재평가하는 사고" |

### 5.3 자동 템플릿 금지 패턴 (R4-audit 정규식 검출 대상)

다음 패턴이 카드에 남아있으면 **다시 합성해야 한다**:

1. `라는 표면 신호가 실제로는`
2. `로 이어지는 조건부 전이 신호인지 확인한다`
3. `왜 지금 '` + `'가 나타났고, 어떤 조건에서`
4. `원초 신호를 곧바로 호재/악재로 판정하지 않고`
5. `1차 영향과 2차 수혜/피해 대상을 분리한다`
6. `카드의 기존 사고 점프는`
7. matched_thinking_pattern이 framework 사전 정의와 완전 일치
   - geopolitical_risk_premium = "지정학 이벤트를 1차 충격이 아니라 리스크 프리미엄과 협상 함수로 해석하는 사고"
   - regime_shift = "자금 흐름·정책·산업 질서의 장기 레짐 전환 가능성을 보는 사고"
   - (기타 framework도 마찬가지)

### 5.4 Framework 사전 (참고, 카드 framework_used에 사용)

`data/insight_storage_quality_guide.md`의 16개 framework + 핵심 질문 + 확인 데이터. R4 카드는 이 사전을 *참고*만 하고, matched_thinking_pattern은 카드별 자유 합성.

빈도 상위 (기존 87장 기준):
- geopolitical_risk_premium 13, regime_shift 12, platform_shift 9, substitution 8, decoupling 6, policy_reaction 6, multiple_rerating 5, adoption_curve 5, operating_leverage 4, margin_pressure 4, second_order_effect 3, capex_chain 3, supply_demand_imbalance 3, price_pass_through 2, commoditization 2, bottleneck 2

**framework는 *사고 방식 기반*으로 부여하라.** 주제 기반 금지. 예: 전력인프라 뉴스라고 무조건 bottleneck X. 데이터센터 CapEx→수주 뉴스면 capex_chain, 변압기 리드타임이면 bottleneck, 원가 전가 뉴스면 price_pass_through.

### 5.5 Batch 분할 안 (`scripts/prepare_r0_inputs.py` 재활용)

기존 `scripts/prepare_r0_inputs.py`의 분할 정책 그대로:

| Batch | 채널/영상 | 추정 토큰 | 카드 ID 영역 | 목표 카드 |
|---|---|---|---|---|
| A1 | 머니그라피 top4 (큰 4영상) | 87K | E001~E006 | 4~6 |
| A2 | 머니그라피 mid4 | 67K | E007~E012 | 4~6 |
| A3 | 머니그라피 small8 | 79K | E013~E020 | 6~8 |
| A4 | 머니코믹스 16 | 118K | E021~E032 | 10~12 |
| A5 | 김단테 14 + 오선 10 (24영상) | 74K | E033~E050 | 16~18 |
| A6 | 지식부장관 16 | 47K | E051~E066 | 12~16 |

**총 80~120장 카드** 목표 (사용자 원래 의도).

**ID prefix**:
- 기존 C/D 시리즈는 보존
- 새 카드 = `E` 시리즈 (E001~E120)
- 기존 카드는 비교/참고 자료로만 사용

### 5.6 Agent 프롬프트 (작성 예정 `prompts/r4_reverse_distill.md`)

다음 세션이 작성. 기존 `prompts/r0_transcript_to_cards.md` 패턴 따라가되:

**추가 지시사항** (R4 신규):
1. 카드 1장당 raw_quote 1~3개 *직접 인용*
2. 4개 핵심 필드 자유 형식 합성 (§5.2 표 참조)
3. **금지 패턴** (§5.3) 명시 — 카드 출력 직전 자체 검수
4. matched_thinking_pattern은 framework 사전 복붙 금지, 카드별 차별화
5. insight_quality 자체 평가 (점수 + score_reasons + missing_to_upgrade)
6. 카드 1장당 source_references에 최소 3개 (`video_id:chunk:sent` 형식, 자막 line은 추정 OK)

### 5.7 출력 구조

```
data/
├── r4_inputs/                  # batch 분할 jsonl (A1~A6)
├── r4_cards/                   # Agent별 카드 jsonl
│   ├── A1_moneygraphy_top4.jsonl
│   ├── A2_moneygraphy_mid4.jsonl
│   └── ...
├── r4_all_cards.jsonl          # 통합본 (E001~E???)
├── r4_all_cards.md             # 사람용 1줄 요약
├── r4_all_stats.md             # 메타 통계 (화자/framework/grade 분포)
└── r4_audit.md                 # 자동 템플릿 검출 결과
```

---

## 6. 검수

### 6.1 자동 검수 (`scripts/r4_audit_templates.py`, 다음 세션 작성)

각 카드의 4개 핵심 필드에 §5.3 금지 패턴 정규식 매칭. 발견 시:
- 카드 ID + 매칭 패턴 + 필드 기록
- 사용자에게 "이 카드들 재합성 필요" 보고

### 6.2 사람 검수 (사용자에게 위임)
- R4-consolidate 후 영역별 5장씩 무작위 샘플 → 사용자가 OK/NG
- NG 시 해당 Agent 호출 재실행

---

## 7. 사용자 운영 룰 (지키지 않으면 폭발)

이전 세션에서 사용자가 명시했거나 행동으로 보여준 룰:

- **코드는 Claude가 쓰고, 사용자는 방향만**. 사용자 답변은 짧은 시그널 위주 ("R2a-1", "OK", "다음 단계 가자")
- **정직한 진단 우선**. 편향·실수·자동 템플릿 같은 문제는 즉시 정직 보고 (이 R4 자체가 그 결과물)
- **jsonl + md 둘 다**. 기계용 + 사람용. 사람이 못 읽으면 검수 불가
- **로컬 ollama 기본**. 단 "지능 사용" 명시 시 Claude OK (R0/R4가 그 경우)
- **PLAYGROUND PLAY 규칙**: `README.md` = 계약서, 같은 턴에 갱신. 코드만 바꾸고 README 안 건드리면 작업 미완료
- **Agent 병렬 OK**. 단 카드 ID 영역 미리 할당 → 충돌 방지
- **HAN_LAB CLAUDE.md 100줄 룰**: 100줄 넘는 코드 한 번에 쏟기 전 (1) 파일 트리 (2) 각 파일 역할 한 줄 (3) 그다음 코드
- **자동 모드 금지**: 사용자 부재 명시 시에만 자동 진행. 그 외에는 분기점마다 짧게 확인

---

## 8. 다음 세션 첫 동작 (체크리스트)

순서대로:

- [ ] 이 `HANDOFF_R4.md` 정독
- [ ] `README.md` 읽고 변경 이력 끝부분 확인
- [ ] `data/인사이트_역증류_프로젝트_인수인계.md` 정독 (사용자 원본 목표)
- [ ] `data/insight_storage_quality_guide.md` 정독 (프레임별 품질 테스트)
- [ ] `data/reverse_distillation_cards.json`의 카드 3~5장 샘플 확인 (자동 템플릿 실물 보기)
- [ ] `scripts/prepare_r0_inputs.py` → `prepare_r4_inputs.py`로 복사 (분할 정책 그대로, 출력 디렉토리만 `r4_inputs/`로)
- [ ] `prepare_r4_inputs.py` 실행 → `data/r4_inputs/A1~A6.jsonl` 생성
- [ ] `prompts/r4_reverse_distill.md` 작성 (`prompts/r0_transcript_to_cards.md` 기반 + §5.2/5.3/5.6 신규 지시 추가)
- [ ] 사용자에게 분할안 + 카드 ID 영역 + 첫 호출 OK 확인
- [ ] 6 Agent 병렬 호출 (A1~A6 동시 또는 안전 위해 A1~A3 → A4~A6 분할)
- [ ] `scripts/r4_audit_templates.py` 작성 + 실행 → `data/r4_audit.md`
- [ ] `scripts/r4_consolidate.py` 작성 (r3a_consolidate.py 패턴) → `data/r4_all_cards.jsonl` + md
- [ ] 사용자 검수 → 통과 카드만 최종본으로 확정

---

## 9. 알려진 위험 / 함정

1. **Agent가 다시 자동 템플릿으로 갈 위험**. 프롬프트에 §5.3 금지 패턴 명시 + Agent 보고에 *자신이 만든 카드 한 장의 4개 핵심 필드 풀로 인용*하게 요청 → 메인이 즉시 검증
2. **머니그라피 big4 영상이 잡담 토크쇼**. R0에서도 영상 4개 중 3개가 비주류 초대석(연애상담/책토크/만화). R4 A1 호출은 카드 4장 미만 가능성 OK 미리 명시
3. **오선/김단테 자막이 R2에서 부분 활용됨**. R4는 자막 처음부터 다시 보는 거라 R2 카드와 source 영상 일부 겹침. **R4 카드는 R2 카드와 별도 평가** — 동일 영상 source라도 *사고 경로 추출* 결과가 다르면 별개 카드 가치 있음
4. **propositions.jsonl 활용**. raw_quote 자료로 *보조* 사용 가능. 단 1,060건이 18영상에서만 추출됐으니 R4 주 자료는 자막 원본. propositions는 김단테/오선의 매크로 카드 raw_quote 보강용으로만
5. **컨텍스트 폭발 주의**. 1 Agent 호출당 영상 자막 입력 + 카드 출력 + 시스템 + 지시서 → 200K 한도. 머니그라피 큰 영상은 영상당 ~24K 토큰이라 한 호출에 4개 까지가 안전선
6. **R0 영상 누락 보충**: 오선 6영상 + 김단테 2영상은 자막 .txt 없음. R4도 이 8영상은 처리 불가. yt-dlp 재다운로드는 R4 범위 외

---

## 10. R4 끝난 후 (R5 후보, 참고만)

사용자 원본 인수인계 §`앞으로 개선할 방향`에 명시:

- **R5-A: 임베딩 + RAG 인덱스**. R4 카드의 search_blurb + attention_hook + implicit_question + reasoning_move 결합 임베딩 → 뉴스 헤드라인 검색
- **R5-B: 산업별 전용 프롬프트 확장**. 전력인프라(`data/전력인프라_역증류_리서치_프롬프트.md`) 외에 AI 반도체/조선/방산/소비재/게임/지정학/SaaS 등 8개 후보
- **R5-C: 뉴스 적용 테스트**. 진짜 뉴스 1~3건 던져서 R4 카드 매칭 품질 + 사고 경로 활용 평가
- **R5-D: 카드 보강**. R4-audit/사용자 검수에서 low 등급 나온 카드의 정량 근거 보강

---

## 11. 한 줄 정리 (이거 하나만 기억해도 됨)

**"화자가 *왜* 이걸 이상하다고 봤는지, 화자가 *어떻게* 1차 인과를 거부하고 다른 방향으로 점프했는지, 그 사고 경로 자체를 raw_quote에서 끄집어내 카드로 저장한다. title을 X→Y로 split해서 자동 템플릿에 박는 건 사고가 아니라 형식이다."**
