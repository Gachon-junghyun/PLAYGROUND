"""
PLAY25 audit.py — runs three checks for US foreign-press RSS expansion:

 Step 1: Fetch every candidate feed in feeds_us.py, record items / HTTP / dup-rate.
         Then scrape up to N article bodies per feed using selectors_us.py.
 Step 2: Bloomberg "summary-only" PoC — read recent Bloomberg rows from
         mvp/research_Mvp/news_alert.db and synthesise macro-keyword micro-cards.
 Step 3: Google News redirect resolution — does requests.get(allow_redirects=True)
         turn a news.google.com/rss/articles/... URL into the real source URL?

Writes the full result to audit_report.md (overwrite) and prints a one-line summary.

Dependencies: requests, feedparser, beautifulsoup4, lxml  (same as mvp).
Target wall-clock: under 50s. We use a thread pool and tiny per-feed item caps.
"""
from __future__ import annotations

import hashlib
import os
import re
import sqlite3
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Tuple

import feedparser
import requests
from bs4 import BeautifulSoup

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from feeds_us import RSS_FEEDS_US  # noqa: E402
from selectors_us import SOURCE_SELECTORS_US  # noqa: E402

# ----- knobs ----------------------------------------------------------------
MAX_ITEMS_PER_FEED = 5
SCRAPE_PER_FEED = 2          # only scrape first 2 bodies — keeps wall-clock low
FEED_TIMEOUT = 8
SCRAPE_TIMEOUT = 8
MIN_BODY_LEN = 100
MAX_PARALLEL_FEEDS = 8
MAX_PARALLEL_SCRAPES = 6

MVP_DB = Path(r"C:\Users\fivep\OneDrive\Desktop\mvp\research_Mvp\news_alert.db")
REPORT_PATH = HERE / "audit_report.md"

# mvp uses Chrome UA. SEC requires a contactable identifier.
HEADERS_DEFAULT = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
}
HEADERS_SEC = {
    "User-Agent": "Researcher Contact: fivepeople201@gmail.com",
    "Accept": "application/atom+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate",
}


def _headers_for(source: str) -> dict:
    if source == "sec_edgar":
        return HEADERS_SEC
    return HEADERS_DEFAULT


# ============================================================================
# Step 1 — Feed fetch + body scrape
# ============================================================================

def fetch_feed(feed: Dict) -> Dict:
    """Returns a result dict with item-level metadata. Catches every exception."""
    out = {
        "name": feed["name"],
        "url": feed["url"],
        "source": feed["source"],
        "http_status": None,
        "parse_ok": False,
        "n_items": 0,
        "items": [],          # list of (title, url, summary)
        "error": "",
        "elapsed_ms": 0,
    }
    t0 = time.time()
    try:
        resp = requests.get(feed["url"], headers=_headers_for(feed["source"]), timeout=FEED_TIMEOUT)
        out["http_status"] = resp.status_code
        if resp.status_code >= 400:
            out["error"] = f"HTTP {resp.status_code}"
            return out
        parsed = feedparser.parse(resp.content)
        out["parse_ok"] = bool(parsed.entries) or not parsed.bozo
        items = []
        for entry in parsed.entries[:MAX_ITEMS_PER_FEED]:
            title = (entry.get("title") or "").strip()
            url = (entry.get("link") or "").strip()
            summary = (entry.get("summary") or entry.get("description") or "").strip()
            if title and url:
                items.append((title, url, summary))
        out["items"] = items
        out["n_items"] = len(items)
        if not items:
            out["error"] = "no items parsed"
    except requests.RequestException as e:
        out["error"] = f"request: {type(e).__name__}: {e}"
    except Exception as e:  # feedparser may raise on weird content
        out["error"] = f"parse: {type(e).__name__}: {e}"
    finally:
        out["elapsed_ms"] = int((time.time() - t0) * 1000)
    return out


def scrape_body(url: str, source: str) -> Tuple[int, str, str]:
    """Returns (status_code, body_text, error). Body is empty if extraction fails."""
    try:
        resp = requests.get(url, headers=_headers_for(source), timeout=SCRAPE_TIMEOUT, allow_redirects=True)
        if resp.status_code >= 400:
            return resp.status_code, "", f"HTTP {resp.status_code}"
        try:
            soup = BeautifulSoup(resp.content, "lxml")
        except Exception:
            soup = BeautifulSoup(resp.content, "html.parser")

        selectors = SOURCE_SELECTORS_US.get(source, [])
        body = ""
        for sel in selectors:
            try:
                tag = soup.select_one(sel)
                if tag:
                    txt = tag.get_text(separator="\n", strip=True)
                    if len(txt) >= MIN_BODY_LEN:
                        body = txt
                        break
            except Exception:
                continue
        if not body:
            # generic fallback similar to mvp scraper
            for unwanted in soup.select("nav, header, footer, aside, script, style"):
                unwanted.decompose()
            candidates = soup.find_all("article") + soup.find_all("main") + soup.find_all("div")
            best = max(
                (c.get_text(separator="\n", strip=True) for c in candidates),
                key=len,
                default="",
            )
            if len(best) >= MIN_BODY_LEN:
                body = best
        return resp.status_code, body, "" if body else "no body extracted"
    except requests.RequestException as e:
        return 0, "", f"request: {type(e).__name__}"
    except Exception as e:
        return 0, "", f"parse: {type(e).__name__}"


def run_step1() -> Dict:
    feed_results: List[Dict] = []
    with ThreadPoolExecutor(max_workers=MAX_PARALLEL_FEEDS) as pool:
        for r in pool.map(fetch_feed, RSS_FEEDS_US):
            feed_results.append(r)

    # Build scrape jobs: first SCRAPE_PER_FEED items per feed
    scrape_jobs: List[Tuple[Dict, str, str]] = []
    for r in feed_results:
        for (title, url, _summary) in r["items"][:SCRAPE_PER_FEED]:
            scrape_jobs.append((r, title, url))

    scrape_outcomes: Dict[str, List[Tuple[int, int, str]]] = {}
    # source_key -> list of (status, body_len, error)
    with ThreadPoolExecutor(max_workers=MAX_PARALLEL_SCRAPES) as pool:
        futures = {pool.submit(scrape_body, url, r["source"]): (r, url) for (r, _t, url) in scrape_jobs}
        for fut in as_completed(futures):
            r, url = futures[fut]
            try:
                status, body, err = fut.result()
            except Exception as e:
                status, body, err = 0, "", f"unexpected: {e}"
            scrape_outcomes.setdefault(r["name"], []).append((status, len(body), err))

    # Per-feed dup rate (title-hash)
    for r in feed_results:
        hashes = [hashlib.sha256(t.encode("utf-8", errors="ignore")).hexdigest() for (t, _u, _s) in r["items"]]
        n = len(hashes)
        uniq = len(set(hashes))
        r["dup_rate"] = round((n - uniq) / n, 3) if n else 0.0
        r["scrape_outcomes"] = scrape_outcomes.get(r["name"], [])
        ok = sum(1 for (s, blen, _e) in r["scrape_outcomes"] if blen >= MIN_BODY_LEN)
        total = len(r["scrape_outcomes"])
        r["scrape_ok_rate"] = round(ok / total, 2) if total else None

    # Aggregate per source-key
    by_source: Dict[str, Dict] = {}
    for r in feed_results:
        s = r["source"]
        by_source.setdefault(s, {"items": 0, "scrape_ok": 0, "scrape_total": 0, "feeds": 0, "feeds_ok": 0})
        by_source[s]["feeds"] += 1
        if r["n_items"] > 0:
            by_source[s]["feeds_ok"] += 1
        by_source[s]["items"] += r["n_items"]
        for (_st, blen, _e) in r["scrape_outcomes"]:
            by_source[s]["scrape_total"] += 1
            if blen >= MIN_BODY_LEN:
                by_source[s]["scrape_ok"] += 1
    for s, agg in by_source.items():
        t = agg["scrape_total"]
        agg["scrape_rate"] = round(agg["scrape_ok"] / t, 2) if t else None

    return {"feeds": feed_results, "by_source": by_source}


# ============================================================================
# Step 2 — Bloomberg summary-only synthesis PoC
# ============================================================================

MACRO_KEYWORDS = [
    "S&P 500", "Nasdaq", "Dow", "Treasury", "yield",
    "Fed", "Federal Reserve", "rate cut", "rate hike", "inflation",
    "CPI", "PPI", "PCE", "jobs", "payroll", "unemployment",
    "tariff", "trade", "China", "Russia", "Ukraine",
    "oil", "OPEC", "dollar", "yen", "euro",
    "AI", "semiconductor", "Nvidia", "Apple", "Tesla",
    "recession", "earnings", "Bitcoin", "ETF", "bond",
]


def run_step2() -> Dict:
    out = {"db_found": MVP_DB.exists(), "rows": [], "cluster": {}, "card": ""}
    if not MVP_DB.exists():
        out["error"] = f"DB not found: {MVP_DB}"
        return out
    try:
        conn = sqlite3.connect(str(MVP_DB))
        cur = conn.cursor()
        cur.execute(
            """
            SELECT title, summary, fetched_at FROM seen_news
            WHERE source = 'bloomberg'
              AND fetched_at >= datetime('now','-7 days')
            ORDER BY fetched_at DESC
            LIMIT 5
            """
        )
        rows = cur.fetchall()
        conn.close()
    except Exception as e:
        out["error"] = f"sqlite: {e}"
        return out

    out["rows"] = [{"title": t, "summary": (s or "")[:200], "fetched_at": f} for (t, s, f) in rows]

    # Heuristic keyword extraction + frequency
    text_blob = " ".join((r["title"] + " " + r["summary"]) for r in out["rows"])
    hits = Counter()
    for kw in MACRO_KEYWORDS:
        # case-insensitive whole-token match
        pattern = r"\b" + re.escape(kw) + r"\b"
        n = len(re.findall(pattern, text_blob, flags=re.IGNORECASE))
        if n:
            hits[kw] = n
    out["cluster"] = dict(hits.most_common(8))

    # One-line micro-card
    top = list(hits.most_common(3))
    if top:
        kw_str = ", ".join(k for k, _ in top)
        out["card"] = (
            f"Bloomberg 5 headlines (last 7d) cluster on: {kw_str}. "
            f"Title-only signal is usable for macro tagging even without body."
        )
    else:
        out["card"] = "No macro keywords hit — title/summary too generic for synthesis."

    return out


# ============================================================================
# Step 3 — Google News redirect resolution
# ============================================================================

GOOGLE_SAMPLES = [
    "https://news.google.com/rss/search?q=reuters&hl=en&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=tariff&hl=en&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=Nvidia&hl=en&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=Federal+Reserve&hl=en&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=S%26P+500&hl=en&gl=US&ceid=US:en",
]


def run_step3() -> Dict:
    """Pull the first item from each Google search feed, then try to resolve its redirect."""
    samples = []
    for url in GOOGLE_SAMPLES:
        sample = {"feed_url": url, "google_link": "", "resolved_url": "", "ok": False, "error": ""}
        try:
            resp = requests.get(url, headers=HEADERS_DEFAULT, timeout=FEED_TIMEOUT)
            parsed = feedparser.parse(resp.content)
            if not parsed.entries:
                sample["error"] = "no entries"
                samples.append(sample)
                continue
            link = parsed.entries[0].get("link", "")
            sample["google_link"] = link
            r2 = requests.get(link, headers=HEADERS_DEFAULT, timeout=SCRAPE_TIMEOUT, allow_redirects=True)
            sample["resolved_url"] = r2.url
            host = re.sub(r"^https?://", "", r2.url).split("/")[0]
            sample["ok"] = bool(host) and "google.com" not in host
            if not sample["ok"]:
                sample["error"] = "still on google.com after redirect"
        except Exception as e:
            sample["error"] = f"{type(e).__name__}: {e}"
        samples.append(sample)
    ok = sum(1 for s in samples if s["ok"])
    return {"samples": samples, "ok": ok, "total": len(samples)}


# ============================================================================
# Report writer
# ============================================================================

def write_report(step1: Dict, step2: Dict, step3: Dict, wall_secs: float) -> None:
    lines: List[str] = []
    lines.append("# PLAY25 audit_report.md")
    lines.append("")
    lines.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}  |  Wall time: {wall_secs:.1f}s")
    lines.append("")
    lines.append(f"Settings: MAX_ITEMS_PER_FEED={MAX_ITEMS_PER_FEED}, "
                 f"SCRAPE_PER_FEED={SCRAPE_PER_FEED}, MIN_BODY_LEN={MIN_BODY_LEN}")
    lines.append("")

    # ---- Step 1 ----
    lines.append("## Step 1 — RSS feed fetch + body scrape")
    lines.append("")
    lines.append("### Per-feed results")
    lines.append("")
    lines.append("| name | source | HTTP | items | dup | scrape ok/total | error |")
    lines.append("|------|--------|------|-------|-----|-----------------|-------|")
    for r in step1["feeds"]:
        ok = sum(1 for (_s, blen, _e) in r["scrape_outcomes"] if blen >= MIN_BODY_LEN)
        tot = len(r["scrape_outcomes"])
        scrape_str = f"{ok}/{tot}" if tot else "0/0"
        err = (r["error"] or "").replace("|", "/")[:60]
        lines.append(
            f"| {r['name']} | {r['source']} | {r['http_status']} | "
            f"{r['n_items']} | {r['dup_rate']} | {scrape_str} | {err} |"
        )
    lines.append("")

    lines.append("### Aggregated by source key")
    lines.append("")
    lines.append("| source | feeds | feeds_ok | items | scrape ok/total | scrape_rate |")
    lines.append("|--------|-------|----------|-------|-----------------|-------------|")
    for s, agg in sorted(step1["by_source"].items()):
        lines.append(
            f"| {s} | {agg['feeds']} | {agg['feeds_ok']} | {agg['items']} | "
            f"{agg['scrape_ok']}/{agg['scrape_total']} | {agg['scrape_rate']} |"
        )
    lines.append("")

    # ---- Step 2 ----
    lines.append("## Step 2 — Bloomberg summary-only synthesis PoC")
    lines.append("")
    if step2.get("error"):
        lines.append(f"ERROR: {step2['error']}")
    else:
        lines.append(f"DB found: {step2['db_found']}, sample rows: {len(step2['rows'])}")
        lines.append("")
        lines.append("**Macro-keyword cluster (top 8):**")
        for k, v in step2["cluster"].items():
            lines.append(f"- {k}: {v}")
        if not step2["cluster"]:
            lines.append("- (no keyword hits)")
        lines.append("")
        lines.append(f"**Synthesised card:** {step2['card']}")
        lines.append("")
        lines.append("**Sample rows:**")
        for r in step2["rows"]:
            t = (r["title"] or "")[:90]
            s = (r["summary"] or "")[:90]
            lines.append(f"- [{r['fetched_at']}] {t} — {s}")
    lines.append("")

    # ---- Step 3 ----
    lines.append("## Step 3 — Google News redirect resolution")
    lines.append("")
    lines.append(f"Resolved {step3['ok']}/{step3['total']} samples to a non-google host.")
    lines.append("")
    lines.append("| feed | google_link host | resolved host | ok | error |")
    lines.append("|------|------------------|---------------|----|-------|")
    for s in step3["samples"]:
        gh = re.sub(r"^https?://", "", s["google_link"]).split("/")[0][:30]
        rh = re.sub(r"^https?://", "", s["resolved_url"]).split("/")[0][:40]
        err = (s["error"] or "").replace("|", "/")[:40]
        feed_short = s["feed_url"].split("q=")[-1].split("&")[0][:25]
        lines.append(f"| {feed_short} | {gh} | {rh} | {s['ok']} | {err} |")
    lines.append("")

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    t0 = time.time()
    print("Step 1: fetching feeds + scraping bodies...", flush=True)
    step1 = run_step1()
    print(f"  done ({time.time()-t0:.1f}s)", flush=True)

    print("Step 2: Bloomberg summary synthesis...", flush=True)
    step2 = run_step2()
    print(f"  done ({time.time()-t0:.1f}s)", flush=True)

    print("Step 3: Google News redirect probe...", flush=True)
    step3 = run_step3()
    print(f"  done ({time.time()-t0:.1f}s)", flush=True)

    wall = time.time() - t0
    write_report(step1, step2, step3, wall)

    n_total = len(step1["feeds"])
    n_ok = sum(1 for r in step1["feeds"] if r["n_items"] > 0)
    print(f"DONE: {n_total} feeds tested, {n_ok} successful "
          f"(wall {wall:.1f}s) -> {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
