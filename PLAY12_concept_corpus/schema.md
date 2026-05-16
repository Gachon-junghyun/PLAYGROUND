# schema.md — 데이터 스키마 정의

모든 jsonl은 한 줄 = 한 객체. UTF-8 / LF.

## raw_hits.jsonl

수집 단계 원본. `discover.py` 또는 디스패치 Claude가 채움.

```json
{
  "id": "hit_001",
  "topic": "전력 인프라 변압기",
  "url": "https://...",
  "title": "...",
  "type": "survey|standard|textbook|wiki|paper|blog|report",
  "year": 2022,
  "authors": ["..."],
  "language": "en|ko",
  "abstract": "3~10문장 발췌·요약",
  "concepts": ["..."],
  "parent_concept": "...",
  "source_domain": "ieee.org"
}
```

## sources.jsonl

정규화·중복제거된 자료 메타. `aggregate.py` 가 raw_hits에서 합쳐 만든다. `enrich.py` 가 text_* 필드 채움.

```json
{
  "id": "src_001",
  "topic": "전력 인프라 변압기",
  "url": "https://...",
  "title": "...",
  "type": "survey|standard|textbook|wiki|paper|blog|report",
  "authority": "high|medium|low",
  "year": 2022,
  "language": "en|ko",
  "abstract": "...",
  "concepts": ["src_001가 다루는 개념들"],

  "text_path": "texts/src_001.full.txt",
  "text_mode": "full|digest|none",
  "text_bytes": 152400,
  "enrich_policy": null,
  "enriched_at": "2026-05-15"
}
```

**authority 분류 규칙 (단순 휴리스틱):**
- `high`: type ∈ {survey, standard, textbook}
- `medium`: type ∈ {paper, wiki, report}
- `low`: type ∈ {blog, news}

**enrich_policy** (선택):
- `null` 또는 누락 — CLI `--mode` 따라감
- `"force_full"` — mode 무관하게 full로
- `"force_digest"` — mode 무관하게 digest로
- `"skip"` — enrich 건너뜀

## concepts.jsonl

```json
{
  "id": "c_001",
  "term": "유입식 변압기",
  "en": "oil-immersed transformer",
  "definition": "...",          // 합성된 정의 (aggregate가 우선 abstract 합성, 사용자가 손으로 다듬어도 됨)
  "parent": "변압기",
  "children": ["c_005", "c_006"],
  "related": ["c_003"],
  "sources": ["src_001", "src_003"]
}
```

## hierarchy.json

루트 토픽을 정점으로 하는 단순 중첩 dict.

```json
{
  "root": "전력 인프라 변압기",
  "tree": {
    "변압기": {
      "유입식": {},
      "건식": {},
      "절연유": {}
    },
    "전력 인프라": {}
  }
}
```

## chunks.jsonl (RAG)

`chunk_for_rag.py` 가 sources + texts/ 에서 만든다.

```json
{
  "id": "chunk_001",
  "source_id": "src_001",
  "text_mode": "full|digest",
  "offset": 0,
  "length": 800,
  "text": "...",
  "title": "원천 자료 제목 (검색 결과 표시용)",
  "authority": "high"
}
```
