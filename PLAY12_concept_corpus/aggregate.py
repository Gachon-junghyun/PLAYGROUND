"""aggregate — raw_hits → sources + concepts + hierarchy.

- URL 중복 제거 (같은 URL이면 가장 최근 hit 메타 사용, abstract는 가장 긴 것)
- 자료 타입 → authority 매핑
- concepts 통합: hit들의 (concept, parent) 관계를 모아 트리 구성
- 각 concept에 sources 역참조
- 정의(definition)는 1차로 "그 개념이 핵심인 hit들 abstract의 첫 문장 합성"
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

from collections import Counter

from _common import (
    authority_of,
    read_jsonl,
    slugify,
    topic_dir,
    write_jsonl,
)


def _authority_from_score(base: str, type_: str, score: int | None) -> str:
    """citations/upvotes 기반으로 권위 등급 보정."""
    if score is None:
        return base
    if type_ in ("paper", "survey"):
        if score >= 500:
            return "high"
        if score >= 50:
            return "medium" if base != "high" else "high"
    if type_ == "blog":
        if score >= 500:
            return "medium"  # 인기 글은 medium까지만
    return base


# 토픽·자료에 자주 나오는 명사구 후보 (한국어/영어, 2~4 단어). 매우 단순한 휴리스틱.
_NGRAM_RE = __import__("re").compile(
    r"\b[A-Z][A-Za-z0-9\-]{2,}(?:\s+[A-Z][A-Za-z0-9\-]{2,}){0,3}\b"
)
_KO_RE = __import__("re").compile(r"[가-힣]{2,}(?:\s[가-힣]{2,}){0,2}")
_STOPWORDS = {
    # 문장 시작 부사·접속어
    "The", "This", "That", "These", "Those", "There", "Their",
    "What", "Which", "When", "Where", "Why", "How",
    "With", "From", "Into", "About", "After", "Before", "Among", "Across", "Through",
    "More", "Most", "Some", "Many", "Such", "Other", "Another", "Several",
    "Additionally", "Despite", "Finally", "However", "Furthermore", "Therefore",
    "Although", "Indeed", "Instead", "Otherwise", "Meanwhile", "Nevertheless",
    "Hence", "Thus", "Recently", "While", "Then", "Moreover", "Currently",
    "First", "Second", "Third", "Last", "Often", "Sometimes",
    "Importantly", "Notably", "Specifically", "Generally", "Typically",
    "Please", "Thank", "Best", "Nice", "Great", "Awesome",
    # 메타·플랫폼
    "Wikipedia", "Survey", "Review", "Overview", "Abstract", "Introduction",
    "Twitter", "Facebook", "Instagram", "YouTube", "Reddit", "PostView", "Mogong",
    # 국가·언어·요일·월
    "Korea", "Korean", "Japanese", "Chinese", "English", "American", "European",
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
    "January", "February", "March", "April", "June", "July",
    "August", "September", "October", "November", "December",
    # 너무 일반적
    "Large", "Small", "New", "Old", "Good", "Bad", "Physical", "Digital",
}
_KO_STOPWORDS = {
    "그리고", "그러나", "하지만", "또한", "따라서", "그래서", "그런데",
    "이것은", "이는", "이러한", "다음과", "위와", "아래와",
    "있습니다", "없습니다", "합니다", "한다고", "이라고", "라고",
    "교과에서", "있는", "위한", "통한", "대한", "관련", "위해",
    "오늘", "어제", "내일", "지금", "현재", "이전", "이후",
}


def _is_noise_concept(term: str) -> bool:
    """concept 후보 자체로 분명한 노이즈."""
    if not term:
        return True
    t = term.strip()
    if t in _STOPWORDS or t in _KO_STOPWORDS:
        return True
    # 숫자만 / 연도-연도 패턴 / "Year-Year in X"
    if __import__("re").match(r"^[\d\s\-–\.]+$", t):
        return True
    if __import__("re").match(r"^20\d\d[\-–]\d\d?\b", t):  # "2025-26"
        return True
    if __import__("re").search(r"\b20\d\d\s+in\b", t):  # "2026 in South Korean music"
        return True
    if t.startswith("List of "):
        return True
    return False


def _token_groups(topic: str, aliases: list[str] | None = None) -> list[list[str]]:
    """토픽과 각 alias를 별도 token 그룹으로 만든다.
    예: topic='피지컬 AI', aliases=['Physical AI'] → [['피지컬'], ['physical']].
    하나의 그룹만 매칭돼도 hit는 적합으로 본다.
    """
    import re
    groups: list[list[str]] = []
    seen_groups: set[tuple[str, ...]] = set()
    for s in [topic] + (aliases or []):
        toks = re.findall(r"[A-Za-z]{3,}|[가-힣]{2,}", s.lower())
        if not toks:
            continue
        key = tuple(sorted(toks))
        if key in seen_groups:
            continue
        seen_groups.add(key)
        groups.append(toks)
    return groups


def _hit_relevant(title: str, abstract: str, token_groups: list[list[str]]) -> bool:
    """token_groups: list of [tok, ...] — 어느 그룹이든 매칭하면 적합."""
    if not token_groups:
        return True
    title_low = (title or "").lower()
    abstract_low = (abstract or "").lower()
    for tokens in token_groups:
        if any(tok in title_low for tok in tokens):
            return True
        if tokens and all(tok in abstract_low for tok in tokens):
            return True
        for tok in tokens:
            if abstract_low.count(tok) >= 2:
                return True
    return False


def _hit_relevant_to_topic(title: str, abstract: str, topic: str) -> bool:
    return _hit_relevant(title, abstract, _token_groups(topic))


def _keyword_candidates(text: str, top_n: int = 10, min_freq: int = 3) -> list[str]:
    """body 텍스트에서 빈도 높은 명사구 후보 추출 (휴리스틱).

    노이즈가 많이 들어가는 1-단어 후보는 엄격(최소 8자)하게.
    한국어는 2단어 이상(공백 포함)만 받음 (단일 한국어 단어는 너무 일반적).
    """
    cnt: Counter[str] = Counter()
    for m in _NGRAM_RE.findall(text or ""):
        tokens = m.split()
        first = tokens[0]
        if first in _STOPWORDS:
            continue
        if len(tokens) == 1 and len(m) < 8:
            continue
        if len(m) < 4 or len(m) > 60:
            continue
        cnt[m] += 1
    for m in _KO_RE.findall(text or ""):
        m = m.strip()
        if m in _KO_STOPWORDS:
            continue
        # 한국어는 공백 있는 다어절만 받음
        if " " not in m:
            continue
        if 5 <= len(m) <= 30:
            cnt[m] += 1
    # _is_noise_concept으로 한 번 더 거르고
    cand = [(w, c) for w, c in cnt.most_common(top_n * 3) if not _is_noise_concept(w)]
    return [w for w, c in cand[:top_n] if c >= min_freq]


def _first_sentences(text: str, n: int = 2) -> str:
    parts = re.split(r"(?<=[.!?。!?])\s+", text.strip())
    return " ".join(parts[:n]).strip()


def aggregate(topic: str, aliases: list[str] | None = None) -> dict:
    tdir = topic_dir(topic)
    raw_path = tdir / "raw_hits.jsonl"
    if not raw_path.exists():
        print(f"[aggregate] {raw_path} 없음 — 먼저 discover 단계를 돌려라", file=sys.stderr)
        sys.exit(1)

    topic_tokens = _token_groups(topic, aliases)
    if aliases:
        print(f"[aggregate] aliases={aliases}  → token groups={topic_tokens}")

    hits = list(read_jsonl(raw_path))
    if not hits:
        print("[aggregate] raw_hits.jsonl 비어 있음", file=sys.stderr)
        sys.exit(1)

    # --- 1) URL 단위 중복 제거 → sources 1차
    by_url: dict[str, dict] = {}
    for h in hits:
        url = h["url"]
        if url not in by_url:
            by_url[url] = dict(h)
        else:
            cur = by_url[url]
            # abstract는 더 긴 거 채택, concepts는 union
            if len(h.get("abstract", "")) > len(cur.get("abstract", "")):
                cur["abstract"] = h["abstract"]
            cur_concepts = list(cur.get("concepts", []))
            for c in h.get("concepts", []):
                if c not in cur_concepts:
                    cur_concepts.append(c)
            cur["concepts"] = cur_concepts
            # year/authors/language도 비어 있으면 보완
            for k in ("year", "authors", "language", "parent_concept"):
                if not cur.get(k) and h.get(k):
                    cur[k] = h[k]

    # sources 만들기 전에 offtopic 계산 (concept 단계와 동일 규칙)
    irrelevant_urls_provisional: set[str] = set()
    for url, h in by_url.items():
        if not _hit_relevant(h.get("title", ""), h.get("abstract", ""), topic_tokens):
            irrelevant_urls_provisional.add(url)

    sources = []
    for i, (_, h) in enumerate(sorted(by_url.items()), start=1):
        sid = f"src_{i:03d}"
        base_auth = authority_of(h["type"])
        score = h.get("score")
        auth = _authority_from_score(base_auth, h["type"], score)
        is_offtopic = h["url"] in irrelevant_urls_provisional
        if is_offtopic:
            auth = "low"
        src = {
            "id": sid,
            "topic": topic,
            "url": h["url"],
            "title": h["title"],
            "type": h["type"],
            "authority": auth,
            "abstract": h.get("abstract", ""),
            "concepts": list(h.get("concepts", [])),
            "domain": h.get("domain", ""),
            "score": score,
            "offtopic": is_offtopic,
            "text_path": None,
            "text_mode": "none",
            "text_bytes": 0,
            "enrich_policy": None,
            "enriched_at": None,
        }
        for k in ("year", "authors", "language", "source_domain"):
            if h.get(k):
                src[k] = h[k]
        # raw_body는 enrich가 활용 (sources.jsonl에 박지 않고 _from_hit으로 raw_hits 역참조 가능)
        src["_from_hit"] = h.get("id")
        sources.append(src)

    # url → src_id 매핑
    url_to_sid = {s["url"]: s["id"] for s in sources}

    # --- 2) concepts 통합
    # (a-pre) 모든 type 동일하게: _hit_relevant_to_topic으로 1차 필터
    irrelevant_urls: set[str] = set()
    for h in hits:
        if not _hit_relevant(h.get("title", ""), h.get("abstract", ""), topic_tokens):
            irrelevant_urls.add(h["url"])

    # (a-pre2) body 키워드 후보 — 자주 나오는 명사구를 hit의 concepts에 보강
    #          단, 관련 있는 hit의 abstract만 합쳐서 키워드 추출
    relevant_text = "\n".join(
        h.get("abstract", "") for h in hits if h["url"] not in irrelevant_urls
    )
    body_kw = _keyword_candidates(relevant_text, top_n=15)
    body_kw = [k for k in body_kw if k.lower() != topic.lower()]

    # 각 hit이 다루는 키워드를 그 hit의 concepts에 살짝 추가 (관련 있는 hit만)
    for h in hits:
        if h["url"] in irrelevant_urls:
            continue
        text = h.get("abstract", "") + " " + h.get("title", "")
        for kw in body_kw:
            if kw in text and kw not in h.get("concepts", []):
                h.setdefault("concepts", []).append(kw)

    # (a) 모든 concept 등장 수집 — irrelevant_urls 제외 + 노이즈 concept 필터
    concept_sources: dict[str, list[str]] = defaultdict(list)
    concept_parent_votes: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for h in hits:
        if h["url"] in irrelevant_urls:
            continue
        sid = url_to_sid[h["url"]]
        cs = [c for c in h.get("concepts", []) if not _is_noise_concept(c)]
        for c in cs:
            if sid not in concept_sources[c]:
                concept_sources[c].append(sid)
        # parent_concept 명시 → 표만 표시
        pc = h.get("parent_concept")
        if pc and cs and not _is_noise_concept(pc):
            head = cs[0]
            if head != pc:
                concept_parent_votes[head][pc] += 1
        if len(cs) >= 2:
            head = cs[0]
            for c in cs[1:]:
                if c != head:
                    concept_parent_votes[c][head] += 1

    # (b) parent 결정 — 표 다수결, 없으면 None (= 루트 직속)
    concept_parent: dict[str, str | None] = {}
    for c in concept_sources:
        votes = concept_parent_votes.get(c, {})
        if not votes:
            concept_parent[c] = None
            continue
        parent = max(votes.items(), key=lambda kv: kv[1])[0]
        # 자기 자신은 부모로 두지 않음
        if parent == c:
            concept_parent[c] = None
        else:
            concept_parent[c] = parent

    # (c) cycle 방지: 부모를 따라가다 자기로 돌아오면 부모를 None으로 강등
    def resolves(c: str) -> bool:
        seen = {c}
        cur = concept_parent.get(c)
        while cur is not None:
            if cur in seen:
                return False
            seen.add(cur)
            cur = concept_parent.get(cur)
        return True

    for c in list(concept_parent.keys()):
        if not resolves(c):
            concept_parent[c] = None

    # (d) concepts.jsonl 만들기
    concepts = []
    concept_ids: dict[str, str] = {}
    for i, c in enumerate(sorted(concept_sources.keys()), start=1):
        cid = f"c_{i:03d}"
        concept_ids[c] = cid

    # children & related 계산
    children_map: dict[str, list[str]] = defaultdict(list)
    for c, p in concept_parent.items():
        if p:
            children_map[p].append(c)

    for c, sids in concept_sources.items():
        # 정의 합성: 이 개념을 첫 번째 concept으로 둔 source의 abstract 첫 2문장
        head_sources = [s for s in sources if s["concepts"] and s["concepts"][0] == c]
        if head_sources:
            head_sources.sort(key=lambda s: {"high": 0, "medium": 1, "low": 2}[s["authority"]])
            definition = _first_sentences(head_sources[0]["abstract"], n=2)
        else:
            # fallback: 이 개념을 포함한 source 중 권위 높은 것의 첫 문장
            cands = [s for s in sources if c in s["concepts"]]
            cands.sort(key=lambda s: {"high": 0, "medium": 1, "low": 2}[s["authority"]])
            definition = _first_sentences(cands[0]["abstract"], n=1) if cands else ""

        concepts.append({
            "id": concept_ids[c],
            "term": c,
            "definition": definition,
            "parent": concept_parent.get(c),
            "children": sorted(children_map.get(c, [])),
            "related": [],
            "sources": sids,
        })

    # --- 3) hierarchy.json 빌드
    # 외부 parent (concept_sources에 없는 부모 노드)도 트리에 표시
    external_parents: set[str] = set()
    for c, p in concept_parent.items():
        if p is not None and p not in concept_sources:
            external_parents.add(p)
            if c not in children_map[p]:
                children_map[p].append(c)

    def build_subtree(node: str, visited: set | None = None) -> dict:
        visited = visited if visited is not None else set()
        if node in visited:
            return {}
        visited = visited | {node}
        return {child: build_subtree(child, visited) for child in sorted(children_map.get(node, []))}

    internal_roots = [c for c, p in concept_parent.items() if p is None]
    roots = sorted(set(internal_roots) | external_parents)
    hierarchy = {
        "root": topic,
        "tree": {r: build_subtree(r) for r in roots},
    }

    # --- 4) 저장
    n_src = write_jsonl(tdir / "sources.jsonl", sources)
    n_con = write_jsonl(tdir / "concepts.jsonl", concepts)
    (tdir / "hierarchy.json").write_text(
        json.dumps(hierarchy, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"[aggregate] {topic} (slug={tdir.name})")
    print(f"  hits {len(hits)} → sources {n_src}, concepts {n_con}, hierarchy roots {len(roots)}")
    print(f"  out: {tdir}")

    return {
        "sources": n_src,
        "concepts": n_con,
        "roots": len(roots),
    }


def main():
    p = argparse.ArgumentParser(description="raw_hits → sources + concepts + hierarchy")
    p.add_argument("topic")
    p.add_argument("--aliases", help="콤마 구분 alias 토픽 (영문/별칭). 예: 'Physical AI,Embodied AI'")
    args = p.parse_args()
    aliases = [a.strip() for a in args.aliases.split(",")] if args.aliases else None
    aggregate(args.topic, aliases=aliases)
    return 0


if __name__ == "__main__":
    sys.exit(main())
