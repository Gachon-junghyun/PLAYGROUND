"""Crossref REST API fetcher (학술 메타데이터, 무료, 키 X).

agent.fetch와 동일한 시그니처: search(query, limit, **kw) -> List[Dict].
DOI 기반이라 인용·연도·저자가 풍부. abstract는 일부 자료만 제공.
"""

from __future__ import annotations

import datetime as dt
import html
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

from _common import get_ssl_context


USER_AGENT = "PLAY12-concept-corpus/0.1 (mailto:fivepeople201@gmail.com)"
TIMEOUT = 15.0


def _clean_html(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = html.unescape(s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def search(query: str, limit: int = 10, **_) -> list[dict]:
    base = "https://api.crossref.org/works"
    params = {
        "query": query,
        "rows": str(limit),
        "sort": "relevance",
        "select": "DOI,title,abstract,author,published-print,published-online,is-referenced-by-count,container-title,URL",
    }
    url = base + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=get_ssl_context()) as r:
            data = json.loads(r.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
        print(f"  [crossref] 실패: {e}", file=sys.stderr)
        return []

    now = dt.datetime.now(dt.timezone.utc).isoformat()
    out = []
    for item in data.get("message", {}).get("items", []):
        title_list = item.get("title") or []
        title = title_list[0] if title_list else ""
        title = _clean_html(title)
        if not title:
            continue
        doi = item.get("DOI", "")
        url_ = item.get("URL") or (f"https://doi.org/{doi}" if doi else "")
        if not url_:
            continue
        abstract = _clean_html(item.get("abstract", ""))
        authors = [
            f"{a.get('given','')} {a.get('family','')}".strip()
            for a in (item.get("author") or [])[:8]
        ]
        year = None
        for k in ("published-print", "published-online"):
            parts = item.get(k, {}).get("date-parts") or []
            if parts and parts[0]:
                year = parts[0][0]
                break
        citations = item.get("is-referenced-by-count", 0)
        venue = (item.get("container-title") or [""])[0]

        meta_lines = []
        if year:
            meta_lines.append(f"year: {year}")
        meta_lines.append(f"citations: {citations}")
        if authors:
            meta_lines.append(f"authors: {', '.join(authors)}")
        if venue:
            meta_lines.append(f"venue: {venue}")
        if doi:
            meta_lines.append(f"doi: https://doi.org/{doi}")
        body_text = "\n".join(meta_lines + [abstract])

        out.append({
            "url": url_,
            "title": title,
            "body": body_text,
            "source": "crossref",
            "fetched_at": now,
        })
    return out
