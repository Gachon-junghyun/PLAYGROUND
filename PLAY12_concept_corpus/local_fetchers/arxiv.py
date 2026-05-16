"""arxiv.org Atom API fetcher.

agent.fetch와 동일한 시그니처: search(query, limit, **kw) -> List[Dict].
반환 dict 키: url, title, body, source, fetched_at
"""

from __future__ import annotations

import datetime as dt
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from _common import get_ssl_context


USER_AGENT = "PLAY12-concept-corpus/0.1 (arxiv)"
TIMEOUT = 15.0
ATOM_NS = {"a": "http://www.w3.org/2005/Atom"}


def search(query: str, limit: int = 10, **_) -> list[dict]:
    base = "https://export.arxiv.org/api/query"
    params = {
        "search_query": f"all:{query}",
        "start": "0",
        "max_results": str(limit),
        "sortBy": "relevance",
        "sortOrder": "descending",
    }
    url = base + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    body = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT, context=get_ssl_context()) as r:
                body = r.read().decode("utf-8")
            break
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 2:
                time.sleep(3.0)
                continue
            print(f"  [arxiv] HTTP {e.code}: {e}", file=sys.stderr)
            return []
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            print(f"  [arxiv] 실패: {e}", file=sys.stderr)
            return []
    if not body:
        return []

    try:
        root = ET.fromstring(body)
    except ET.ParseError as e:
        print(f"  [arxiv] XML 파싱 실패: {e}", file=sys.stderr)
        return []

    now = dt.datetime.now(dt.timezone.utc).isoformat()
    out = []
    for entry in root.findall("a:entry", ATOM_NS):
        title_el = entry.find("a:title", ATOM_NS)
        summary_el = entry.find("a:summary", ATOM_NS)
        published_el = entry.find("a:published", ATOM_NS)
        if title_el is None or summary_el is None:
            continue
        title = re.sub(r"\s+", " ", (title_el.text or "").strip())
        summary = re.sub(r"\s+", " ", (summary_el.text or "").strip())
        if not title or not summary:
            continue

        abs_url = None
        for link in entry.findall("a:link", ATOM_NS):
            if link.get("rel") == "alternate" and link.get("type") == "text/html":
                abs_url = link.get("href")
                break
        if not abs_url:
            id_el = entry.find("a:id", ATOM_NS)
            abs_url = (id_el.text or "").strip() if id_el is not None else None
        if not abs_url:
            continue

        authors = [
            (a.find("a:name", ATOM_NS).text or "").strip()
            for a in entry.findall("a:author", ATOM_NS)
            if a.find("a:name", ATOM_NS) is not None
        ]
        year = None
        if published_el is not None and published_el.text:
            m = re.match(r"(\d{4})", published_el.text)
            if m:
                year = int(m.group(1))

        # body는 agent.fetch와 동일한 멀티라인 형태로 구성 (year/authors 등 메타 prefix)
        meta_lines = []
        if year:
            meta_lines.append(f"year: {year}")
        if authors:
            meta_lines.append(f"authors: {', '.join(authors[:8])}")
        meta_lines.append(f"venue: arxiv.org")
        body_text = "\n".join(meta_lines + [summary])

        out.append({
            "url": abs_url,
            "title": title,
            "body": body_text,
            "source": "arxiv",
            "fetched_at": now,
        })
    return out
