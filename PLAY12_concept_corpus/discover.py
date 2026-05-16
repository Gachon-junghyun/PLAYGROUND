"""discover — raw_hits.jsonl 채우기.

`agent.fetch` 패키지(설치된 crawling 모듈)의 fetcher들을 dispatch한다.
모든 fetcher는 `search(query, limit, **kw) -> List[Dict{url,title,body,source,fetched_at}]` 통일 시그니처.

도메인 프로파일로 여러 백엔드를 묶어서 한 번에 굴린다:
  --domains academic        : OpenAlex + Semantic Scholar + Wikipedia(en)
  --domains tech            : Wikipedia(ko+en) + StackExchange
  --domains policy_kr       : KOSIS + BOK ECOS (한국 통계·경제)
  --domains industry_kr     : DART + RSS (한국 기업 공시)
  --domains industry_us     : SEC EDGAR + RSS
  --domains community       : Reddit + StackExchange + YouTube
  --domains events          : GDELT + RSS (보조)
  --domains all             : 위 전부 (키 필요한 건 자동 스킵)

백엔드 직접 지정:
  --backends wikipedia:ko,openalex,reddit

데모용:
  --sample / --validate
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import traceback

from _common import append_jsonl, read_jsonl, set_ssl_verify, topic_dir


# ============================ 백엔드 dispatch ============================

def _search_dispatch(backend: str, query: str, limit: int) -> list[dict]:
    """backend 이름 → agent.fetch 모듈의 search() 호출."""
    if backend == "wikipedia:ko":
        from agent.fetch import wikipedia
        return wikipedia.search(query, limit=limit, lang="ko")
    if backend == "wikipedia:en":
        from agent.fetch import wikipedia
        return wikipedia.search(query, limit=limit, lang="en")
    if backend == "openalex":
        from agent.fetch import openalex
        return openalex.search(query, limit=limit)
    if backend == "semantic_scholar":
        from agent.fetch import semantic_scholar
        return semantic_scholar.search(query, limit=limit)
    if backend == "reddit":
        from agent.fetch import reddit
        return reddit.search(query, limit=limit)
    if backend == "stackexchange":
        from agent.fetch import stackexchange
        return stackexchange.search(query, limit=limit)
    if backend == "dart":
        from agent.fetch import dart
        return dart.search(query, limit=limit)
    if backend == "sec_edgar":
        from agent.fetch import sec_edgar
        return sec_edgar.search(query, limit=limit)
    if backend == "kosis":
        from agent.fetch import kosis
        return kosis.search(query, limit=limit)
    if backend == "bok_ecos":
        from agent.fetch import bok_ecos
        return bok_ecos.search(query, limit=limit)
    if backend == "gdelt":
        from agent.fetch import gdelt
        return gdelt.search(query, limit=limit)
    if backend == "rss":
        from agent.fetch import rss
        return rss.search(query, limit=limit)
    if backend == "youtube":
        from agent.fetch import youtube
        return youtube.search(query, limit=limit)
    # --- local_fetchers (PLAY12 자체 fetcher) ---
    if backend == "arxiv":
        from local_fetchers import arxiv
        return arxiv.search(query, limit=limit)
    if backend == "scholar":
        from local_fetchers import scholar
        return scholar.search(query, limit=limit)
    if backend == "dbpia":
        from local_fetchers import dbpia
        return dbpia.search(query, limit=limit)
    if backend == "crossref":
        from local_fetchers import crossref
        return crossref.search(query, limit=limit)
    raise ValueError(f"알 수 없는 백엔드: {backend}")


# ============================ 어댑터 (search 결과 → raw_hit) ============================

# (backend) → (raw_hit type, default language). language=""면 본문에서 추정.
BACKEND_META = {
    "wikipedia:ko":      ("wiki",     "ko"),
    "wikipedia:en":      ("wiki",     "en"),
    "openalex":          ("paper",    "en"),
    "semantic_scholar":  ("paper",    "en"),
    "arxiv":             ("paper",    "en"),
    "scholar":           ("paper",    ""),
    "crossref":          ("paper",    ""),
    "dbpia":             ("paper",    "ko"),
    "reddit":            ("blog",     ""),
    "stackexchange":     ("blog",     "en"),
    "dart":              ("report",   "ko"),
    "sec_edgar":         ("report",   "en"),
    "kosis":             ("report",   "ko"),
    "bok_ecos":          ("report",   "ko"),
    "gdelt":             ("news",     ""),
    "rss":               ("news",     ""),
    "youtube":           ("blog",     ""),
}

_HANGUL = __import__("re").compile(r"[가-힣]")


def _guess_lang(text: str) -> str:
    return "ko" if _HANGUL.search(text or "") else "en"


_SURVEY_RE = __import__("re").compile(
    r"\b(survey|review|overview|tutorial|comprehensive|state[- ]of[- ]the[- ]art)\b",
    __import__("re").I,
)
_STANDARD_RE = __import__("re").compile(
    r"\b(IEC|IEEE Std|ISO/IEC|RFC \d+|standard for|specification)\b",
    __import__("re").I,
)


def _refine_type(type_: str, title: str, body: str) -> str:
    """title/body에 survey·review·standard 표지가 있으면 type을 격상."""
    blob = f"{title}\n{body[:500]}"
    if type_ == "paper" and _SURVEY_RE.search(blob):
        return "survey"
    if _STANDARD_RE.search(blob):
        return "standard"
    return type_


def _extract_score(rec: dict, backend: str, body: str) -> int | None:
    """백엔드별 인기/인용 스코어 추출. body 텍스트에서 정규식 + 백엔드 특수 규칙."""
    import re
    # openalex / semantic_scholar: body에 "citations: 1234" 패턴
    m = re.search(r"citations[:\s]+(\d+)", body)
    if m:
        return int(m.group(1))
    # reddit / stackexchange: body에 "score: 1234"
    m = re.search(r"score[:\s]+(\d+)", body)
    if m:
        return int(m.group(1))
    return None


def _extract_year(body: str) -> int | None:
    import re
    m = re.search(r"year[:\s]+(\d{4})", body)
    if m:
        return int(m.group(1))
    return None


def adapt(rec: dict, backend: str, topic: str, domain: str) -> dict | None:
    url = rec.get("url")
    title = rec.get("title")
    body = (rec.get("body") or "").strip()
    if not url or not title:
        return None
    type_, lang = BACKEND_META.get(backend, ("blog", ""))
    if not lang:
        lang = _guess_lang(title + " " + body)

    type_ = _refine_type(type_, title, body)

    # concept 추정: wiki는 페이지 제목 = 개념. 그 외는 토픽만.
    concepts = [topic]
    if backend.startswith("wikipedia"):
        t = title.strip()
        if t and t != topic:
            concepts = [t, topic]

    score = _extract_score(rec, backend, body)
    year = _extract_year(body)

    hit = {
        "url": url,
        "title": title,
        "type": type_,
        "language": lang,
        "abstract": body[:2000],
        "raw_body": body,            # enrich가 이중 fetch 없이 재활용
        "concepts": concepts,
        "parent_concept": topic,
        "source_domain": rec.get("source") or backend,
        "domain": domain,
        "_fetched_at": rec.get("fetched_at"),
    }
    if score is not None:
        hit["score"] = score
    if year is not None:
        hit["year"] = year
    return hit


# ============================ 도메인 프로파일 ============================

DOMAINS: dict[str, list[str]] = {
    "academic":     ["openalex", "semantic_scholar", "arxiv", "crossref", "scholar", "wikipedia:en"],
    "academic_kr":  ["dbpia"],  # 한국 학술 (KCI Open API 키 있으면 활성)
    "tech":         ["wikipedia:ko", "wikipedia:en", "stackexchange"],
    "industry_kr":  ["dart", "rss"],
    "industry_us":  ["sec_edgar", "rss"],
    "policy_kr":    ["kosis", "bok_ecos"],
    "community":    ["reddit", "stackexchange", "youtube"],
    "events":       ["gdelt", "rss"],
}


def resolve_backends(domains: list[str], backends_arg: str | None) -> list[tuple[str, str]]:
    """(backend, domain_tag) 리스트로 정규화. 중복 backend는 첫 등장 도메인만 유지."""
    pairs: list[tuple[str, str]] = []
    seen: set[str] = set()

    if backends_arg:
        for b in [x.strip() for x in backends_arg.split(",") if x.strip()]:
            if b in seen:
                continue
            seen.add(b)
            pairs.append((b, "custom"))

    for d in domains:
        if d == "all":
            for dn, bs in DOMAINS.items():
                for b in bs:
                    if b in seen:
                        continue
                    seen.add(b)
                    pairs.append((b, dn))
        elif d in DOMAINS:
            for b in DOMAINS[d]:
                if b in seen:
                    continue
                seen.add(b)
                pairs.append((b, d))
        else:
            print(f"  [warn] 알 수 없는 도메인: {d}", file=sys.stderr)
    return pairs


# ============================ search 실행 ============================

# 쿼리 multi-variant: 토픽 + 변형들. 백엔드 종류별로 다른 suffix를 쓰는 게 자연스럽지만
# 단순화 위해 도메인 그룹별로 한 묶음씩 적용.
QUERY_VARIANTS = {
    "academic":     ["{T}", "{T} survey", "{T} review"],
    "academic_kr":  ["{T}", "{T} 연구", "{T} 동향"],
    "tech":         ["{T}", "{T} tutorial"],
    "industry_kr":  ["{T}", "{T} 시장", "{T} 산업"],
    "industry_us":  ["{T}", "{T} market", "{T} industry"],
    "policy_kr":    ["{T}", "{T} 정책", "{T} 규제"],
    "community":    ["{T}"],
    "events":       ["{T}"],
    "custom":       ["{T}"],
}


def _variants_for(domain: str, topic: str, enabled: bool) -> list[str]:
    if not enabled:
        return [topic]
    tpl = QUERY_VARIANTS.get(domain, ["{T}"])
    return [t.format(T=topic) for t in tpl]


def cmd_search(topic: str, plan: list[tuple[str, str]], limit: int,
               variants: bool, sleep_between: float) -> int:
    tdir = topic_dir(topic)
    rh_path = tdir / "raw_hits.jsonl"
    seen_urls = {h["url"] for h in read_jsonl(rh_path)}
    next_id = sum(1 for _ in read_jsonl(rh_path)) + 1

    all_new: list[dict] = []

    for backend, domain in plan:
        queries = _variants_for(domain, topic, variants)
        backend_added = 0
        backend_raw = 0
        t0 = time.time()
        for qi, q in enumerate(queries):
            if qi > 0 and sleep_between > 0:
                time.sleep(sleep_between)
            try:
                results = _search_dispatch(backend, q, limit)
            except Exception as e:
                # 429면 좀 더 길게 쉬고 다음 쿼리
                msg = str(e)
                if "429" in msg:
                    print(f"  [{backend:<18}] q={q!r} 429 — backoff 3s", file=sys.stderr)
                    time.sleep(3.0)
                else:
                    print(f"  [{backend:<18}] q={q!r} 실패: {type(e).__name__}: {e}", file=sys.stderr)
                continue
            backend_raw += len(results)
            for rec in results:
                h = adapt(rec, backend, topic, domain)
                if not h:
                    continue
                if h["url"] in seen_urls:
                    continue
                seen_urls.add(h["url"])
                h["id"] = f"hit_{next_id:03d}"
                h["topic"] = topic
                h["_query"] = q
                next_id += 1
                all_new.append(h)
                backend_added += 1
        dt = time.time() - t0
        print(f"  [{backend:<18}] domain={domain:<11} queries={len(queries)} raw={backend_raw:>3d}  new={backend_added:>3d}  ({dt:.1f}s)")

    n = append_jsonl(rh_path, all_new)
    print(f"[discover] +{n} new hits → {rh_path}")
    print(f"  (총 {next_id - 1}개)")
    return 0 if n > 0 else 2


# ============================ sample (오프라인 시연용) ============================

SAMPLE_HITS = [
    {
        "url": "https://example.org/sample-survey",
        "title": "A Survey (sample)",
        "type": "survey", "year": 2022, "language": "en",
        "abstract": "This is a sample survey entry used for offline demo.",
        "concepts": ["sample"],
        "parent_concept": "sample",
        "source_domain": "example.org",
        "domain": "academic",
    },
]


def cmd_sample(topic: str) -> int:
    tdir = topic_dir(topic)
    rh_path = tdir / "raw_hits.jsonl"
    seen = {h["url"] for h in read_jsonl(rh_path)}
    start = sum(1 for _ in read_jsonl(rh_path))
    new = []
    for i, base in enumerate(SAMPLE_HITS, start=start + 1):
        if base["url"] in seen:
            continue
        h = dict(base)
        h["id"] = f"hit_{i:03d}"
        h["topic"] = topic
        new.append(h)
    n = append_jsonl(rh_path, new)
    print(f"[sample] +{n} hits → {rh_path}")
    return 0


def cmd_validate(topic: str) -> int:
    tdir = topic_dir(topic)
    rh_path = tdir / "raw_hits.jsonl"
    if not rh_path.exists():
        print(f"[validate] {rh_path} 없음", file=sys.stderr)
        return 1
    required = {"id", "url", "title", "type", "abstract", "concepts"}
    valid_types = {"survey", "standard", "textbook", "wiki", "paper", "blog", "report", "news"}
    errors = []
    ids, urls = set(), set()
    n = 0
    for i, hit in enumerate(read_jsonl(rh_path), start=1):
        n += 1
        missing = required - hit.keys()
        if missing:
            errors.append(f"line {i}: missing {missing}")
        if hit.get("type") not in valid_types:
            errors.append(f"line {i}: bad type {hit.get('type')!r}")
        if hit.get("id") in ids:
            errors.append(f"line {i}: duplicate id {hit.get('id')}")
        ids.add(hit.get("id"))
        if hit.get("url") in urls:
            errors.append(f"line {i}: duplicate url {hit.get('url')}")
        urls.add(hit.get("url"))
    print(f"[validate] {n} hits, {len(errors)} errors")
    for e in errors[:20]:
        print(f"  - {e}")
    return 0 if not errors else 1


# ============================ CLI ============================

DEFAULT_DOMAINS = ["academic", "tech"]


def main():
    p = argparse.ArgumentParser(description="agent.fetch 기반 도메인별 검색")
    p.add_argument("topic")
    p.add_argument("--domains", default=",".join(DEFAULT_DOMAINS),
                   help=f"콤마 구분. {','.join(DOMAINS.keys())},all. 기본: {','.join(DEFAULT_DOMAINS)}")
    p.add_argument("--backends",
                   help="도메인 무시하고 백엔드 직접 지정 (콤마 구분). 도메인과 함께 쓰면 둘 다 적용.")
    p.add_argument("--limit", type=int, default=10, help="백엔드당 결과 개수")
    p.add_argument("--sample", action="store_true", help="외부 호출 없이 더미 추가")
    p.add_argument("--validate", action="store_true", help="raw_hits.jsonl 검증")
    p.add_argument("--list-domains", action="store_true", help="도메인/백엔드 목록 출력 후 종료")
    p.add_argument("--no-variants", action="store_true", help="쿼리 multi-variant 비활성화 (토픽 그대로만)")
    p.add_argument("--sleep-between", type=float, default=0.5,
                   help="쿼리 사이 sleep 초 (rate limit 완화). 기본 0.5")
    p.add_argument("--insecure", action="store_true",
                   help="SSL 인증서 검증 비활성화 (Windows 시스템 CA 못 잡을 때)")
    args = p.parse_args()

    if args.insecure:
        set_ssl_verify(False)

    if args.list_domains:
        for d, bs in DOMAINS.items():
            print(f"  {d:<13} → {', '.join(bs)}")
        return 0

    if args.validate:
        return cmd_validate(args.topic)
    if args.sample:
        return cmd_sample(args.topic)

    domains = [d.strip() for d in args.domains.split(",") if d.strip()]
    plan = resolve_backends(domains, args.backends)
    if not plan:
        print("실행할 백엔드 없음", file=sys.stderr)
        return 1
    print(f"[discover] topic={args.topic!r}  plan={[b for b,_ in plan]}  variants={not args.no_variants}")
    return cmd_search(args.topic, plan, args.limit, variants=not args.no_variants,
                      sleep_between=args.sleep_between)


if __name__ == "__main__":
    sys.exit(main())
