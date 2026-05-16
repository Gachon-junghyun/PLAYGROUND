# PROMPT.md — discover 단계 검색 지침

이 파일은 디스패치 환경의 Claude가 `discover` 단계에서 raw_hits.jsonl을 채울 때 따르는 지침이다.

## 입력
- `<topic>`: 개념·도메인 키워드 (예: "전력 인프라 변압기", "로컬 LLM")
- 출력 경로: `data/<topic_slug>/raw_hits.jsonl`

## 수집 원칙

1. **개념 중심, evergreen 우선.** 뉴스·이벤트 기사가 아니라 다음 우선순위로:
   - 서베이/리뷰 논문 (`type: "survey"`)
   - 표준 문서 (`type: "standard"`) — IEC, IEEE, KS, NIST 등
   - 교과서/북챕터 (`type: "textbook"`)
   - 위키 (`type: "wiki"`)
   - 핵심 논문 (`type: "paper"`)
   - 기술 블로그/리포트 (`type: "blog"`, `type: "report"`) — 보조
2. **언어 균형.** 한국 도메인이면 한국어 자료 절반 이상 확보. 영어 표준/논문은 거의 항상 포함.
3. **개념 계층을 의식해서 수집.** 토픽이 "전력 인프라 변압기"면 상위(전력 인프라), 핵심(변압기 일반), 하위(유입식·건식·절연유 등)를 골고루.
4. **검색 폭 ≒ 도메인당 5~10건, 총 20~40건.** 너무 많으면 다음 단계가 무거워짐. 권위 높은 것 위주.
5. **중복 URL 금지.** 같은 자료 두 번 안 적음.

## 검색 쿼리 생성 (참고)

토픽 `T`에 대해 다음 쿼리들을 생성해서 분기별로 Agent 띄움:
- `"{T}" survey OR review`
- `"{T}" tutorial OR textbook`
- `"{T}" IEC OR IEEE OR KS standard`
- `"{T}" 기초 OR 개론` (한국어)
- `"{T}" 분류 OR 종류 OR taxonomy`
- `"{T} site:wikipedia.org"` / `"{T} site:ko.wikipedia.org"`
- `"{T}" filetype:pdf` (PDF 우선)
- 하위 개념 키워드 추정 후 각각에 대해서도 위 쿼리 변형

## raw_hits.jsonl 한 줄 스키마

```json
{
  "id": "hit_001",
  "topic": "전력 인프라 변압기",
  "url": "https://...",
  "title": "Survey of Power Transformer Design",
  "type": "survey",
  "year": 2022,
  "authors": ["A. Kim", "B. Lee"],
  "language": "en",
  "abstract": "변압기 설계 동향에 대한 종합 리뷰... (3~10문장)",
  "concepts": ["변압기", "전력 인프라", "변압기 설계"],
  "parent_concept": "변압기",
  "source_domain": "ieee.org"
}
```

필드 설명:
- `id`: hit 고유 ID. `hit_{NNN}` 식 zero-padding.
- `type`: 위 7가지 중 하나 (`survey|standard|textbook|wiki|paper|blog|report`).
- `concepts`: 이 자료가 다루는 개념들. **첫 항목이 가장 핵심.**
- `parent_concept`: 개념 트리에서 이 자료의 1차 위치. `concepts[0]` 와 같거나 그 부모.
- `abstract`: **자료 본문에서 직접 발췌하거나, 페이지를 읽은 뒤 3~10문장으로 요약.** 추측 금지. 못 읽으면 그 hit은 제외.
- `year`, `authors`, `language`: 알면 채우고 모르면 생략 (null 말고 키 자체를 빼라).

## 출력 규칙

- 한 줄 = 한 hit. 줄 사이에 빈 줄 X.
- UTF-8, LF 줄바꿈.
- 같은 토픽 재실행 시 기존 `raw_hits.jsonl`에 **append** (id는 이어서 증가, URL 중복은 미리 제거).

## 금지

- 검증되지 않은 URL 만들어 적기 (환각 금지). 실제로 페이지를 받아 본 자료만.
- abstract 자리에 LLM이 일반론으로 채우기. 반드시 페이지 본문 기반.
- 뉴스 기사 비중 30% 초과. (뉴스가 핵심이면 PLAY4를 써라.)
