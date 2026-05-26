# R0: 자막 → 카드 직접 합성 (Agent용 일반화 프롬프트)

> 모든 R0 호출(A1~A6)에서 재사용. 격리 Agent 컨텍스트에 그대로 전달.
> propositions 단계를 거치지 않고 자막에서 직접 사고회로 카드를 합성한다.

---

## 너의 역할

PLAY13_insight_distill의 R0 라운드 — 한국 경제 유튜브 자막 N개를 읽고 사고회로 카드 N장을 합성한다.

**왜 이 단계가 필요한가**: R1~R2에서 만든 카드 47장은 80영상 중 18영상에서만 추출된 propositions 기반이라 채널 편향이 큼. R0는 자막 원본에서 직접 카드를 만들어 4채널+지식부장관까지 균형을 회복한다.

최종 목적: Claude(=메인 컨텍스트의 AI)가 뉴스를 받았을 때 검색할 RAG 코퍼스. 카드 = 하나의 사고 회로.

---

## 호출 인자 (메인 컨텍스트가 줌)

- `INPUT_LIST_FILE`: 이번 호출이 처리할 영상 리스트 jsonl. 각 줄에 `{video_id, channel, file_path, title_hint, size_bytes}`.
- `OUTPUT_FILE`: 합성한 카드를 쓸 jsonl.
- `CARD_ID_START`: 이번 호출이 사용할 카드 ID 시작 (예: "D001"). D 시리즈는 R0 신규.
- `CARD_COUNT_HINT`: 권장 카드 수.
- `CHANNEL_CONTEXT`: 이번 호출이 다루는 채널의 성격 + sub-cluster 힌트.

---

## 입력 자막 형식

각 영상은 `file_path` 경로의 `.txt` 파일. Whisper 변환 결과로, 보통 문장 단위로 줄바꿈된 한국어 텍스트.

영상 1개 자막은 보통 3KB~97KB. 큰 영상(머니그라피 등)은 Read 한 호출 토큰 한도(25K)에 빠듯할 수 있다. 그 경우 `offset/limit`으로 분할 읽기. 절대 룰 기반 스크립트로 우회하지 마라.

---

## 작업 절차

### Step 1. INPUT_LIST_FILE 읽기
영상 리스트 jsonl을 Read. 영상 수와 각 file_path 확인.

### Step 2. 각 영상 자막 읽기
각 영상의 `file_path`를 Read. 큰 파일은 분할.

영상마다 다음을 파악:
- 주요 토픽 1~3개 (예: 연준 정책 / 이란 협상 / 반도체 실적 / 게임 산업 / 사업 운영 등)
- 핵심 인과 사슬 또는 예측 (있다면)
- 화자의 주된 시각/주장
- 인용할 만한 구체 사건/수치/고유명사

### Step 3. Cross-video 클러스터링
여러 영상이 같은 주제·인과를 다루면 한 카드로 묶는다. 한 영상이 여러 주제 섞으면 주제별로 따로 카드 후보.

`CHANNEL_CONTEXT`의 sub-cluster 힌트를 출발점으로 하되, 실제 자막 보고 조정.

### Step 4. 카드별 합성

`CARD_COUNT_HINT` 근처로 카드 수 조정. 한 카드 = 한 사고 회로.

카드 1장 스키마:

```jsonc
{
  "card_id": "D001",  // CARD_ID_START부터 순차
  "source_type": "transcript",  // R0 카드 구분자 (R2 카드는 "proposition")
  "label_origin": ["fed_policy", "us_equity_market"],  // R1 라벨 사전 25개 중 골라 부여 (아래 라벨 사전 참조)
  "title": "한국어 25자 이내, 'X → Y' 또는 'X 시나리오' 패턴",
  "trigger_conditions": [  // 뉴스 헤드라인에서 발견 가능한 객관적 신호. 2~5개. 추상화 금지.
    "구체 사건/지표/인물명을 포함한 문구"
  ],
  "speakers_view": {  // 발화한 화자만. 발화 없는 화자 절대 끼우지 마라.
    "화자명": "이 카드 주제에 대한 시각 한 줄"
  },
  "causal_chain": "[원인] → [중간] → [결과] 형식 한 줄",
  "expected_direction": "bullish_short | bearish_long | neutral | conditional | mixed 등 조합 자유",
  "time_horizon": "intraday | short | mid | long | unspecified",
  "confidence_meta": "신뢰도 한 줄 사유 (예: 'medium — 화자 2명 일치, 데이터 근거 1건')",
  "source_videos": [  // 이 카드에 기여한 영상들. 최소 1개. 인용 quote 1~2줄 포함.
    {
      "video_id": "ARn8WwEdieQ",
      "channel": "김단테 월가아재",
      "quote": "자막 원문에서 가장 핵심적인 1~2줄 직접 인용"
    }
  ],
  "search_blurb": "RAG 임베딩 대상. 한국어 키워드 풀 30~60단어. 명사/주제어 위주, 조사·동사 제거. 영어 키워드 OK (Fed, oil, CPI 등)."
}
```

### Step 5. 출력 파일 쓰기
`OUTPUT_FILE`에 합성 카드들을 jsonl로 Write.

---

## R1 라벨 사전 (label_origin에 사용)

매크로: `fed_policy`, `inflation_data`, `employment_data`, `oil_geopolitics`, `china_macro`, `emerging_markets`, `us_equity_market`, `korea_economy`
산업·섹터: `ai_tech`, `semiconductor_cycle`, `big_tech_earnings`, `game_industry`, `consumer_electronics`, `entertainment_content`, `energy_commodities`
기업·종목: `corporate_earnings`, `single_stock_move`, `startup_business`, `brand_strategy`
일반론·메타: `market_sentiment`, `investment_strategy`, `risk_factors`, `geopolitics_general`, `analyst_view`
(personal_anecdote는 카드화 안 함 — 사업 인사이트로 일반화 가능하면 startup_business로)

---

## 합성 규칙

- **자막은 Whisper 결과라 오타·동음이의 오류 존재** (예: "호르무즈" → "호르무지", "호르무제", "케빈 워시" → "케이리이닉스"). 의미 파악으로 원본 추정 후 카드에는 정확한 표기 사용.
- **title**: 명사형, 25자 이내.
- **trigger_conditions**: 뉴스에서 발견 가능한 객관적 신호. 구체 사건/지표/인물명. 추상화·일반화 과잉 금지.
- **speakers_view**: 발화 없는 화자 절대 끼우지 마라. 단일 화자 카드 OK.
- **causal_chain**: `[...] → [...] → [...]` 한 줄. 자막에 없는 단계 창작 금지.
- **confidence_meta**: 영상 수, 화자 수, 근거 유형 사실 그대로. 영상 1개·화자 1명이면 "low — 단일 영상·단일 화자".
- **source_videos**: 카드 합성에 실제 기여한 영상만. quote는 1~2줄, 자막에서 직접 인용 (오타 정리해도 됨).
- **search_blurb**: 한국어/영어 키워드 나열. 문장 X. 30~60단어.

---

## 메인 컨텍스트로 보고 (300단어 이내, 한국어)

1. **처리한 영상 수** + 영상별 핵심 주제 1줄씩
2. **생성한 카드 수** + sub-cluster 분할 결과
3. **카드 1장 전체 샘플** (가장 잘 만든 것, JSON 전체)
4. **자막 품질 이슈** (Whisper 오타, 잡담 비중, 매크로/산업 인사이트 밀도)
5. **다음 호출에 권하는 조정** (있으면)
6. **OUTPUT_FILE 절대경로** + 줄 수 확인

---

## 하지 마라
- 자막에 없는 사실/예측 창작 금지.
- 화자 짜맞춤 금지 (단일 화자 카드 자연 수용).
- 추상화·일반화 과잉 금지.
- search_blurb에 문장 쓰지 마라.
- 자막 전체 요약은 카드 가치 낮음 — 핵심 인과·예측·시각만 추출.
- 잡담·여행 일화·개인 경험은 사업 인사이트로 일반화되지 않으면 카드 제외.
- 룰 스크립트 작성 금지. 자막 본문 직접 읽고 의미 이해.
