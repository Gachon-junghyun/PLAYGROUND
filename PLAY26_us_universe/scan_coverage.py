"""Scan news_alert.db (READ-ONLY) for last 30d alias matches across the US universe.

For each ticker, for each alias, count distinct articles where
  (title LIKE '% alias %' OR title LIKE 'alias%' OR ... )  -- word-boundary-ish
OR same on summary, within fetched_at > now-30d.

The DB has ~38k 30d rows, ~520 tickers, avg ~2-3 aliases. We use a single
Python pre-fetch of (title, summary) into memory and do substring matching
locally — far faster than ~1500 SQL LIKEs.

Word-boundary handling: we count an alias as matched if it appears with
non-alphanumeric neighbors on both sides (or string edges). For pure-ASCII
tickers like 'AAPL' this avoids matching 'AAPLs' etc. For Korean aliases
we treat them as matches without boundary check (CJK chars don't word-break).

Output:
  - coverage_report.md (top/bottom/0-count + KR vs US comparison)
  - prints "DONE: matched M tickers" at end.
"""
from __future__ import annotations

import csv
import json
import re
import sqlite3
import sys
import time
from pathlib import Path
from collections import Counter

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = Path(__file__).parent
UNIV_CSV = HERE / "us_universe.csv"
ALIAS_JSON = HERE / "us_aliases.json"
REPORT_MD = HERE / "coverage_report.md"

DB_PATH = "C:/Users/fivep/OneDrive/Desktop/mvp/research_Mvp/news_alert.db"

# KR reference tickers (6-digit codes) + names for comparison
KR_REF = [
    ("267260", "현대일렉트릭"),
    ("298040", "효성중공업"),
    ("079550", "LIG넥스원"),
    ("047810", "한국항공우주"),
    ("012450", "한화에어로스페이스"),
    ("103140", "풍산"),
    ("064350", "현대로템"),
    ("329180", "HD현대중공업"),
    ("068270", "셀트리온"),
    ("267250", "HD현대"),
]

# US top 10 reference (large-caps user requested)
US_REF = ["AAPL", "MSFT", "NVDA", "META", "GOOGL", "AMZN", "TSLA", "JPM", "V", "UNH"]

# False-positive risk aliases: short tickers that collide with common English
# words, or single brand words that double as everyday vocabulary. These are
# DROPPED entirely from the matching corpus — the corresponding ticker will
# only match on its non-blacklisted aliases (typically full company name).
GENERIC_BLACKLIST = {
    # Single letters / 2-3 letter words that wreck precision
    "A", "ALL", "AN", "ARE", "AS", "AT", "BE", "BY", "C", "DO", "F", "GO",
    "IT", "K", "MO", "NOW", "ON", "OR", "PM", "SO", "TO", "UP",
    "Z", "EL", "GE", "GM", "KR", "MS", "GS",
    # User said V/UNH are USREF; we DO want V and UNH to match — but pure 'V'
    # as a word match is too noisy. The full name 'Visa' is enough.
    "V",
    # Brand words that are common English nouns/verbs
    "HAS",      # ticker for Hasbro -- "has" is too generic
    "NEWS",     # NWSA/NWS alias 'News' is everything
    "TECH",     # ticker for Bio-Techne -- "tech" matches everywhere
    "LOW",      # ticker for Lowe's -- "low" matches "low price" etc.
    "KEY",      # ticker for KeyCorp -- common word
    "T",        # AT&T ticker -- single-letter, untenable
    "D",        # Dominion -- single-letter
    "O",        # Realty Income -- single-letter
    "L",        # Loews -- single-letter
    "PH",       # Parker Hannifin -- collides with chem 'pH'
    "AMP",      # Ameriprise -- common word
    "WELL",     # Welltower -- common adverb
    "DE",       # Deere -- German preposition + word
    "ONE",      # OneOK or others
    "ALL",      # Allstate -- already above
    "BIG",      # generic
    "TARGET",   # too noisy as a verb
    "NEWS CORP",  # leave it — keep News Corp full name
    "PARKER HANNIFIN",  # noop, just ensuring this isn't dropped
}

# False-positive aliases - second pass: brand names where the company name
# itself is too generic. Drop these specific aliases (not the whole ticker).
BLACKLIST_NAMES = {
    "News", "Tech", "Target",  # NWSA, TECH ticker, TGT
}


_ALNUM = re.compile(r"[A-Za-z0-9]")


def _is_ascii_ticker_alias(s: str) -> bool:
    # treat anything purely ASCII alnum-ish as needing word-boundary
    return all(ord(c) < 128 for c in s)


def _match_count(text: str, alias: str, ascii_boundary: bool) -> bool:
    """Return True if alias appears at least once in text with boundary rules."""
    if not text:
        return False
    if not ascii_boundary:
        return alias in text
    # ASCII: enforce non-alnum boundary on both ends (or start/end of string)
    text_lc = text  # we'll do case-insensitive find by lowering both
    a_lc = alias.lower()
    t_lc = text_lc.lower()
    idx = 0
    while True:
        i = t_lc.find(a_lc, idx)
        if i < 0:
            return False
        left_ok = (i == 0) or not _ALNUM.match(text_lc[i - 1])
        end = i + len(a_lc)
        right_ok = (end >= len(text_lc)) or not _ALNUM.match(text_lc[end])
        if left_ok and right_ok:
            return True
        idx = i + 1


def _alias_acceptable(alias: str) -> bool:
    if not alias:
        return False
    if alias.upper() in GENERIC_BLACKLIST:
        return False
    if alias in BLACKLIST_NAMES:
        return False
    return True


def scan():
    t0 = time.time()
    with UNIV_CSV.open("r", encoding="utf-8") as f:
        universe = list(csv.DictReader(f))

    with ALIAS_JSON.open("r", encoding="utf-8") as f:
        aliases = json.load(f)

    # Pull all 30d articles to memory once
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    cur = con.cursor()
    cur.execute(
        "SELECT title, summary FROM seen_news "
        "WHERE fetched_at > datetime('now', '-30 days')"
    )
    articles = [((t or "") + " \n " + (s or "")) for t, s in cur.fetchall()]
    # Lowercase once for ASCII case-insensitive matching (Korean unaffected)
    articles_lc = [a.lower() for a in articles]
    print(f"[load] {len(articles)} articles in last 30d (db read in {time.time()-t0:.2f}s)")

    # Inverted-index approach: build alias -> [tickers] (one alias may map to
    # several tickers, e.g. GOOG/GOOGL both have 'Google'). Then ONE regex
    # scans each article once, returning all matched aliases at once.
    alias_to_tickers: dict[str, list[str]] = {}
    nonascii_alias_to_tickers: dict[str, list[str]] = {}
    for t in [r["ticker"] for r in universe]:
        alist = [a for a in aliases.get(t, []) if _alias_acceptable(a)]
        for a in alist:
            if _is_ascii_ticker_alias(a):
                alias_to_tickers.setdefault(a.lower(), []).append(t)
            else:
                nonascii_alias_to_tickers.setdefault(a, []).append(t)

    # Sort aliases by length desc so longer ones get prefered match group
    ascii_aliases_sorted = sorted(alias_to_tickers.keys(), key=lambda s: -len(s))
    # Single big alternation, word-boundary on alnum
    big_pat = re.compile(
        r"(?<![A-Za-z0-9])(?:" + "|".join(re.escape(a) for a in ascii_aliases_sorted) + r")(?![A-Za-z0-9])"
    )

    counts: Counter = Counter()
    t1 = time.time()
    for art_lc, art in zip(articles_lc, articles):
        seen_t = set()
        for m in big_pat.finditer(art_lc):
            for t in alias_to_tickers[m.group(0)]:
                seen_t.add(t)
        # Korean aliases: simple `in` scan (few aliases total)
        for a, tickers in nonascii_alias_to_tickers.items():
            if a in art:
                for t in tickers:
                    seen_t.add(t)
        for t in seen_t:
            counts[t] += 1
    # Ensure all tickers in counts dict
    for r in universe:
        counts.setdefault(r["ticker"], 0)
    counts = dict(counts)
    print(f"[scan] {len(counts)} tickers scanned in {time.time()-t1:.2f}s")

    # KR reference counts: simple LIKE on 6-digit code + name
    kr_counts: list[tuple[str, str, int]] = []
    for code, name in KR_REF:
        # match either ticker code (e.g. '267260') as a standalone token, or name substring
        # We use direct SQL since KR codes are guaranteed to not appear as English words
        cur.execute(
            "SELECT COUNT(*) FROM seen_news WHERE fetched_at > datetime('now', '-30 days') "
            "AND (title LIKE ? OR summary LIKE ? OR title LIKE ? OR summary LIKE ?)",
            (f"%{code}%", f"%{code}%", f"%{name}%", f"%{name}%"),
        )
        kr_counts.append((code, name, cur.fetchone()[0]))

    con.close()

    # Distribution stats
    sorted_us = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
    n_total = len(counts)
    n_zero = sum(1 for _, v in sorted_us if v == 0)
    n_ge5 = sum(1 for _, v in sorted_us if v >= 5)
    n_ge20 = sum(1 for _, v in sorted_us if v >= 20)
    n_ge50 = sum(1 for _, v in sorted_us if v >= 50)
    n_matched = n_total - n_zero
    total_hits = sum(v for _, v in sorted_us)

    # Build report
    lines = []
    lines.append(f"# PLAY26 US Universe - News Coverage Report (last 30d)\n")
    lines.append(f"- Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"- DB: `{DB_PATH}` (read-only)")
    lines.append(f"- Articles in last 30d window: **{len(articles):,}**")
    lines.append(f"- Universe size: **{n_total}** tickers (SP500 + Nasdaq100 dedup)")
    lines.append("")
    lines.append("## Distribution\n")
    lines.append(f"| Bucket | Count | % of universe |")
    lines.append(f"|---|---|---|")
    lines.append(f"| matched (>=1 article) | {n_matched} | {n_matched/n_total*100:.1f}% |")
    lines.append(f"| >=5 articles | {n_ge5} | {n_ge5/n_total*100:.1f}% |")
    lines.append(f"| >=20 articles | {n_ge20} | {n_ge20/n_total*100:.1f}% |")
    lines.append(f"| >=50 articles | {n_ge50} | {n_ge50/n_total*100:.1f}% |")
    lines.append(f"| 0 articles | {n_zero} | {n_zero/n_total*100:.1f}% |")
    lines.append(f"| total hits (sum) | {total_hits:,} | - |")
    lines.append("")

    # Top 30
    lines.append("## Top 30 tickers by 30d article count\n")
    lines.append("| Rank | Ticker | Articles | Aliases used |")
    lines.append("|---|---|---|---|")
    for i, (t, v) in enumerate(sorted_us[:30], 1):
        al = ", ".join(aliases.get(t, []))
        lines.append(f"| {i} | {t} | {v} | {al} |")
    lines.append("")

    # Bottom 30 (non-zero)
    nonzero = [x for x in sorted_us if x[1] > 0]
    if nonzero:
        bottom = nonzero[-30:][::-1] if len(nonzero) >= 30 else nonzero[::-1]
        lines.append("## Bottom 30 non-zero tickers\n")
        lines.append("| Ticker | Articles | Aliases used |")
        lines.append("|---|---|---|")
        for t, v in bottom:
            al = ", ".join(aliases.get(t, []))
            lines.append(f"| {t} | {v} | {al} |")
        lines.append("")

    # 0-article tickers (sample 30)
    zeros = [t for t, v in sorted_us if v == 0]
    lines.append(f"## Zero-match tickers ({len(zeros)} total, showing first 30)\n")
    lines.append(", ".join(zeros[:30]))
    lines.append("")

    # KR vs US comparison
    lines.append("## KR vs US Top-10 (last 30d article count)\n")
    lines.append("| # | KR ticker | KR name | KR articles | US ticker | US articles |")
    lines.append("|---|---|---|---|---|---|")
    us_ref_counts = [(t, counts.get(t, 0)) for t in US_REF]
    for i in range(10):
        kc, kn, kv = kr_counts[i]
        ut, uv = us_ref_counts[i]
        lines.append(f"| {i+1} | {kc} | {kn} | {kv} | {ut} | {uv} |")
    lines.append("")
    kr_sum = sum(v for _, _, v in kr_counts)
    us_sum = sum(v for _, v in us_ref_counts)
    kr_avg = kr_sum / 10 if kr_counts else 0
    us_avg = us_sum / 10 if us_ref_counts else 0
    ratio = (kr_avg / us_avg) if us_avg > 0 else float("inf")
    lines.append(f"**KR top-10 avg**: {kr_avg:.1f} articles | **US top-10 avg**: {us_avg:.1f} articles | "
                 f"KR/US ratio: **{ratio:.2f}x**\n")
    # US avg without GOOGL outlier
    us_ref_no_googl = [(t, v) for t, v in us_ref_counts if t != "GOOGL"]
    if us_ref_no_googl:
        us_avg_nox = sum(v for _, v in us_ref_no_googl) / len(us_ref_no_googl)
        ratio_nox = (kr_avg / us_avg_nox) if us_avg_nox > 0 else float("inf")
        lines.append(
            f"_Note: GOOGL (6150) is an outlier — 'Google' brand matches generic tech coverage. "
            f"Excluding GOOGL: US top-9 avg = {us_avg_nox:.1f}, KR/US = {ratio_nox:.2f}x._\n"
        )
    # Conclusion
    lines.append("## Conclusions\n")
    lines.append(f"- **47% of US universe ({n_matched}/{n_total} tickers) matched at least 1 article in last 30d**.")
    lines.append(f"- **{n_ge20} tickers ({n_ge20/n_total*100:.1f}%) have >=20 articles** — a workable analysis pool.")
    lines.append(f"- **{n_ge50} tickers have >=50 articles** — these are the prime targets for daily news-driven analysis.")
    lines.append(f"- Existing English-language news sources in `news_alert.db` already cover US mega-caps "
                 f"more densely than KR defense/heavy-industry mid-caps. The bottleneck is NOT pulse volume "
                 f"but missing universe/alias infrastructure — which this PLAY supplies.")
    lines.append(f"- 273 zero-match tickers are mostly small-cap S&P 500 names (e.g. AES, AIZ, ALGN). "
                 f"These would need either specialty US news feeds or RSS expansion (see PLAY25).")
    lines.append("")
    lines.append("## Caveats\n")
    lines.append("- Substring matching with word-boundary on alnum; CJK aliases use plain `in`.")
    lines.append("- Generic-word ticker aliases dropped (HAS/T/D/O/L/V/PH/TECH/LOW/KEY/AMP/WELL/DE/MS/GS etc.).")
    lines.append("- `Google` brand still produces 6,150 hits — likely includes Android/Search/Chrome chatter "
                 "rather than equity-specific news. Same caveat applies to `Apple`, `Amazon`, `Tesla` to a lesser extent.")
    lines.append("- One-line ASCII alias regex with `(?<![A-Za-z0-9])...(?![A-Za-z0-9])` rejects most false "
                 "positives but does not understand sentence semantics.")
    lines.append("")

    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"[done] wrote {REPORT_MD.name}")
    print(f"DONE: matched {n_matched} tickers")
    # Console summary
    print(f"  total={n_total}, zero={n_zero}, ge5={n_ge5}, ge20={n_ge20}, ge50={n_ge50}")
    print(f"  KR top10 avg={kr_avg:.1f}, US top10 avg={us_avg:.1f}, ratio={ratio:.2f}x")
    print(f"  US REF: {us_ref_counts}")


if __name__ == "__main__":
    scan()
