# R4: 자막 → 진짜 사고 경로 카드 (Agent용 일반화 프롬프트)

> 모든 R4 호출(A1~A6)에서 재사용. 격리 Agent 컨텍스트에 그대로 전달.
> R4는 **자동 템플릿 절대 금지**. 자막의 raw_quote에서 화자가 *실제로 의아해한 지점*과 *어떻게 1차 인과를 거부했는지*를 추출해 카드의 4개 핵심 필드를 합성한다.

---

## 너의 역할

PLAY13_insight_distill의 **R4 라운드** — 한국 경제 유튜브 자막 N개를 읽고 **진짜 사고 경로 카드 N장**을 합성한다.

**왜 R4가 필요한가**: 이전 라운드(R0/R2)에서 만든 87장 카드를 외부에서 reverse-distillation 메타로 보강했더니, 4개 핵심 필드(attention_hook, implicit_question, reasoning_move, matched_thinking_pattern)가 **카드 title을 "X → Y"로 split하거나 framework 정의를 복붙한 자동 템플릿**으로 판명. 화자의 진짜 *의아함*과 *사고 점프*가 사라졌다. R4는 자막에서 raw_quote를 직접 끄집어 그 4개 필드를 **자유 합성**한다.

최종 목적: Claude(=메인 컨텍스트의 AI)가 뉴스를 받았을 때 검색해 빌려 쓸 RAG 코퍼스. 카드 = 하나의 **사고 회로**.

---

## 호출 인자 (메인 컨텍스트가 줌)

- `INPUT_LIST_FILE`: 처리할 영상 리스트 jsonl. 각 줄 `{video_id, channel, file_path, title_hint, size_bytes}`.
- `OUTPUT_FILE`: 합성한 카드를 쓸 jsonl.
- `CARD_ID_START`: 카드 ID 시작 (예: "E001"). **E 시리즈는 R4 신규**. C/D 시리즈는 기존이므로 충돌 금지.
- `CARD_ID_END`: 영역 끝(예: "E006"). 이 범위 안에서만 ID 발행. 권장 카드 수 = `END - START + 1` 부근.
- `CHANNEL_CONTEXT`: 채널 성격 + sub-cluster 힌트.

---

## 입력 자막 형식

각 영상은 `file_path` 경로의 `.txt`. Whisper 변환 결과로 문장 단위 줄바꿈된 한국어. 영상당 3KB~97KB. 큰 영상은 Read `offset/limit`으로 분할. **절대 룰 기반 스크립트로 우회하지 마라.**

---

## 작업 절차

### Step 1. INPUT_LIST_FILE 읽기
영상 리스트 jsonl을 Read. 영상 수와 file_path 확인.

### Step 2. 각 영상 자막 읽기
각 영상의 `file_path`를 Read. 큰 파일은 offset/limit으로 분할 읽기. 영상마다 다음을 메모:
- 주요 토픽 1~3개
- **화자가 *의아해한 지점*** (자막에서 "근데 이게 좀 이상한 게…", "원래라면 …일 텐데", "사람들은 …라고 보는데 저는…" 같은 표지)
- **화자의 사고 점프** (1차 인과 → 다른 방향 함수 추가/거부)
- 인용할 만한 raw_quote 2~3개 (직접 인용)

### Step 3. Cross-video 클러스터링
같은 주제·인과를 다루는 영상이 여러 개면 한 카드로 묶는다. 한 영상이 여러 주제 섞으면 주제별로 따로 카드 후보. `CHANNEL_CONTEXT`의 sub-cluster 힌트를 출발점으로 하되 자막 보고 조정.

### Step 4. Framework 선택 (사고 방식 기반, 주제 X)

다음 16개 사전 중 **그 카드의 *사고 방식*에 맞는 것 1개** 부여. 주제 기반 금지.

| framework | 사고 방식 한 줄 | 예시 적용 |
|---|---|---|
| `geopolitical_risk_premium` | 지정학 이벤트를 1차 충격이 아니라 리스크 프리미엄·협상 함수로 본다 | 이란/우크라/대만 협상·제재·봉쇄 |
| `regime_shift` | 단기 사건이 아니라 자금/정책/경쟁 구도의 지속 변화로 본다 | 달러 패권/AI 자본 사이클/인구 구조 |
| `platform_shift` | 기술이 가치 포획 위치(과금 주체·고객 접점)를 옮긴다 | AI 검색/플랫폼 갈아탐 |
| `substitution` | 대체재가 가격·성능·유통·브랜드로 강자를 압박한다 | 전기차/제네릭/저가 브랜드 |
| `decoupling` | 뉴스 방향과 가격 반응이 *왜 어긋났나*를 기대치/포지셔닝으로 설명 | 호실적인데 주가 하락/악재인데 반등 |
| `policy_reaction` | 정책 입안자의 반응 함수와 실제 규제/금리/보조금 연결 | 연준 점도표/IRA/규제 변화 |
| `multiple_rerating` | 실적 비트보다 기대치·가이던스·주가 반응 조합 | 어닝 시즌 멀티플 리레이팅 |
| `adoption_curve` | 일화가 아니라 반복 구매·침투율·CAC/LTV로 본다 | 신제품/구독/플랫폼 채택 |
| `operating_leverage` | 고정비 구조·단위경제·규모 마진 변화 | SaaS/플랫폼 마진 확장 |
| `margin_pressure` | 매출 성장과 비용 분리, 영업레버리지/감가상각 부담 | CapEx 큰 빅테크/하드웨어 |
| `second_order_effect` | 1차 반응과 2차 파급 분리, 뜻밖의 수혜/피해자 | 트럼프 관세/이민 정책 파급 |
| `capex_chain` | 상위 CapEx 변화가 후방 수주/매출/가이던스로 연결 | 빅테크 AI 데이터센터 → 반도체/전력 |
| `supply_demand_imbalance` | 수요·공급·재고·가동률 중 최소 2개 같은 방향 | 원유/반도체/곡물 |
| `price_pass_through` | 원가 상승이 최종가/PPI/마진 중 어디로 전가되나 | 인플레/관세 전가 |
| `commoditization` | 차별화 소멸 → 가격경쟁·과잉·마진 하락 동시 | 메모리/일반 SaaS |
| `bottleneck` | 희소 자원/처리량/리드타임이 가격을 먼저 올린다 | HBM/변압기/조선소 슬롯 |
| `platform_shift` 외 | (위 16개에 들어가는 게 핵심) | |

**framework 선택 후 그 카드만의 `matched_thinking_pattern`을 *자유 합성*한다.** 사전 정의를 복붙하지 마라. 카드의 화자가 실제로 보인 사고 습관을 한 줄로.

### Step 5. 카드 합성 (스키마 아래 §"카드 스키마")

`CARD_ID_START`~`CARD_ID_END` 범위 안에서 ID 발행. 한 카드 = 한 사고 회로.

**4개 핵심 필드는 raw_quote 기반 자유 합성** (§"4 핵심 필드 합성 규칙" 참조).

### Step 6. 자가 검수 (필수)

각 카드 출력 직전, 4개 필드에 다음 **금지 패턴**이 있는지 확인. 발견되면 *그 카드를 다시 합성*.

```
패턴 1: "라는 표면 신호가 실제로는"
패턴 2: "로 이어지는 조건부 전이 신호인지 확인한다"
패턴 3: "왜 지금 '" + "'가 나타났고, 어떤 조건에서"
패턴 4: "원초 신호를 곧바로 호재/악재로 판정하지 않고"
패턴 5: "1차 영향과 2차 수혜/피해 대상을 분리한다"
패턴 6: "카드의 기존 사고 점프는"
패턴 7: matched_thinking_pattern이 framework 사전 정의와 완전 일치
        예: "지정학 이벤트를 1차 충격이 아니라 리스크 프리미엄과 협상 함수로 해석하는 사고" 그대로 X
```

### Step 7. 출력 파일 쓰기
`OUTPUT_FILE`에 합성 카드들을 jsonl로 Write.

---

## 4 핵심 필드 합성 규칙 (R4의 핵심)

이게 R4 존재 이유다. **자동 템플릿 절대 금지**.

### `attention_hook` (화자가 *실제로 의아해한 지점*)
- 자막에서 화자가 "근데 좀 이상한 게…", "보통은 …일 텐데", "왜 …지?" 같은 표지로 의아함을 표현한 지점을 잡아 1~2문장으로.
- **나쁜 예** (자동 템플릿): "'이란-미국 협상 쟁점'라는 표면 신호가 실제로는 '결렬 리스크'로 이어지는 조건부 전이 신호인지 확인한다."
- **좋은 예** (raw_quote 기반): "왜 미국이 우라늄 농축을 양보했지? 트럼프가 나중에 뒤집을 빌미를 일부러 남긴 거 아닌가?"

### `implicit_question` (화자가 *던졌을 법한 진짜 질문*)
- 화자의 raw_quote가 *답하려 했던 질문*을 재구성. 표면 정보 X, 사고 함수 X.
- **나쁜 예**: "왜 지금 '이란-미국 협상 쟁점'가 나타났고, 어떤 조건에서 '결렬 리스크'로 확장되는가?"
- **좋은 예**: "휴전안의 *언어판본 차이*가 의도된 모호함이라면, 이 협상은 시간 끌기 아닌가?"

### `reasoning_move` (화자가 *어떻게 1차 인과를 거부하고 다른 방향으로 점프했나*)
- 헤드라인 1차 해석 vs 화자가 함수에 추가/뺀 변수. 구체적 사고 점프 1~2문장.
- **나쁜 예**: "원초 신호를 곧바로 호재/악재로 판정하지 않고, geopolitical_risk_premium 프레임으로 1차 영향과 2차 수혜/피해 대상을 분리한다."
- **좋은 예**: "헤드라인=휴전 합의=bullish인데, 김단테는 *합의문 문구 모호함*에 주목 → 트럼프 SNS 변덕을 함수에 넣고 결렬 시나리오를 더 무겁게 잡음."

### `matched_thinking_pattern` (화자가 보인 사고 *습관*, 카드별 차별화)
- framework 사전 정의 복붙 X. 이 카드의 화자가 *반복적으로 보이는 사고 패턴*을 한 줄로.
- **나쁜 예** (framework 복붙): "지정학 이벤트를 1차 충격이 아니라 리스크 프리미엄과 협상 함수로 해석하는 사고"
- **좋은 예**: "공식 합의문보다 *합의가 깨질 조건*에서 가격을 재평가하는 사고"

---

## 카드 스키마 (R4)

```jsonc
{
  "card_id": "E001",                    // CARD_ID_START~END 범위
  "title": "한국어 25자 이내, 'X → Y' 또는 'X 시나리오' 패턴",
  "labels": ["fed_policy"],             // R1 라벨 사전 25개 중 1~3개
  "source_origin": "channel_interpretation",  // channel_interpretation | reported_fact | speaker_inference
  "source_quality": "medium",           // low | medium | high
  "framework_used": "geopolitical_risk_premium",  // 16개 사전 중 1개
  "matched_thinking_pattern": "<카드별 자유 합성, framework 복붙 금지>",

  // ===== R4 핵심 4필드 (자동 템플릿 금지) =====
  "attention_hook": "<화자가 실제 의아해한 지점, 1~2문장>",
  "implicit_question": "<화자가 던졌을 법한 진짜 질문>",
  "reasoning_move": "<화자가 1차 인과를 거부하고 점프한 경로, 1~2문장>",

  "original_signal": "트리거 사건/지표/발언, 자막 충실. 세미콜론으로 구분 OK",
  "trigger_conditions": [
    "뉴스 헤드라인에서 발견 가능한 객관적 신호. 구체 사건/지표/인물명. 2~5개."
  ],
  "causal_chain": "[원인] → [중간] → [결과]  최소 3단계",
  "expected_direction": "bullish_short | bearish_long | neutral | conditional | mixed",
  "time_horizon": "intraday | short | mid | long | unspecified",
  "confidence": "medium — 화자 N명 일치, 데이터 근거 M건",
  "evidence_type": "expert_interpretation | public_fact | speaker_inference | mixed",
  "abstraction_level": "low | medium | high",
  "technical_depth": "low | medium | high",
  "quant_support": "none | one_or_two_numbers | multi_numbers",

  "speaker_views": {                    // 발화한 화자만. 발화 없는 화자 절대 끼우지 마라.
    "김단테 월가아재": "이 카드 주제에 대한 시각 한 줄"
  },

  "source_videos": [                    // 카드 합성에 기여한 영상. 최소 1개.
    {
      "video_id": "ARn8WwEdieQ",
      "channel": "김단테 월가아재",
      "quote": "자막에서 가장 핵심적인 1~2줄 직접 인용 (오타 정리 OK)"
    }
  ],

  "source_references": [                // 최소 3개. video_id:chunk:sent 형식. 자막 line은 추정 OK.
    "ARn8WwEdieQ:2:5",
    "ARn8WwEdieQ:5:12",
    "V5dXgp5Cxgg:0:3"
  ],

  "search_blurb": "한국어/영어 키워드 30~60단어. 문장 X. 명사/주제어 위주.",

  "insight_quality": {
    "score_0_to_10": 7,
    "grade": "medium",                  // low | medium | high
    "score_reasons": ["3단 이상 causal_chain", "구체 trigger 다수", ...],
    "quality_test": "<framework별 quality_test, insight_storage_quality_guide.md 참고>",
    "missing_to_upgrade": ["보강 필요 항목 1~2개"]
  },

  "storage_guidance": {
    "keep_as_fact": ["original_signal", "raw numbers in trigger"],
    "keep_as_inference": ["matched_thinking_pattern", "reasoning_move", "expected_direction"],
    "must_not_store_as_fact": ["unverified future prediction", "speaker interpretation without source label"]
  }
}
```

---

## R1 라벨 사전 (label에 사용)

매크로: `fed_policy`, `inflation_data`, `employment_data`, `oil_geopolitics`, `china_macro`, `emerging_markets`, `us_equity_market`, `korea_economy`
산업·섹터: `ai_tech`, `semiconductor_cycle`, `big_tech_earnings`, `game_industry`, `consumer_electronics`, `entertainment_content`, `energy_commodities`
기업·종목: `corporate_earnings`, `single_stock_move`, `startup_business`, `brand_strategy`
일반론·메타: `market_sentiment`, `investment_strategy`, `risk_factors`, `geopolitics_general`, `analyst_view`

(personal_anecdote는 카드화 X — 사업 인사이트로 일반화되면 startup_business)

---

## 합성 규칙

- **자막은 Whisper 결과라 오타·동음이의 오류 존재** (예: "호르무즈" → "호르무지"). 의미로 원본 추정 후 카드는 정확 표기.
- **title**: 명사형, 25자 이내.
- **trigger_conditions**: 뉴스에서 발견 가능한 객관적 신호. 구체 사건/지표/인물명. 추상화·일반화 과잉 X.
- **speakers_view**: 발화 없는 화자 절대 끼우지 마라. 단일 화자 카드 OK.
- **causal_chain**: `[...] → [...] → [...]` 한 줄. 자막에 없는 단계 창작 X.
- **confidence**: 영상 수, 화자 수, 근거 유형 사실 그대로. 영상 1개·화자 1명이면 "low — 단일 영상·단일 화자".
- **source_videos**: 카드 합성에 실제 기여한 영상만. quote는 1~2줄 직접 인용.
- **search_blurb**: 키워드 나열. 문장 X.
- **framework는 *사고 방식* 기반**. 주제 기반 X. (예: 전력인프라 뉴스라고 무조건 bottleneck X. 데이터센터 CapEx→수주면 capex_chain, 변압기 리드타임이면 bottleneck, 원가 전가면 price_pass_through.)

---

## 메인 컨텍스트로 보고 (400단어 이내, 한국어)

1. **처리한 영상 수** + 영상별 핵심 주제 1줄
2. **생성한 카드 수** + sub-cluster 분할 결과 + 사용한 framework 분포
3. **카드 1장 *4개 핵심 필드 풀로 인용*** (자가 검수 통과한 가장 잘 만든 카드)
   - 메인이 자동 템플릿 패턴 다시 검증할 수 있게 4필드 본문 그대로 보고
4. **자가 검수 결과** — 재합성한 카드가 있으면 그 사유 한 줄
5. **자막 품질 이슈** (Whisper 오타, 잡담 비중, 매크로/산업 인사이트 밀도)
6. **OUTPUT_FILE 절대경로** + 줄 수 확인

---

## 하지 마라

- 자막에 없는 사실/예측 창작 X.
- 화자 짜맞춤 X (단일 화자 카드 자연 수용).
- **4개 핵심 필드에 자동 템플릿 X** (§"4 핵심 필드 합성 규칙" / Step 6 금지 패턴 참고).
- matched_thinking_pattern을 framework 사전 정의 그대로 복붙 X.
- title을 "X → Y"로 split해서 attention_hook/implicit_question에 박지 마라.
- 추상화·일반화 과잉 X.
- search_blurb에 문장 쓰지 마라.
- 자막 전체 요약 X — 핵심 인과·예측·시각·*화자의 의아함*만 추출.
- 잡담·여행 일화·개인 경험은 사업 인사이트로 일반화 안 되면 카드 제외.
- 룰 스크립트 작성 X. 자막 본문 직접 읽고 의미 이해.
