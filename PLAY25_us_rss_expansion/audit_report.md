# PLAY25 audit_report.md

Generated: 2026-05-26 22:54:55  |  Wall time: 10.5s

Settings: MAX_ITEMS_PER_FEED=5, SCRAPE_PER_FEED=2, MIN_BODY_LEN=100

## Step 1 — RSS feed fetch + body scrape

### Per-feed results

| name | source | HTTP | items | dup | scrape ok/total | error |
|------|--------|------|-------|-----|-----------------|-------|
| Reuters Agency Biz | reuters | 404 | 0 | 0.0 | 0/0 | HTTP 404 |
| Reuters via GoogleNews | reuters_google | 200 | 5 | 0.0 | 0/2 |  |
| Seeking Alpha Market Currents | seekingalpha | 200 | 5 | 0.0 | 2/2 |  |
| Seeking Alpha Feed | seekingalpha | 200 | 5 | 0.0 | 2/2 |  |
| Yahoo Finance AAPL | yahoo_finance | 200 | 5 | 0.0 | 2/2 |  |
| Yahoo Finance NVDA | yahoo_finance | 200 | 5 | 0.0 | 2/2 |  |
| Yahoo Finance MSFT | yahoo_finance | 200 | 5 | 0.0 | 2/2 |  |
| Yahoo Finance TSLA | yahoo_finance | 200 | 5 | 0.0 | 2/2 |  |
| Yahoo Finance META | yahoo_finance | 200 | 5 | 0.0 | 2/2 |  |
| SEC EDGAR 8-K (current) | sec_edgar | 200 | 5 | 0.0 | 2/2 |  |
| PRNewswire News Releases | prnewswire | 200 | 5 | 0.0 | 2/2 |  |
| BusinessWire Home | businesswire | 200 | 0 | 0.0 | 0/0 | no items parsed |
| MarketWatch MarketPulse | marketwatch | 200 | 5 | 0.0 | 2/2 |  |
| Investing.com Stock News | investing_com | 200 | 5 | 0.0 | 0/2 |  |

### Aggregated by source key

| source | feeds | feeds_ok | items | scrape ok/total | scrape_rate |
|--------|-------|----------|-------|-----------------|-------------|
| businesswire | 1 | 0 | 0 | 0/0 | None |
| investing_com | 1 | 1 | 5 | 0/2 | 0.0 |
| marketwatch | 1 | 1 | 5 | 2/2 | 1.0 |
| prnewswire | 1 | 1 | 5 | 2/2 | 1.0 |
| reuters | 1 | 0 | 0 | 0/0 | None |
| reuters_google | 1 | 1 | 5 | 0/2 | 0.0 |
| sec_edgar | 1 | 1 | 5 | 2/2 | 1.0 |
| seekingalpha | 2 | 2 | 10 | 4/4 | 1.0 |
| yahoo_finance | 5 | 5 | 25 | 10/10 | 1.0 |

## Step 2 — Bloomberg summary-only synthesis PoC

DB found: True, sample rows: 5

**Macro-keyword cluster (top 8):**
- Fed: 2
- inflation: 2
- Federal Reserve: 1
- Russia: 1
- Ukraine: 1

**Synthesised card:** Bloomberg 5 headlines (last 7d) cluster on: Fed, inflation, Federal Reserve. Title-only signal is usable for macro tagging even without body.

**Sample rows:**
- [2026-05-26T22:47:18.524139] Fed’s Case for Cutting Rates ‘Very, Very Weak,' Bill Dudley Says — Bill Dudley, former New York Fed President and Bloomberg Opinion columnist, examines the e
- [2026-05-26T22:47:18.524139] Supreme Court Ducks State Clash Over Immigrant Driver’s Licenses — The US Supreme Court refused to let Florida file an unusual lawsuit that accused Californi
- [2026-05-26T22:47:18.524139] Dutch Block US Takeover of Cloud Services Provider Solvinity — The Dutch government blocked a proposed takeover of Solvinity Group BV, a provider of clou
- [2026-05-26T22:47:18.524139] Putin Steps Up Kyiv Missile Strikes Seeking New Momentum in War — With the battlefield largely at a stalemate, Russia is ramping up ballistic missile attack
- [2026-05-26T22:47:18.524139] ECB to Do ‘Everything in Its Power’ to Tame Inflation: Sleijpen — The European Central Bank will do whatever is needed to bring consumer-price growth back t

## Step 3 — Google News redirect resolution

Resolved 0/5 samples to a non-google host.

| feed | google_link host | resolved host | ok | error |
|------|------------------|---------------|----|-------|
| reuters | news.google.com | news.google.com | False | still on google.com after redirect |
| tariff | news.google.com | news.google.com | False | still on google.com after redirect |
| Nvidia | news.google.com | news.google.com | False | still on google.com after redirect |
| Federal+Reserve | news.google.com | news.google.com | False | still on google.com after redirect |
| S%26P+500 | news.google.com | news.google.com | False | still on google.com after redirect |
