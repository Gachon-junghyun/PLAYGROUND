# R2: 카드 합성 (일반화 프롬프트, Agent용)

> 이 파일은 모든 R2 호출(R2a-1 ~ R2d)에서 재사용된다.
> 호출별 차이는 메인 컨텍스트가 전달하는 인자(`INPUT_FILE`, `CARD_ID_START`, `CARD_COUNT_HINT`, `LABEL_CONTEXT`, `OUTPUT_FILE`)로만 결정된다.
> self-contained — 격리된 Agent 컨텍스트에 그대로 전달.

---

## 너의 역할

PLAY13_insight_distill의 R2 카드 합성 — 한 라벨(또는 라벨 묶음)의 명제들을 읽고 "사고회로 카드" N장으로 합성한다.

최종 목적: Claude(=메인 컨텍스트의 AI)가 나중에 뉴스를 받았을 때 검색할 RAG 코퍼스. 카드 한 장 = 하나의 사고 회로. 카드 봤을 때 "비슷한 상황에서 화자들이 이렇게 봤구나, 이 회로를 빌리자"가 가능해야 함.

---

## 호출 인자 (메인 컨텍스트가 줌)

- `INPUT_FILE`: 이번 호출이 처리할 명제 jsonl. 슬림 포맷(아래 스키마).
- `OUTPUT_FILE`: 합성한 카드를 쓸 jsonl.
- `CARD_ID_START`: 이번 호출이 사용할 카드 ID 시작 (예: "C001", "C005").
- `CARD_COUNT_HINT`: 권장 카드 수 (예: "3~4장"). 실제 분포 보고 조정 가능.
- `LABEL_CONTEXT`: 이번 호출이 다루는 라벨 + sub-cluster 힌트.

---

## 입력 스키마

`INPUT_FILE`의 각 줄 = 명제 1개. 매크로 영역 전처리에서 만든 슬림 포맷:

```jsonc
{
  "id": "<video_id>:<chunk_idx>:<sentence_idx_in_chunk>",
  "speaker": "오선의 미국 증시 라이프" | "김단테 월가아재" | "머니코믹스" | "머니그라피",
  "labels": ["oil_geopolitics", "us_equity_market"],  // R1이 붙인 라벨들
  "macro_labels": ["oil_geopolitics"],  // 이번 라운드에 해당하는 라벨만
  "proposition": "중립적으로 정리된 명제",
  "raw_quote": "원문 문장",
  "types": ["fact_statement", "causal_claim", ...],
  "direction": "bullish" | "bearish" | "neutral" | ...,
  "time_horizon": "short" | "long" | ...,
  "confidence_level": "high" | "medium" | "low" | "unspecified",
  "evidence_type": "data" | "public_fact" | "none" | ...,
  "evidence_mentioned": ["4.6%", ...],
  "conditions": ["조건절들"]
}
```

---

## 출력 스키마 (카드 1장)

```jsonc
{
  "card_id": "C001",  // CARD_ID_START부터 순차
  "label_origin": ["oil_geopolitics"],  // 이 카드의 R1 라벨(들)
  "title": "한국어 25자 이내. 'X → Y' 또는 'X 시나리오' 패턴.",
  "trigger_conditions": [  // 뉴스에서 이런 신호 보이면 이 카드 적용. 2~5개.
    "뉴스 기사에서 발견 가능한 객관적 신호 문구"
  ],
  "speakers_view": {  // 화자별 시각. 발화 없는 화자는 빼라.
    "화자명": "이 화자의 시각 한 줄 요약"
  },
  "causal_chain": "[원인] → [중간] → [결과] 형식 한 줄",
  "expected_direction": "bullish_short | bearish_long | neutral | conditional | mixed 등 조합 자유",
  "time_horizon": "intraday | short | mid | long | unspecified",
  "confidence_meta": "신뢰도 한 줄 사유 (예: 'medium — 화자 2명 일치, 근거 public_fact 1건')",
  "source_propositions": [  // 이 카드에 쓰인 원본 명제 id. 최소 3개 권장, 많으면 대표 5~10개.
    "<video_id>:<chunk_idx>:<sentence_idx>"
  ],
  "search_blurb": "한국어 키워드 풀. 30~60단어. 명사/주제어 위주, 조사·동사 제거. 영어 키워드 OK (Fed, oil, CPI 등)."
}
```

---

## 작업 절차

### Step 1. 입력 읽기
`INPUT_FILE`을 Read로 읽는다. 파일이 25K 토큰 한도에 빠듯하면 offset/limit으로 분할 읽기. 메인 컨텍스트가 파일 크기를 인자에 포함시켰을 수 있다.

### Step 2. Sub-cluster 결정
`LABEL_CONTEXT`의 sub-cluster 힌트를 출발점으로, 실제 명제 분포 보고 최종 분할 결정.
- 한 cluster = 한 카드. 명제 3개 미만이면 인접 카드에 병합.
- `CARD_COUNT_HINT`는 권장. 실제 명제 분포가 다르면 ±1~2장 조정 OK.
- 화자별 명제 분포도 의식: 한 카드에 화자 1명만 나와도 OK, 굳이 짜맞추지 마라.

### Step 3. 카드별 합성

각 sub-cluster에 대해:
1. 그 클러스터의 명제들을 다 본다 (proposition + raw_quote + conditions + evidence_mentioned).
2. **title**: 명사형, 25자 이내, "X → Y" 또는 "X 시나리오".
3. **trigger_conditions**: 뉴스 기사에서 발견 가능한 객관적 신호. 추상화 과잉 금지 ("글로벌 경제는 복잡" 같은 거 X). 구체적 사건/지표/발언 단위.
4. **speakers_view**: 화자별 시각 1~2줄. 명제에 등장하지 않은 화자는 절대 끼워 넣지 마라.
5. **causal_chain**: `[...] → [...] → [...]` 한 줄. 명제들의 인과 사슬을 통합. 명제에 없는 단계 창작 금지.
6. **expected_direction / time_horizon**: 클러스터 내 명제들의 direction/time_horizon 메타에서 우세한 쪽 또는 조합. "혼재"면 "mixed" 또는 "conditional".
7. **confidence_meta**: 화자 수, 근거 유형, 일치/불일치를 사실 그대로. 화자 1명만이면 "low — 단일 화자". 화자들 입장이 갈리면 "mixed — 강세/약세 혼재".
8. **source_propositions**: 클러스터의 명제 id들. 최소 3개, 너무 많으면 대표 5~10개로 추림.
9. **search_blurb**: 키워드 나열만. 문장 X. 30~60단어.

### Step 4. 출력 파일 쓰기
`OUTPUT_FILE`에 합성한 카드들을 jsonl로 Write. 파일이 이미 존재하면 덮어쓰지 말고 append (메인 컨텍스트가 별도 알리는 경우 외에는).

각 줄 = 카드 1장 JSON.

---

## 메인 컨텍스트로 보고 (250단어 이내, 한국어)

1. **생성한 카드 수** + sub-cluster 분할 결과 (예: "oil_geopolitics 148건을 4 클러스터로 — 협상/봉쇄/유가/휴전")
2. **카드 1장 전체 샘플** (가장 잘 만들어졌다고 생각하는 것, JSON 전체)
3. **합성 중 발견한 이슈** (예: "협상 클러스터의 명제 절반이 김단테 단독, 오선 거의 없음 — 화자 다양성 약함")
4. **다음 호출에 권하는 프롬프트 조정** (예: "trigger_conditions가 너무 일반적으로 나옴 — 다음엔 '뉴스 헤드라인에 실제 등장할 단어' 강조")
5. **OUTPUT_FILE 절대경로** + 줄 수 확인

---

## 하지 마라
- 명제에 없는 사실/예측 창작 금지. raw_quote와 proposition 안에서만 합성.
- speakers_view에 발화 없는 화자 끼워 넣기 금지.
- title/trigger를 추상화·일반화 과하게 하지 마라.
- 한 카드에 화자 1명만 들어가도 OK — 4명 다 채우려 짜맞추지 마라.
- search_blurb에 문장 쓰지 마라 — 키워드 나열만.
- card_id 직접 만들지 마라 — `CARD_ID_START`부터 순차 부여.
