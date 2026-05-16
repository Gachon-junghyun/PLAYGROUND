"""DBpia 검색 fetcher (best-effort).

DBpia (https://www.dbpia.co.kr/) 공식 Open API 없음. 검색 페이지가 SPA(JS 렌더링)라
일반 HTML 스크래핑으로는 결과가 잘 안 잡힌다. 그래도 토픽에 따라 일부 잡히는 경우가 있어
시도는 한다. 진짜 한국 학술 자료가 필요하면 KCI Open API(키 신청 후)를 추가 추천.

agent.fetch와 동일한 시그니처: search(query, limit, **kw) -> List[Dict].
KCI_OPEN_API_KEY 환경변수가 있으면 KCI Open API를 우선 시도.
"""

from __future__ import annotations

import datetime as dt
import html
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from _common import get_ssl_context


USER_AGENT = "Mozilla/5.0 (PLAY12-concept-corpus)"
TIMEOUT = 15.0


def _clean(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def _kci_search(query: str, limit: int) -> list[dict]:
    """KCI(한국학술지인용색인) Open API. 키 필요."""
    key = os.environ.get("KCI_OPEN_API_KEY")
    if not key:
        return []
    # KCI Open API: 논문 검색
    # https://open.kci.go.kr/po/openapi/openApiSearch.kci?apiCode=articleSearch&...
    params = {
        "apiCode": "articleSearch",
        "key": key,
        "title": query,
        "displayCount": str(limit),
    }
    url = "https://open.kci.go.kr/po/openapi/openApiSearch.kci?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT, context=get_ssl_context()) as r:
            body = r.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
        print(f"  [dbpia/kci] 실패: {e}", file=sys.stderr)
        return []

    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        return []

    now = dt.datetime.now(dt.timezone.utc).isoformat()
    out = []
    for rec in root.findall(".//record"):
        def t(tag):
            el = rec.find(tag)
            return _clean(el.text) if el is not None else ""
        title = t("article-title")
        if not title:
            continue
        url_ = t("url") or f"https://www.kci.go.kr/kciportal/po/search/poArticleSearchView.kci?artId={t('article-id')}"
        abstract = t("abstract")
        year = t("pub-year")
        authors = t("author-name")
        journal = t("journal-name")
        meta = []
        if year:
            meta.append(f"year: {year}")
        if authors:
            meta.append(f"authors: {authors}")
        if journal:
            meta.append(f"venue: {journal}")
        body_text = "\n".join(meta + [abstract])
        out.append({
            "url": url_,
            "title": title,
            "body": body_text,
            "source": "kci",
            "fetched_at": now,
        })
    return out


def _dbpia_html_scrape(query: str, limit: int) -> list[dict]:
    """DBpia 검색 페이지 best-effort 스크래핑. SPA라 보통 빈 결과."""
    q = urllib.parse.quote(query)
    url = f"https://www.dbpia.co.kr/search/topSearch?searchOption=all&query={q}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=get_ssl_context()) as r:
            body = r.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
        print(f"  [dbpia] HTML fetch 실패: {e}", file=sys.stderr)
        return []

    # 정적 HTML에 결과 링크가 보이면 추출. 대부분 SPA라 비어 있음.
    # 후보 패턴: /thesis/ 또는 /journal/, title 텍스트
    links = re.findall(r'href="(/thesis/[^"]+)"[^>]*>([^<]{4,200})</a>', body)
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    out = []
    for path, raw_title in links[:limit]:
        title = _clean(raw_title)
        if not title:
            continue
        out.append({
            "url": "https://www.dbpia.co.kr" + path,
            "title": title,
            "body": f"venue: DBpia\n(HTML 스크래핑으로 추출된 메타 — abstract 미확보)",
            "source": "dbpia",
            "fetched_at": now,
        })
    return out


def search(query: str, limit: int = 10, **_) -> list[dict]:
    # 1) KCI Open API (키 있으면 — 안정적·구조화)
    res = _kci_search(query, limit)
    if res:
        return res

    # 2) DBpia HTML best-effort
    res = _dbpia_html_scrape(query, limit)
    if res:
        return res

    # 둘 다 0 — 사용자에게 한국 학술 보강 옵션 안내 (한 번만)
    print("  [dbpia] 결과 없음. 한국 학술 자료가 필요하면 KCI_OPEN_API_KEY 설정 권장.", file=sys.stderr)
    return []
