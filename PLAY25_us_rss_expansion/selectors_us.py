"""
Body selectors for newly-added US/foreign-press sources.

Format matches mvp/research_Mvp/src/pipeline_bot/news/scraper.py::SOURCE_SELECTORS:
    { source_key: [css_selector, ...] }

The scraper tries each selector in order; the first that yields >=100 chars wins.
If no selector matches it falls back to a generic <article>/<main>/<div> extractor.

Notes per source:
- reuters:        modern Reuters renders the body inside <div data-testid="paragraph-*">.
                  We also keep <article> as a last resort.
- reuters_google: Google News redirect → final URL still reuters.com, same selectors.
- seekingalpha:   article body lives inside [data-test-id="content-container"] /
                  <div id="a-body">. Heavy paywall — often only "lede" survives.
- yahoo_finance:  modern Yahoo renders <div class="caas-body"> (CAAS = Content as a Service).
- sec_edgar:      EDGAR 8-K landing page is a table of documents, not prose.
                  We mainly want metadata; the real 8-K text is one click deeper.
                  Selector targets the filing summary table.
- prnewswire:     <section class="release-body">.
- businesswire:   <div class="bw-release-main"> or <div class="bw-release-body">.
- investing_com:  <div id="leftColumn"> + <section class="article-section">.
"""
from __future__ import annotations

SOURCE_SELECTORS_US: dict[str, list[str]] = {
    "reuters": [
        "div[data-testid='ArticleBody']",
        "div[class*='article-body']",
        "div[class*='paywall-article']",
        "article",
    ],
    "reuters_google": [
        "div[data-testid='ArticleBody']",
        "div[class*='article-body']",
        "article",
    ],
    "seekingalpha": [
        "div[data-test-id='content-container']",
        "div#a-body",
        "div[class*='article-body']",
        "article",
    ],
    "yahoo_finance": [
        "div.caas-body",
        "div[class*='caas-body']",
        "div[class*='article-body']",
        "article",
    ],
    "sec_edgar": [
        "div.formContent",
        "table.tableFile",
        "div#contentDiv",
        "div#main-content",
    ],
    "prnewswire": [
        "section.release-body",
        "div.release-body",
        "div[class*='release-body']",
        "article",
    ],
    "businesswire": [
        "div.bw-release-main",
        "div.bw-release-body",
        "div[class*='bw-release']",
        "article",
    ],
    "investing_com": [
        "div.WYSIWYG.articlePage",
        "div#leftColumn",
        "section.article-section",
        "article",
    ],
}
