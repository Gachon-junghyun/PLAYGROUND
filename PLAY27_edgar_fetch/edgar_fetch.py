"""EDGAR 필링 fetch + 카테고라이즈 + markdown 리포트.

사용:
    python edgar_fetch.py AAPL --days 90 --out report_AAPL.md
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

import warnings

import requests
from bs4 import BeautifulSoup
try:
    from bs4 import XMLParsedAsHTMLWarning
    warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
except Exception:
    pass

from _categorizer import categorize_filing, extract_items_from_html
from _renderer import Filing, render_markdown
from _ticker_cik import ticker_to_cik, USER_AGENT

SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
ARCHIVE_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{accession_no_clean}/{primary_doc}"
FILING_INDEX_URL = (
    "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik:010d}"
)
FILING_DETAIL_URL = (
    "https://www.sec.gov/Archives/edgar/data/{cik}/{accession_no_clean}/"
)

HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept-Encoding": "gzip, deflate",
    "Host": "data.sec.gov",
}
WEB_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept-Encoding": "gzip, deflate",
    "Host": "www.sec.gov",
}


def _get_submissions(cik: int) -> dict:
    url = SUBMISSIONS_URL.format(cik=cik)
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()


def _within_days(filing_date_str: str, days: int) -> bool:
    try:
        d = datetime.strptime(filing_date_str, "%Y-%m-%d").date()
    except Exception:
        return False
    return (date.today() - d).days <= days


def _build_filing_rows(
    ticker: str, cik: int, sub_json: dict, days: int
) -> list[Filing]:
    """submissions JSON -> Filing list (날짜 필터링까지)."""
    recent = sub_json.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    accs = recent.get("accessionNumber", [])
    docs = recent.get("primaryDocument", [])
    n = min(len(forms), len(dates), len(accs), len(docs))
    rows: list[Filing] = []
    for i in range(n):
        if not _within_days(dates[i], days):
            continue
        acc_clean = accs[i].replace("-", "")
        primary = docs[i]
        url = ARCHIVE_URL.format(cik=cik, accession_no_clean=acc_clean, primary_doc=primary)
        idx_url = FILING_DETAIL_URL.format(cik=cik, accession_no_clean=acc_clean)
        rows.append(
            Filing(
                ticker=ticker,
                cik=cik,
                form=forms[i],
                filing_date=dates[i],
                accession_no=accs[i],
                primary_doc=primary,
                url=url,
                filing_index_url=idx_url,
            )
        )
    return rows


def _fetch_8k_body_and_categorize(row: Filing) -> None:
    """8-K 한 건 본문 fetch -> Item 추출 -> category + summary 채움.

    비-8K 는 본문 fetch 안 함 (FORM_MAP 으로 직접 매핑).
    """
    if not row.form.upper().startswith("8-K"):
        cat, label = categorize_filing(row.form, [])
        row.category = cat
        row.label = label
        return

    items: list[str] = []
    summary = ""
    try:
        r = requests.get(row.url, headers=WEB_HEADERS, timeout=20)
        if r.status_code == 200:
            html = r.text
            items = extract_items_from_html(html)
            # 짧은 텍스트 요약: <body> 첫 200자
            try:
                soup = BeautifulSoup(html, "lxml")
                # SEC 8-K 는 보통 첫 Item 헤더 다음에 본문이 옴
                text = soup.get_text(" ", strip=True)
                # "Item N.NN" 첫 등장 이후 200자
                if items:
                    first_item = items[0]
                    idx = text.lower().find(f"item {first_item}".lower())
                    if idx >= 0:
                        snippet = text[idx : idx + 240]
                    else:
                        snippet = text[:240]
                else:
                    snippet = text[:240]
                summary = " ".join(snippet.split())[:200]
            except Exception:
                summary = ""
    except Exception as e:
        sys.stderr.write(f"[warn] {row.ticker} {row.accession_no} body fetch failed: {e}\n")

    row.items = items
    cat, label = categorize_filing(row.form, items)
    row.category = cat
    row.label = label
    row.summary = summary


def fetch_filings(ticker: str, days: int = 90) -> tuple[list[Filing], int, Optional[str]]:
    """EDGAR submissions + 8-K 본문 enrich. 반환: (rows, cik, company_name)."""
    cik = ticker_to_cik(ticker)
    if cik is None:
        raise SystemExit(f"Unknown ticker: {ticker}")
    sub = _get_submissions(cik)
    company_name = sub.get("name")
    time.sleep(0.2)
    rows = _build_filing_rows(ticker, cik, sub, days)
    # 8-K 만 본문 fetch (속도 절약). 같은 날짜에 같은 8-K가 amendment 로 또 있을 수 있어
    # 최신순으로 한정 없이 다 받지만, 8-K 개수가 보통 90일에 10~15개 수준이라 OK.
    eightk = [r for r in rows if r.form.upper().startswith("8-K")]
    sys.stderr.write(f"[{ticker}] {len(rows)} filings total, {len(eightk)} 8-K (fetching bodies)\n")
    for r in rows:
        _fetch_8k_body_and_categorize(r)
        if r.form.upper().startswith("8-K"):
            time.sleep(0.2)  # SEC rate limit (정중하게)
    return rows, cik, company_name


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    p = argparse.ArgumentParser(prog="edgar_fetch")
    p.add_argument("ticker", help="US 티커 (예: AAPL)")
    p.add_argument("--days", type=int, default=90)
    p.add_argument("--out", default="", help="출력 .md 경로 (없으면 stdout)")
    args = p.parse_args()

    rows, cik, name = fetch_filings(args.ticker, days=args.days)
    md = render_markdown(args.ticker.upper(), cik, rows, args.days, company_name=name)
    if args.out:
        Path(args.out).write_text(md, encoding="utf-8")
        print(f"saved: {args.out}")
    else:
        print(md)
    print(f"DONE: {len(rows)} filings")


if __name__ == "__main__":
    main()
