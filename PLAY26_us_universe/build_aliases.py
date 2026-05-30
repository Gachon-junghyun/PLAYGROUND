"""Build ticker -> alias list from us_universe.csv.

Rules per ticker:
  a) ticker itself (and BRK-B variants -> BRK.B)
  b) full company name + name with common suffixes stripped (Inc, Corp, etc.)
  c) Korean alias (large-cap manual dict, ~50 entries)

Output: us_aliases.json
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = Path(__file__).parent
UNIV_CSV = HERE / "us_universe.csv"
OUT_JSON = HERE / "us_aliases.json"

# Manual Korean aliases for major US large-caps. Keep ~50 entries.
KR_ALIAS = {
    "AAPL": "애플",
    "MSFT": "마이크로소프트",
    "NVDA": "엔비디아",
    "GOOGL": "구글",
    "GOOG": "구글",
    "AMZN": "아마존",
    "META": "메타",
    "TSLA": "테슬라",
    "BRK-B": "버크셔",
    "JPM": "JP모건",
    "V": "비자",
    "UNH": "유나이티드헬스",
    "JNJ": "존슨앤드존슨",
    "WMT": "월마트",
    "XOM": "엑슨모빌",
    "PG": "P&G",
    "MA": "마스터카드",
    "HD": "홈디포",
    "CVX": "셰브론",
    "ABBV": "애브비",
    "PFE": "화이자",
    "KO": "코카콜라",
    "PEP": "펩시코",
    "AVGO": "브로드컴",
    "COST": "코스트코",
    "MRK": "머크",
    "DIS": "디즈니",
    "ADBE": "어도비",
    "CSCO": "시스코",
    "CRM": "세일즈포스",
    "NFLX": "넷플릭스",
    "AMD": "AMD",
    "QCOM": "퀄컴",
    "INTC": "인텔",
    "IBM": "IBM",
    "ORCL": "오라클",
    "TXN": "텍사스인스트루먼트",
    "HON": "허니웰",
    "UPS": "UPS",
    "CAT": "캐터필러",
    "BA": "보잉",
    "GS": "골드만삭스",
    "MS": "모건스탠리",
    "BAC": "뱅크오브아메리카",
    "WFC": "웰스파고",
    "PYPL": "페이팔",
    "SBUX": "스타벅스",
    "NKE": "나이키",
    "MCD": "맥도날드",
    "UBER": "우버",
    "ABNB": "에어비앤비",
    "COIN": "코인베이스",
    "SHOP": "쇼피파이",
    "SPOT": "스포티파이",
    "MU": "마이크론",
    "PLTR": "팔란티어",
    "SMCI": "슈퍼마이크로",
    "ARM": "ARM",
}

# Suffixes to strip when generating "short name" alias.
SUFFIX_RE = re.compile(
    r"\s*[,]?\s*\b("
    r"Inc\.?|Incorporated|Corp\.?|Corporation|Co\.?|Company|Companies|"
    r"Ltd\.?|Limited|Holdings|Holding|Group|plc|PLC|"
    r"The|N\.V\.|NV|S\.A\.|AG|LLC|L\.L\.C\.|LP|L\.P\."
    r")\b\.?\s*$",
    re.IGNORECASE,
)


def _strip_suffix(name: str) -> str:
    prev = None
    cur = name.strip()
    # repeatedly strip — handles "Inc." after "Corp." etc.
    while prev != cur:
        prev = cur
        cur = SUFFIX_RE.sub("", cur).strip()
        # also strip trailing comma
        cur = cur.rstrip(",.").strip()
    # strip leading "The "
    if cur.lower().startswith("the "):
        cur = cur[4:].strip()
    return cur


# Explicit name-mapping overrides: Wikipedia name -> additional brand aliases
NAME_BRAND_ALIASES = {
    "Alphabet": ["Google", "Alphabet"],
    "Meta Platforms": ["Meta", "Facebook"],
    "Berkshire Hathaway": ["Berkshire"],
    "JPMorgan Chase": ["JPMorgan", "JP Morgan"],
    "Procter & Gamble": ["P&G", "Procter Gamble"],
    "Mastercard": ["Mastercard"],
    "Home Depot": ["Home Depot"],
    "Walt Disney": ["Disney"],
    "Bank of America": ["BofA", "Bank of America"],
    "Wells Fargo": ["Wells Fargo"],
    "American Express": ["AmEx", "American Express"],
    "Goldman Sachs": ["Goldman", "Goldman Sachs"],
    "Morgan Stanley": ["Morgan Stanley"],
    "BlackRock": ["BlackRock"],
    "Charles Schwab": ["Schwab", "Charles Schwab"],
    "PayPal": ["PayPal"],
    "Salesforce": ["Salesforce"],
    "Tesla": ["Tesla"],
    "Coca-Cola": ["Coca-Cola", "Coke"],
    "PepsiCo": ["PepsiCo", "Pepsi"],
    "Lockheed Martin": ["Lockheed"],
    "RTX": ["Raytheon"],
    "General Electric": ["GE"],
    "Ford Motor": ["Ford"],
    "General Motors": ["GM", "General Motors"],
    "Delta Air Lines": ["Delta"],
    "United Airlines Holdings": ["United Airlines"],
    "American Airlines Group": ["American Airlines"],
    "Carnival": ["Carnival"],
    "Royal Caribbean": ["Royal Caribbean"],
    "Norwegian Cruise Line": ["Norwegian Cruise"],
    "Marriott": ["Marriott"],
    "Hilton Worldwide": ["Hilton"],
    "MGM Resorts": ["MGM"],
    "Target": ["Target"],
    "Lowe's": ["Lowes", "Lowe's"],
    "TJX": ["TJX"],
    "Costco": ["Costco"],
    "Kroger": ["Kroger"],
    "Constellation Brands": ["Constellation"],
    "Altria": ["Altria"],
    "Philip Morris": ["Philip Morris"],
    "Colgate-Palmolive": ["Colgate"],
    "Estée Lauder": ["Estee Lauder", "Estée Lauder"],
    "Church & Dwight": ["Church Dwight"],
    "McDonald's": ["McDonald's", "McDonalds"],
    "Chipotle": ["Chipotle"],
    "eBay": ["eBay"],
    "Etsy": ["Etsy"],
    "Shopify": ["Shopify"],
    "Spotify": ["Spotify"],
    "Uber": ["Uber"],
    "DoorDash": ["DoorDash"],
    "Airbnb": ["Airbnb"],
    "Coinbase": ["Coinbase"],
    "Robinhood": ["Robinhood"],
    "Apple": ["Apple"],
    "Microsoft": ["Microsoft"],
    "Nvidia": ["Nvidia", "NVIDIA"],
    "Amazon": ["Amazon"],
    "Netflix": ["Netflix"],
    "Adobe": ["Adobe"],
    "Cisco": ["Cisco"],
    "Oracle": ["Oracle"],
    "Intel": ["Intel"],
    "AMD": ["AMD"],
    "Qualcomm": ["Qualcomm"],
    "Broadcom": ["Broadcom"],
    "Micron": ["Micron"],
    "Palantir": ["Palantir"],
    "ARM": ["ARM"],
    "Walmart": ["Walmart"],
    "Pfizer": ["Pfizer"],
    "Merck": ["Merck"],
    "AbbVie": ["AbbVie"],
    "Johnson & Johnson": ["Johnson Johnson", "J&J"],
    "ExxonMobil": ["Exxon", "ExxonMobil"],
    "Chevron": ["Chevron"],
    "Boeing": ["Boeing"],
    "Caterpillar": ["Caterpillar"],
    "Honeywell": ["Honeywell"],
    "Intuit": ["Intuit"],
    "ServiceNow": ["ServiceNow"],
    "Texas Instruments": ["Texas Instruments"],
    "Visa": ["Visa"],
    "Citigroup": ["Citigroup", "Citi"],
    "IBM": ["IBM", "International Business Machines"],
    "Analog Devices": ["Analog Devices"],
    "Archer Daniels Midland": ["Archer Daniels Midland", "ADM"],
    "Automatic Data Processing": ["ADP"],
    "Autodesk": ["Autodesk"],
    "American Electric Power": ["AEP"],
}


def _aliases_for(ticker: str, name: str) -> list[str]:
    out: list[str] = []
    seen = set()

    def add(s: str):
        s = s.strip()
        if not s:
            return
        key = s.lower()
        if key in seen:
            return
        seen.add(key)
        out.append(s)

    add(ticker)
    # ticker variant: BRK-B -> BRK.B
    if "-" in ticker:
        add(ticker.replace("-", "."))

    if name:
        # Drop "(Class A)" / "(Class B)" etc. before further processing
        clean = re.sub(r"\s*\(Class\s+[A-Z]\)\s*", "", name).strip()
        add(clean)
        short = _strip_suffix(clean)
        if short and short != clean:
            add(short)
        # Variant without period after Inc
        no_dot = clean.replace(".", "").strip()
        if no_dot != clean:
            add(no_dot)
        # Brand-level explicit aliases (matched by 'short' or 'clean' substring)
        for key, extra_list in NAME_BRAND_ALIASES.items():
            if key.lower() in short.lower() or key.lower() in clean.lower():
                for extra in extra_list:
                    add(extra)

    kr = KR_ALIAS.get(ticker)
    if kr:
        add(kr)

    return out


def main():
    rows = []
    with UNIV_CSV.open("r", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            rows.append(r)

    aliases: dict[str, list[str]] = {}
    for r in rows:
        t = r["ticker"]
        aliases[t] = _aliases_for(t, r["name"])

    with OUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(aliases, f, ensure_ascii=False, indent=2)

    lens = [len(v) for v in aliases.values()]
    print(f"[done] wrote {OUT_JSON.name} for {len(aliases)} tickers")
    print(f"  alias count avg={sum(lens)/len(lens):.2f} min={min(lens)} max={max(lens)}")
    # Sample
    for t in ["AAPL", "NVDA", "BRK-B", "JPM", "GOOGL", "PEP"]:
        if t in aliases:
            print(f"  {t}: {aliases[t]}")


if __name__ == "__main__":
    main()
