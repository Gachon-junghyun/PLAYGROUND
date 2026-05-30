# R2a: 매크로 영역 카드 합성 (Agent용 프롬프트)

> 매크로 영역 8개 라벨의 명제들을 → 25~35장 사고회로 카드로 합성한다.
> self-contained 지시서. Agent 격리 컨텍스트에 그대로 전달.

---

## 너의 역할
PLAY13_insight_distill의 R2a 라운드 — 매크로 영역 카드 합성 담당.

최종 목적: Claude(=메인 컨텍스트의 AI)가 나중에 뉴스를 받았을 때 검색할 RAG 코퍼스. 카드 한 장 = 하나의 "사고 회로" 단위. 카드를 봤을 때 "비슷한 상황에서 4명 화자가 이렇게 봤구나, 이 회로를 빌리자"가 가능해야 함.

---

## 입력 파일 (2개 조인 필요)

1. `C:\Users\fivep\OneDrive\Desktop\PLAYGROUND\PLAY13_insight_distill\data\s1_clean.jsonl`
   - 명제 본문 (958건). 스키마: `{speaker, video_id, chunk_idx, sentence_idx_in_chunk, raw_quote, proposition, types, direction, time_horizon, confidence_level, evidence_type, ...}`

2. `C:\Users\fivep\OneDrive\Desktop\PLAYGROUND\PLAY13_insight_distill\data\r1_topics.jsonl`
   - 각 명제의 토픽 라벨. 스키마: `{id, labels}`. id 형식: `<video_id>:<chunk_idx>:<sentence_idx_in_chunk>`.

조인 키: s1_clean의 `video_id:chunk_idx:sentence_idx_in_chunk` ↔ r1_topics의 `id`.

---

## 대상 라벨 (이번 라운드)

매크로 영역 **8개 라벨**만 처리:
- `fed_policy` (49건)
- `inflation_data`
- `employment_data` (5건, 소량)
- `oil_geopolitics` (148건, 가장 큼)
- `china_macro` (8건, 소량)
- `emerging_markets` (56건)
- `us_equity_market` (69건)
- `korea_economy`

다른 라벨(brand_strategy, game_industry 등)은 이 라운드에서 무시. 단 멀티라벨 명제가 매크로 라벨 하나라도 포함하면 이 라운드 대상.

---

## 제외 룰
- `labels == ["personal_anecdote"]` 단독 → 제외.
- `labels`에 personal_anecdote가 있고 다른 라벨도 있으면 → 다른 라벨로 처리 (personal_anecdote는 무시).

---

## 작업 절차

### Step 1. 조인 + 그룹화
1. 두 jsonl 파일 읽고 id로 조인.
2. 매크로 8개 라벨에 해당하는 명제만 필터.
3. 라벨별로 그룹화 (멀티라벨 명제는 매크로 라벨 각각에 중복 포함).

### Step 2. 그룹별 카드 분할 결정
**큰 라벨은 sub-cluster로 분할, 작은 라벨은 병합 또는 단독 1장.**

권장 분할 (절대 강제 아님, 실제 명제 분포 보고 조정):
- `oil_geopolitics` 148건 → **3~4장** (예: 이란 협상 / 호르무즈 봉쇄 시나리오 / 유가→인플레 전이 / 휴전 시 시장 반응)
- `us_equity_market` 69건 → 2~3장
- `emerging_markets` 56건 → 1~2장 (인도 vs 신흥국 전반)
- `fed_policy` 49건 → 1~2장
- `inflation_data` → 1장
- `korea_economy` → 1장
- `employment_data` 5건 + `china_macro` 8건 → 너무 작으면 인접 매크로 라벨 카드의 부록 섹션으로 흡수하거나, 합쳐서 1 카드

**최종 목표 25~35장**. 카드 너무 작으면 (명제 3개 미만) 인접 카드에 병합.

### Step 3. 카드별 합성

각 카드 = 아래 스키마 1 JSON 객체. 모든 필드 채워라.

```jsonc
{
  "card_id": "C001",  // 라운드 단위 일련번호. R2a는 C001~C035 범위.
  "label_origin": ["fed_policy"],  // 이 카드를 만든 R1 라벨(들)
  "title": "고용 강세 → 연준 금리 동결 기대",  // 한 줄, 한국어
  "trigger_conditions": [  // 뉴스에서 이런 신호 보이면 이 카드 적용
    "미국 고용 지표 강세",
    "에너지 가격 상승",
    "근원 PCE 끈적"
  ],
  "speakers_view": {  // 화자별 시각. 카드 안에 등장하지 않은 화자는 생략.
    "오선의 미국 증시 라이프": "연말까지 금리 동결 전망에 무게",
    "김단테 월가아재": "동결 + 점도표가 시장 충격 트리거 가능"
  },
  "causal_chain": "[고용 강세 + 에너지↑] → [인플레 끈적] → [연준 동결] → [장기금리·달러 변동성↑]",  // 한 줄 인과 사슬
  "expected_direction": "neutral_to_bearish_short",  // 카드의 예측 방향. 자유 표기: bullish_short, bearish_long, neutral, conditional 등 조합 허용
  "time_horizon": "short",  // 카드 전체의 주된 시간축
  "confidence_meta": "medium — 화자 2명 일치, 근거 public_fact 1건",  // 신뢰도 사유. 화자 수, 근거, 일치/불일치
  "source_propositions": [  // 이 카드 합성에 쓰인 원본 명제 id. 최소 3개 권장, 너무 많으면 대표 10개로 추림.
    "ARn8WwEdieQ:0042:001",
    "T9L5jSFarmc:0011:000"
  ],
  "search_blurb": "고용 강세 에너지 가격 상승 연준 금리 동결 점도표 단기 변동성 미국 증시 호르무즈"
  // RAG 임베딩 대상. 한국어 키워드 풀. 명사/주제어 위주, 조사·동사 제거. 30~60단어.
}
```

**합성 규칙:**
- `title`: 명사형, "X → Y" 또는 "X 시나리오" 패턴. 25자 이내.
- `trigger_conditions`: 뉴스 기사에서 발견 가능한 객관적 신호. 2~5개.
- `speakers_view`: 명제들의 화자 시각을 짧게 요약. 화자 발화가 없으면 그 화자는 빼라 (4명 다 채우려고 만들지 마라).
- `causal_chain`: 한 줄, `[...] → [...] → [...]` 형식. 추상→구체 또는 원인→결과.
- `confidence_meta`: 화자 수와 근거를 사실 그대로. 화자 1명만이면 "low — 단일 화자"라고 솔직히. 화자들끼리 불일치면 "mixed — 강세/약세 화자 혼재".
- `source_propositions`: id 정확히. 최소 3개, 너무 많으면 대표 5~10개 추림.
- `search_blurb`: 한국어 키워드만 (조사·동사 X). 영어 키워드도 OK (Fed, oil, CPI 등). 카드 검색 시 매칭 핵심.

---

## 출력 파일

`C:\Users\fivep\OneDrive\Desktop\PLAYGROUND\PLAY13_insight_distill\data\r2a_cards.jsonl`
- 각 줄 = 카드 1장 JSON.
- 25~35장.

산출 후 Read 또는 Bash로 줄 수 확인.

---

## 메인 컨텍스트로 보고 (250단어 이내, 한국어)

1. **생성한 카드 수** + 라벨별 분포 (예: oil_geopolitics 4장, fed_policy 2장, ...)
2. **카드 1장 샘플 전체** (가장 잘 만들어졌다고 생각하는 것 1개, JSON 전체)
3. **합성 중 발견한 이슈** (예: "fed_policy 명제 49건 중 실제로는 점도표/금리 동결 두 클러스터로 갈렸음", "korea_economy는 명제 자체가 빈약해 1장 만들기도 애매")
4. **R2b(산업·섹터) 진입 전 사용자에게 권하는 프롬프트 조정** (예: "trigger_conditions가 추상적으로 나오는 경향 — 더 구체적으로 지시할 것")
5. **산출물 절대경로**

---

## 하지 마라
- 명제에 없는 사실/예측을 추가 창작 금지. raw_quote와 proposition 안에서 합성.
- speakers_view에서 발화 없는 화자 끼워 넣기 금지.
- 카드 제목·trigger를 추상화·일반화 과하게 하지 마라 (예: "글로벌 경제는 복잡하다" 같은 것).
- 한 카드에 화자 1명만 들어가도 OK — 굳이 여러 화자 짜맞추지 마라.
- search_blurb에 문장 쓰지 마라. 키워드 나열만.
