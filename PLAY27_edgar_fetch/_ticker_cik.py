"""티커 <-> CIK 매핑.

SEC 공식 매핑 파일 (https://www.sec.gov/files/company_tickers.json) 을
첫 호출 시 한 번 받아 `ticker_cik_map.json` 으로 캐싱한다.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

import requests

USER_AGENT = "PLAY27 Researcher fivepeople201@gmail.com"
TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
CACHE_PATH = Path(__file__).parent / "ticker_cik_map.json"


def _download_tickers() -> dict[str, int]:
    """SEC company_tickers.json -> {TICKER_UPPER: cik_int} 압축."""
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    r = requests.get(TICKERS_URL, headers=headers, timeout=30)
    r.raise_for_status()
    raw = r.json()
    # 원본 구조: {"0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}, ...}
    out: dict[str, int] = {}
    for v in raw.values():
        t = str(v.get("ticker", "")).upper().strip()
        cik = v.get("cik_str")
        if t and isinstance(cik, int):
            out[t] = cik
    return out


def load_ticker_cik_map(force_refresh: bool = False) -> dict[str, int]:
    if CACHE_PATH.exists() and not force_refresh:
        try:
            data = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data:
                return {k.upper(): int(v) for k, v in data.items()}
        except Exception:
            pass
    data = _download_tickers()
    CACHE_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    time.sleep(0.2)
    return data


def ticker_to_cik(ticker: str, cache: Optional[dict[str, int]] = None) -> Optional[int]:
    if cache is None:
        cache = load_ticker_cik_map()
    return cache.get(ticker.upper().strip())


if __name__ == "__main__":
    m = load_ticker_cik_map()
    print(f"Loaded {len(m)} ticker->CIK pairs")
    for t in ["AAPL", "NVDA", "MSFT", "TSLA", "META"]:
        print(f"  {t} -> CIK {m.get(t)}")
