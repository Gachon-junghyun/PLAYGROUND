"""Build US universe = SP500 + Nasdaq100 dedup from Wikipedia.

Strategy:
  1. If `us_universe.csv` already exists (size > 200 rows), skip — fetch is slow.
  2. Try wikipedia tables (requests + BeautifulSoup, timeout=10).
  3. On failure, fall back to `us_universe_seed.csv` (hand-curated ~100 tickers).

Output columns: ticker, name, gics_sector, gics_industry, source.
"""
from __future__ import annotations

import csv
import sys
import os
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import requests
from bs4 import BeautifulSoup

HERE = Path(__file__).parent
OUT_CSV = HERE / "us_universe.csv"
SEED_CSV = HERE / "us_universe_seed.csv"

HEADERS = {"User-Agent": "Mozilla/5.0 (PLAY26 research_Mvp universe builder)"}
SP500_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
NDX_URL = "https://en.wikipedia.org/wiki/Nasdaq-100"


def _clean(s: str) -> str:
    return " ".join((s or "").split()).strip()


def _parse_sp500(html: str) -> list[dict]:
    """SP500 wikipedia table: id='constituents'. Columns: Symbol, Security, GICS Sector, GICS Sub-Industry, ..."""
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table", {"id": "constituents"})
    if not table:
        # fallback: first wikitable
        table = soup.find("table", {"class": "wikitable"})
    rows = []
    if not table:
        return rows
    body = table.find("tbody") or table
    for tr in body.find_all("tr")[1:]:
        cells = tr.find_all(["td", "th"])
        if len(cells) < 4:
            continue
        ticker = _clean(cells[0].get_text())
        name = _clean(cells[1].get_text())
        sector = _clean(cells[2].get_text())
        industry = _clean(cells[3].get_text())
        if not ticker or len(ticker) > 6:
            continue
        rows.append({
            "ticker": ticker.replace(".", "-"),  # BRK.B -> BRK-B (matches yahoo style; keep dot in alias step too)
            "name": name,
            "gics_sector": sector,
            "gics_industry": industry,
            "source": "sp500",
        })
    return rows


def _parse_ndx(html: str) -> list[dict]:
    """Nasdaq-100 wikipedia: table id contains 'constituents' or look for table with Ticker/Symbol header."""
    soup = BeautifulSoup(html, "lxml")
    tables = soup.find_all("table", {"class": "wikitable"})
    target = None
    # Pick table whose header includes Ticker/Symbol and Company
    for t in tables:
        header_text = " ".join(_clean(th.get_text()).lower() for th in t.find_all("th")[:8])
        if ("ticker" in header_text or "symbol" in header_text) and ("company" in header_text or "security" in header_text):
            target = t
            break
    if target is None and tables:
        # fallback: try id='constituents'
        target = soup.find("table", {"id": "constituents"})
    rows = []
    if target is None:
        return rows
    headers_row = [_clean(th.get_text()).lower() for th in target.find_all("th")[:8]]
    # Determine col indexes
    def find_col(*names):
        for n in names:
            for i, h in enumerate(headers_row):
                if n in h:
                    return i
        return -1
    sym_idx = find_col("ticker", "symbol")
    name_idx = find_col("company", "security")
    sector_idx = find_col("gics sector", "sector")
    industry_idx = find_col("gics sub", "sub-industry", "industry")
    body = target.find("tbody") or target
    for tr in body.find_all("tr")[1:]:
        cells = tr.find_all(["td", "th"])
        if len(cells) < 2:
            continue
        try:
            ticker = _clean(cells[sym_idx].get_text()) if sym_idx >= 0 else ""
            name = _clean(cells[name_idx].get_text()) if name_idx >= 0 else ""
        except IndexError:
            continue
        if not ticker or len(ticker) > 6:
            continue
        sector = ""
        industry = ""
        if sector_idx >= 0 and sector_idx < len(cells):
            sector = _clean(cells[sector_idx].get_text())
        if industry_idx >= 0 and industry_idx < len(cells):
            industry = _clean(cells[industry_idx].get_text())
        rows.append({
            "ticker": ticker.replace(".", "-"),
            "name": name,
            "gics_sector": sector,
            "gics_industry": industry,
            "source": "ndx100",
        })
    return rows


def _write_seed_if_missing():
    if SEED_CSV.exists():
        return
    seed = [
        ("AAPL", "Apple Inc."), ("MSFT", "Microsoft Corporation"), ("NVDA", "NVIDIA Corporation"),
        ("GOOGL", "Alphabet Inc."), ("GOOG", "Alphabet Inc."), ("AMZN", "Amazon.com Inc."),
        ("META", "Meta Platforms Inc."), ("TSLA", "Tesla Inc."), ("BRK-B", "Berkshire Hathaway Inc."),
        ("JPM", "JPMorgan Chase & Co."), ("V", "Visa Inc."), ("UNH", "UnitedHealth Group Inc."),
        ("JNJ", "Johnson & Johnson"), ("WMT", "Walmart Inc."), ("XOM", "Exxon Mobil Corporation"),
        ("PG", "Procter & Gamble Company"), ("MA", "Mastercard Inc."), ("HD", "The Home Depot Inc."),
        ("CVX", "Chevron Corporation"), ("ABBV", "AbbVie Inc."), ("PFE", "Pfizer Inc."),
        ("KO", "Coca-Cola Company"), ("PEP", "PepsiCo Inc."), ("AVGO", "Broadcom Inc."),
        ("COST", "Costco Wholesale Corporation"), ("MRK", "Merck & Co."), ("TMO", "Thermo Fisher Scientific"),
        ("DIS", "The Walt Disney Company"), ("ADBE", "Adobe Inc."), ("CSCO", "Cisco Systems Inc."),
        ("CRM", "Salesforce Inc."), ("ABT", "Abbott Laboratories"), ("ACN", "Accenture plc"),
        ("NFLX", "Netflix Inc."), ("AMD", "Advanced Micro Devices Inc."), ("QCOM", "Qualcomm Inc."),
        ("INTC", "Intel Corporation"), ("IBM", "International Business Machines"),
        ("ORCL", "Oracle Corporation"), ("TXN", "Texas Instruments Inc."), ("HON", "Honeywell International"),
        ("UPS", "United Parcel Service"), ("CAT", "Caterpillar Inc."), ("RTX", "RTX Corporation"),
        ("LMT", "Lockheed Martin Corporation"), ("BA", "Boeing Company"),
        ("GS", "Goldman Sachs Group"), ("MS", "Morgan Stanley"), ("BAC", "Bank of America Corporation"),
        ("WFC", "Wells Fargo & Company"), ("C", "Citigroup Inc."), ("AXP", "American Express Company"),
        ("BLK", "BlackRock Inc."), ("SCHW", "Charles Schwab Corporation"), ("PYPL", "PayPal Holdings Inc."),
        ("SBUX", "Starbucks Corporation"), ("MDLZ", "Mondelez International"), ("NKE", "Nike Inc."),
        ("MMM", "3M Company"), ("GE", "GE Aerospace"), ("F", "Ford Motor Company"),
        ("GM", "General Motors Company"), ("DAL", "Delta Air Lines"), ("UAL", "United Airlines Holdings"),
        ("AAL", "American Airlines Group"), ("CCL", "Carnival Corporation"), ("RCL", "Royal Caribbean Cruises"),
        ("NCLH", "Norwegian Cruise Line Holdings"), ("MAR", "Marriott International"), ("HLT", "Hilton Worldwide"),
        ("MGM", "MGM Resorts International"), ("WYNN", "Wynn Resorts"), ("TGT", "Target Corporation"),
        ("LOW", "Lowe's Companies"), ("TJX", "TJX Companies"), ("DG", "Dollar General Corporation"),
        ("DLTR", "Dollar Tree Inc."), ("KR", "Kroger Co."), ("GIS", "General Mills Inc."),
        ("K", "Kellanova"), ("STZ", "Constellation Brands"), ("MO", "Altria Group"),
        ("PM", "Philip Morris International"), ("CL", "Colgate-Palmolive Company"), ("EL", "Estée Lauder Companies"),
        ("CHD", "Church & Dwight"), ("CLX", "Clorox Company"), ("MCD", "McDonald's Corporation"),
        ("YUM", "Yum! Brands"), ("CMG", "Chipotle Mexican Grill"), ("DPZ", "Domino's Pizza"),
        ("QSR", "Restaurant Brands International"), ("EBAY", "eBay Inc."), ("ETSY", "Etsy Inc."),
        ("SHOP", "Shopify Inc."), ("SPOT", "Spotify Technology"), ("UBER", "Uber Technologies"),
        ("LYFT", "Lyft Inc."), ("DASH", "DoorDash Inc."), ("ABNB", "Airbnb Inc."),
        ("COIN", "Coinbase Global"), ("HOOD", "Robinhood Markets"), ("SOFI", "SoFi Technologies"),
    ]
    with SEED_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ticker", "name", "gics_sector", "gics_industry", "source"])
        for t, n in seed:
            w.writerow([t, n, "", "", "seed"])
    print(f"[seed] wrote {SEED_CSV.name} ({len(seed)} tickers)")


def _load_seed() -> list[dict]:
    rows = []
    with SEED_CSV.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            rows.append(row)
    return rows


def main():
    _write_seed_if_missing()

    if OUT_CSV.exists():
        # Skip if already big enough
        with OUT_CSV.open("r", encoding="utf-8", newline="") as f:
            n = sum(1 for _ in f) - 1
        if n >= 200:
            print(f"[skip] {OUT_CSV.name} already exists with {n} rows. Delete to rebuild.")
            return

    rows: list[dict] = []
    fetched_sp500 = fetched_ndx = False
    try:
        r1 = requests.get(SP500_URL, headers=HEADERS, timeout=10)
        if r1.status_code == 200:
            sp = _parse_sp500(r1.text)
            print(f"[sp500] parsed {len(sp)} rows")
            rows.extend(sp)
            fetched_sp500 = len(sp) > 100
    except Exception as e:
        print(f"[sp500] fetch failed: {e}")

    try:
        r2 = requests.get(NDX_URL, headers=HEADERS, timeout=10)
        if r2.status_code == 200:
            nd = _parse_ndx(r2.text)
            print(f"[ndx100] parsed {len(nd)} rows")
            rows.extend(nd)
            fetched_ndx = len(nd) > 50
    except Exception as e:
        print(f"[ndx100] fetch failed: {e}")

    if not (fetched_sp500 or fetched_ndx):
        print("[fallback] wikipedia failed, loading seed")
        rows = _load_seed()

    # Dedup by ticker, prefer first occurrence but merge sector data if missing
    by_ticker: dict[str, dict] = {}
    for r in rows:
        t = r["ticker"]
        if not t:
            continue
        if t not in by_ticker:
            by_ticker[t] = dict(r)
        else:
            cur = by_ticker[t]
            if not cur.get("gics_sector") and r.get("gics_sector"):
                cur["gics_sector"] = r["gics_sector"]
            if not cur.get("gics_industry") and r.get("gics_industry"):
                cur["gics_industry"] = r["gics_industry"]
            # If sp500 + ndx100 both, mark both
            srcs = set(cur.get("source", "").split("+"))
            srcs.add(r.get("source", ""))
            cur["source"] = "+".join(sorted(s for s in srcs if s))

    out = list(by_ticker.values())
    out.sort(key=lambda x: x["ticker"])

    with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["ticker", "name", "gics_sector", "gics_industry", "source"])
        w.writeheader()
        for r in out:
            w.writerow(r)
    print(f"[done] wrote {OUT_CSV.name} ({len(out)} unique tickers)")


if __name__ == "__main__":
    main()
