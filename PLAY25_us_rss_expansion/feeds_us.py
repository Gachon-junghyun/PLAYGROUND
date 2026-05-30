"""
US foreign-press RSS candidate list.

Format is compatible with mvp's RSS_FEEDS so that successful feeds can be merged
back into pipeline_bot/news/fetcher.py without further mapping.

Each entry:
    {"name": display, "url": rss_url, "source": selector_key}

`source` keys here are NEW (not yet in mvp SOURCE_SELECTORS).
See selectors_us.py for the matching body selectors.
"""
from __future__ import annotations
from typing import Dict, List

# Yahoo Finance per-ticker tickers tested in the audit. Easy to extend.
YAHOO_TICKERS = ["AAPL", "NVDA", "MSFT", "TSLA", "META"]


def _yahoo_feeds() -> List[Dict]:
    base = "https://feeds.finance.yahoo.com/rss/2.0/headline?s={t}&region=US&lang=en-US"
    return [
        {"name": f"Yahoo Finance {t}", "url": base.format(t=t), "source": "yahoo_finance"}
        for t in YAHOO_TICKERS
    ]


# Reuters: classic feeds.reuters.com was shut down in 2020. We try the
# reutersagency.com "best-topics" feed and a Google-News fallback that always
# resolves to reuters.com items. audit.py records which URL actually returned items.
REUTERS_CANDIDATES: List[Dict] = [
    {
        "name": "Reuters Agency Biz",
        "url": "https://www.reutersagency.com/feed/?best-topics=business-finance&post_type=best",
        "source": "reuters",
    },
    {
        "name": "Reuters via GoogleNews",
        "url": "https://news.google.com/rss/search?q=site:reuters.com+when:1d&hl=en&gl=US&ceid=US:en",
        "source": "reuters_google",
    },
]


RSS_FEEDS_US: List[Dict] = [
    # --- Reuters (two candidates; treat as a single "source" experimentally) ---
    *REUTERS_CANDIDATES,
    # --- Seeking Alpha ---
    {
        "name": "Seeking Alpha Market Currents",
        "url": "https://seekingalpha.com/market_currents.xml",
        "source": "seekingalpha",
    },
    {
        "name": "Seeking Alpha Feed",
        "url": "https://seekingalpha.com/feed.xml",
        "source": "seekingalpha",
    },
    # --- Yahoo Finance per-ticker (expanded) ---
    *_yahoo_feeds(),
    # --- SEC EDGAR 8-K (regulatory primary source) ---
    # The bare company-search atom URL returns an empty feed without a CIK filter.
    # The "current events" endpoint gives the live 8-K firehose across all filers.
    {
        "name": "SEC EDGAR 8-K (current)",
        "url": (
            "https://www.sec.gov/cgi-bin/browse-edgar"
            "?action=getcurrent&type=8-K&company=&dateb=&owner=include&count=40&output=atom"
        ),
        "source": "sec_edgar",
    },
    # --- Press release wires (raw corporate disclosures) ---
    {
        "name": "PRNewswire News Releases",
        "url": "https://www.prnewswire.com/rss/news-releases-list.rss",
        "source": "prnewswire",
    },
    {
        "name": "BusinessWire Home",
        "url": "https://feed.businesswire.com/rss/home/?rss=G1QFDERJXkJeEVtRVw==",
        "source": "businesswire",
    },
    # --- MarketWatch (extra; mvp has only Top stories) ---
    {
        "name": "MarketWatch MarketPulse",
        "url": "https://www.marketwatch.com/rss/marketpulse",
        "source": "marketwatch",
    },
    # --- Investing.com ---
    {
        "name": "Investing.com Stock News",
        "url": "https://www.investing.com/rss/news_25.rss",
        "source": "investing_com",
    },
]
