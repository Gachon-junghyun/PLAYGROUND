"""Google Scholar fetcher.

전략 우선순위:
  1) SERPAPI_KEY 환경변수가 있으면 SerpAPI의 Google Scholar engine 사용 (안정적)
  2) 그게 없으면 `scholarly` 라이브러리 (설치돼 있고 차단 안 됐을 때만 동작)
  3) 둘 다 안 되면 빈 결과 반환 + 안내

agent.fetch와 동일한 시그니처: search(query, limit, **kw) -> List[Dict].
"""

from __future__ import annotations

import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

from _common import get_ssl_context


USER_AGENT = "PLAY12-concept-corpus/0.1 (scholar)"
TIMEOUT = 20.0


def _serpapi_search(query: str, limit: int) -> list[dict]:
    key = os.environ.get("SERPAPI_KEY")
    if not key:
        return []
    params = {
        "engine": "google_scholar",
        "q": query,
        "num": str(min(limit, 20)),
        "api_key": key,
    }
    url = "https://serpapi.com/search?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=get_ssl_context()) as r:
            data = json.loads(r.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
        print(f"  [scholar/serpapi] 실패: {e}", file=sys.stderr)
        return []

    now = dt.datetime.now(dt.timezone.utc).isoformat()
    out = []
    for r in data.get("organic_results", []):
        url_ = r.get("link") or ""
        title = r.get("title") or ""
        snippet = r.get("snippet") or ""
        if not url_ or not title:
            continue
        info = r.get("publication_info", {}) or {}
        summary = info.get("summary", "")
        citation_count = (r.get("inline_links", {}).get("cited_by", {}) or {}).get("total")
        meta = []
        if summary:
            meta.append(f"info: {summary}")
        if citation_count is not None:
            meta.append(f"citations: {citation_count}")
        body = "\n".join(meta + [snippet])
        out.append({
            "url": url_,
            "title": title,
            "body": body,
            "source": "scholar_serpapi",
            "fetched_at": now,
        })
    return out


def _scholarly_search(query: str, limit: int) -> list[dict]:
    try:
        from scholarly import scholarly
    except ImportError:
        print("  [scholar] scholarly 미설치 — `pip install scholarly`로 설치 시 사용 가능", file=sys.stderr)
        return []
    try:
        gen = scholarly.search_pubs(query)
    except Exception as e:
        print(f"  [scholar/scholarly] 검색 시작 실패: {type(e).__name__}: {e}", file=sys.stderr)
        return []

    now = dt.datetime.now(dt.timezone.utc).isoformat()
    out = []
    try:
        for _ in range(limit):
            try:
                r = next(gen)
            except StopIteration:
                break
            bib = r.get("bib", {}) or {}
            title = (bib.get("title") or "").strip()
            abstract = (bib.get("abstract") or "").strip()
            year = bib.get("pub_year")
            authors = bib.get("author") or []
            citations = r.get("num_citations", 0)
            url_ = r.get("pub_url") or r.get("eprint_url") or ""
            if not url_ or not title:
                continue
            meta = []
            if year:
                meta.append(f"year: {year}")
            meta.append(f"citations: {citations}")
            if authors:
                if isinstance(authors, str):
                    authors_str = authors
                else:
                    authors_str = ", ".join(authors[:8])
                meta.append(f"authors: {authors_str}")
            body = "\n".join(meta + [abstract])
            out.append({
                "url": url_,
                "title": title,
                "body": body,
                "source": "scholar_scholarly",
                "fetched_at": now,
            })
    except Exception as e:
        # 차단·예외 시 그때까지 모은 것만 반환
        print(f"  [scholar/scholarly] 중단: {type(e).__name__}: {str(e)[:120]}", file=sys.stderr)
    return out


def search(query: str, limit: int = 10, **_) -> list[dict]:
    # 1) SerpAPI
    res = _serpapi_search(query, limit)
    if res:
        return res
    # 2) scholarly
    return _scholarly_search(query, limit)
