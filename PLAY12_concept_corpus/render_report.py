"""render_report — concepts + sources + hierarchy → reports/<slug>.md.

읽을 거리 위주:
- TL;DR + "주요 발견" (휴리스틱 자동 합성)
- 핵심 개념마다 정의 + 여러 source 본문 인용
- 도메인별 자료 섹션에 abstract 직접 인라인
- mermaid 트리 (가지치기 + max-nodes cap)
- offtopic 자료는 별도 섹션
- 출처 인덱스
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from _common import REPORTS_ROOT, read_jsonl, slugify, topic_dir


AUTH_ORDER = {"high": 0, "medium": 1, "low": 2}
TYPE_LABEL = {
    "survey": "서베이/리뷰",
    "standard": "표준",
    "textbook": "교과서",
    "wiki": "위키",
    "paper": "논문",
    "report": "리포트",
    "blog": "블로그",
    "news": "뉴스",
}
DOMAIN_LABEL = {
    "academic": "학술 (국제)",
    "academic_kr": "학술 (한국)",
    "tech": "기술/위키",
    "industry_kr": "산업 (한국)",
    "industry_us": "산업 (미국)",
    "policy_kr": "정책 (한국)",
    "community": "커뮤니티",
    "events": "이벤트/뉴스",
    "custom": "직접 지정",
    "": "기타",
}


_MERMAID_SAFE_RE = re.compile(r"[^A-Za-z0-9가-힣_\-]+")
_SENT_SPLIT = re.compile(r"(?<=[.!?。!?])\s+|\n+")
_META_LINE = re.compile(r"^(year|citations|authors|venue|doi|info|score|comments|tags|site|flair|r/)\s*[:/]", re.I)


def _mid(name: str) -> str:
    return "n_" + _MERMAID_SAFE_RE.sub("_", name)[:40]


def _strip_meta(body: str) -> str:
    """body 텍스트에서 'year: ...', 'doi: ...' 같은 메타 라인 제거 후 본문만 남김."""
    if not body:
        return ""
    lines = []
    for ln in body.splitlines():
        s = ln.strip()
        if not s:
            continue
        if _META_LINE.match(s):
            continue
        lines.append(s)
    return "\n".join(lines).strip()


def _first_sentences(text: str, n: int = 2, max_chars: int = 400) -> str:
    text = _strip_meta(text)
    parts = [p.strip() for p in _SENT_SPLIT.split(text) if p.strip()]
    out = " ".join(parts[:n])
    if len(out) > max_chars:
        out = out[:max_chars].rstrip() + "…"
    return out


def _excerpt(text: str, max_chars: int = 500) -> str:
    text = _strip_meta(text)
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars]
    # 마지막 마침표 또는 공백 기준으로 정리
    for sep in ("。", ".", "!", "?", " "):
        idx = cut.rfind(sep)
        if idx > max_chars * 0.6:
            return cut[: idx + 1].rstrip() + "…"
    return cut.rstrip() + "…"


_BOILERPLATE_HINTS = (
    "메뉴 건너뛰기", "로그인 / 회원가입", "전체삭제", "최근 검색",
    "주제분류", "고객센터", "내서재", "기관회원 로그인",
    "네이버 아이디로 로그인", "카카오 아이디로 로그인", "구글 아이디로 로그인",
    "아이디/비밀번호", "개인회원 가입", "기관로그인",
    "Subscription Inquiry", "Instructions to Authors",
    "Cookies on", "Accept all cookies", "Sign in to", "Subscribe now",
    "JavaScript is required", "Please enable JavaScript",
)


def _looks_boilerplate(text: str) -> bool:
    if not text:
        return False
    hits = sum(1 for kw in _BOILERPLATE_HINTS if kw in text)
    if hits >= 2:
        return True
    # digest의 "[ABSTRACT]\n[EXCERPTS]\n<로그인/UI>..." 패턴
    if text.lstrip().startswith("[ABSTRACT]"):
        head = text[:300]
        if any(kw in head for kw in _BOILERPLATE_HINTS):
            return True
    return False


def _load_text(tdir: Path, src: dict, max_chars: int) -> str:
    """본문 선택 정책:
      - paper/survey/wiki/standard/textbook: abstract가 길면 abstract 우선 (DBpia/Publisher 메뉴 오염 회피)
      - 그 외: text_path 본문 우선, 없으면 abstract
      - text_path 본문이 명백한 boilerplate면 abstract로 폴백
    """
    abstract = src.get("abstract", "")
    type_ = src.get("type", "")
    tp = src.get("text_path")

    prefer_abstract = type_ in ("paper", "survey", "wiki", "standard", "textbook") and len(abstract) >= 150

    if prefer_abstract:
        return _excerpt(abstract, max_chars=max_chars)

    if tp:
        p = tdir / tp
        if p.exists():
            t = p.read_text(encoding="utf-8")
            if _looks_boilerplate(t) and abstract:
                return _excerpt(abstract, max_chars=max_chars)
            return _excerpt(t, max_chars=max_chars)
    return _excerpt(abstract, max_chars=max_chars)


def _prune_tree(tree: dict, concept_support: dict, min_support: int = 1) -> dict:
    pruned = {}
    for k, v in tree.items():
        child = _prune_tree(v, concept_support, min_support) if isinstance(v, dict) else {}
        support = concept_support.get(k, 0)
        if support >= min_support or child:
            pruned[k] = child
    return pruned


def _tree_to_lines(tree: dict, depth: int = 0) -> list[str]:
    lines = []
    for k, v in tree.items():
        lines.append(f"{'  ' * depth}- {k}")
        if isinstance(v, dict) and v:
            lines.extend(_tree_to_lines(v, depth + 1))
    return lines


def _tree_to_mermaid(tree: dict, root_label: str, max_nodes: int = 60) -> list[str]:
    lines = ["```mermaid", "graph TD"]
    root_id = _mid(root_label)
    lines.append(f"  {root_id}([{root_label}])")
    visited: set[str] = set()
    n = [0]

    def walk(parent_id: str, subtree: dict):
        for k, v in subtree.items():
            if n[0] >= max_nodes:
                return
            cid = _mid(k)
            edge = f"  {parent_id} --> {cid}[\"{k}\"]"
            if edge in visited:
                continue
            visited.add(edge)
            lines.append(edge)
            n[0] += 1
            if isinstance(v, dict) and v:
                walk(cid, v)

    walk(root_id, tree)
    if n[0] >= max_nodes:
        lines.append(f"  more[\"...{n[0]}+ nodes truncated\"]")
    lines.append("```")
    return lines


def render(topic: str) -> str:
    tdir = topic_dir(topic)
    concepts = list(read_jsonl(tdir / "concepts.jsonl"))
    sources = list(read_jsonl(tdir / "sources.jsonl"))
    hierarchy_path = tdir / "hierarchy.json"
    hierarchy = (
        json.loads(hierarchy_path.read_text(encoding="utf-8"))
        if hierarchy_path.exists() else {"tree": {}}
    )

    if not concepts and not sources:
        print(f"[render] {tdir}에 데이터 없음", file=sys.stderr)
        sys.exit(1)

    # 통계
    type_counts = Counter(s["type"] for s in sources)
    auth_counts = Counter(s["authority"] for s in sources)
    domain_counts = Counter(s.get("domain") or "" for s in sources)
    text_modes = Counter(s.get("text_mode", "none") for s in sources)

    sid_to_src = {s["id"]: s for s in sources}
    ontopic = [s for s in sources if not s.get("offtopic")]

    lines: list[str] = []
    add = lines.append

    # ── 헤더
    add(f"# {topic}")
    add("")
    add("> 개념 입문서 — `PLAY12_concept_corpus` 자동 생성. evergreen 자료 기반.")
    add("")

    # ── TL;DR
    add("## TL;DR")
    add("")
    add(f"- 토픽: **{topic}**")
    add(f"- 자료 {len(sources)}건 "
        f"(권위 high {auth_counts.get('high', 0)} · medium {auth_counts.get('medium', 0)} · low {auth_counts.get('low', 0)})")
    add(f"- 개념 {len(concepts)}개")
    add(f"- 본문: full {text_modes.get('full', 0)} · digest {text_modes.get('digest', 0)} · none {text_modes.get('none', 0)}")
    add(f"- 도메인 분포: " + ", ".join(
        f"{DOMAIN_LABEL.get(d, d)} {c}" for d, c in domain_counts.most_common()))
    add(f"- 타입 분포: " + ", ".join(
        f"{TYPE_LABEL.get(t, t)} {c}" for t, c in type_counts.most_common()))
    add("")

    # ── 주요 발견 (휴리스틱: 권위 high 자료 우선, 각 1문장씩)
    add("## 주요 발견 (자동 추출)")
    add("")
    add("> 권위·인용 기반으로 정렬된 자료에서 첫 문장씩 뽑아 자동 합성. "
        "이건 LLM 합성이 아니라 단순 발췌라 흐름이 부드럽진 않다. "
        "본격 합성은 `synthesize.py` 단계가 따로 있다.")
    add("")
    ranked = sorted(
        ontopic,
        key=lambda s: (
            AUTH_ORDER[s["authority"]],
            -(s.get("score") or 0),
            -(s.get("year") or 0),
        ),
    )
    for s in ranked[:8]:
        snippet = _first_sentences(s.get("abstract", ""), n=1, max_chars=320)
        if not snippet:
            continue
        meta = []
        if s.get("year"):
            meta.append(str(s["year"]))
        if s.get("score") is not None:
            meta.append(f"score {s['score']}")
        meta.append(s["authority"].upper())
        meta_str = " · ".join(meta)
        add(f"- {snippet}  ")
        add(f"  — [{s['title']}]({s['url']}) ({meta_str}, [{s['id']}](#{s['id']}))")
    add("")

    # ── 개념 지도
    concept_support = {c["term"]: len(c.get("sources", [])) for c in concepts}
    raw_tree = hierarchy.get("tree", {})
    tree = _prune_tree(raw_tree, concept_support, min_support=2) if raw_tree else {}

    add("## 개념 지도")
    add("")
    add("```")
    add(f"{hierarchy.get('root', topic)}")
    if tree:
        for line in _tree_to_lines(tree, depth=1):
            add(line)
    else:
        add("  (관련도 높은 개념 부족 — sources 인용수 1회뿐인 가지는 숨김)")
    add("```")
    add("")

    if tree:
        add("### Mermaid 다이어그램")
        add("")
        lines.extend(_tree_to_mermaid(tree, hierarchy.get("root", topic)))
        add("")

    # ── 핵심 개념 (정의 + 본문 발췌 여러 source)
    add("## 핵심 개념")
    add("")

    def concept_score(c):
        n_src = len(c.get("sources", []))
        n_child = len(c.get("children", []))
        hi = sum(1 for sid in c["sources"] if sid_to_src.get(sid, {}).get("authority") == "high")
        return -(hi * 3 + n_src + n_child * 2)

    notable = [c for c in concepts if len(c.get("sources", [])) >= 2 or c.get("children")]
    for c in sorted(notable, key=concept_score)[:25]:
        term = c["term"]
        parent = c.get("parent")
        add(f"### {term}")
        if parent:
            add(f"*상위 개념:* `{parent}`")
        if c.get("children"):
            add(f"*하위 개념:* " + ", ".join(f"`{x}`" for x in c["children"][:10]))

        if c.get("definition"):
            add("")
            add(_first_sentences(c["definition"], n=3, max_chars=500))

        # 이 개념을 다루는 source의 본문에서 발췌 (권위 순으로 최대 3개)
        cited_sources = [sid_to_src[sid] for sid in c.get("sources", []) if sid in sid_to_src]
        cited_sources = [s for s in cited_sources if not s.get("offtopic")]
        cited_sources.sort(key=lambda s: (AUTH_ORDER[s["authority"]], -(s.get("score") or 0)))
        excerpts = cited_sources[:3]
        if excerpts:
            add("")
            add("**관련 자료 발췌:**")
            for s in excerpts:
                snippet = _load_text(tdir, s, max_chars=320)
                if not snippet:
                    continue
                add(f"- [{s['id']}](#{s['id']}) _{s['title'][:80]}_  ")
                # 인용 블록으로
                for ln in snippet.splitlines():
                    add(f"  > {ln}")

        if c.get("sources"):
            add("")
            cited = [f"[{sid}](#{sid})" for sid in c["sources"][:8]]
            extra = f" 외 {len(c['sources'])-8}건" if len(c["sources"]) > 8 else ""
            add("*근거:* " + ", ".join(cited) + extra)
        add("")

    # ── 도메인별 자료 (offtopic 제외) + abstract 인라인
    add("## 자료 (도메인별, 본문 발췌 포함)")
    add("")
    by_domain: dict[str, list[dict]] = defaultdict(list)
    offtopic_sources: list[dict] = []
    for s in sources:
        if s.get("offtopic"):
            offtopic_sources.append(s)
        else:
            by_domain[s.get("domain") or ""].append(s)

    domain_order = ["academic", "academic_kr", "industry_kr", "industry_us",
                    "policy_kr", "tech", "community", "events", "custom", ""]
    for d in domain_order:
        bucket = by_domain.get(d, [])
        if not bucket:
            continue
        add(f"### {DOMAIN_LABEL.get(d, d)} ({len(bucket)})")
        add("")
        bucket_sorted = sorted(
            bucket,
            key=lambda s: (
                AUTH_ORDER[s["authority"]],
                -(s.get("score") or 0),
                -(s.get("year") or 0),
            )
        )
        for s in bucket_sorted:
            yr = f" ({s['year']})" if s.get("year") else ""
            sc = f" · score {s['score']}" if s.get("score") is not None else ""
            auth = s["authority"].upper()
            tlabel = TYPE_LABEL.get(s["type"], s["type"])
            tm = s.get("text_mode", "none")
            add(f"#### [{s['id']}](#{s['id']}) {s['title']}{yr}")
            add(f"_{tlabel}_, {auth}{sc}, 본문 `{tm}` — <{s['url']}>")
            snippet = _load_text(tdir, s, max_chars=600)
            if snippet:
                add("")
                for ln in snippet.splitlines():
                    add(f"> {ln}")
            add("")
        add("")

    # ── offtopic
    if offtopic_sources:
        add(f"### 토픽 무관 (자동 분류, {len(offtopic_sources)})")
        add("")
        add("> 검색 백엔드(주로 wiki fuzzy match)가 가져왔지만 토픽 키워드가 본문에 없어 _자동 제외된_ 항목.")
        add("")
        for s in offtopic_sources[:15]:
            add(f"- ~~{s['title']}~~ — {s['url']}")
        if len(offtopic_sources) > 15:
            add(f"- … 외 {len(offtopic_sources)-15}건")
        add("")

    # ── 출처 인덱스
    add("## 출처 인덱스")
    add("")
    add("| ID | 도메인 | 권위 | 타입 | score | 본문 | 제목 |")
    add("|---|---|---|---|---|---|---|")
    for s in sorted(sources, key=lambda s: s["id"]):
        tm = s.get("text_mode", "none")
        tm_disp = {"full": "full", "digest": "digest", "none": "—"}.get(tm, tm)
        title = s["title"].replace("|", "\\|").replace("\n", " ")
        d = s.get("domain") or "—"
        sc = s.get("score")
        sc_disp = sc if sc is not None else "—"
        add(f"| <a id=\"{s['id']}\"></a>`{s['id']}` | {d} | {s['authority']} | {s['type']} | {sc_disp} | {tm_disp} | [{title}]({s['url']}) |")
    add("")

    out_path = REPORTS_ROOT / f"{tdir.name}.md"
    REPORTS_ROOT.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[render] {out_path}  ({len(lines)} lines)")
    return str(out_path)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("topic")
    args = p.parse_args()
    render(args.topic)
    return 0


if __name__ == "__main__":
    sys.exit(main())
