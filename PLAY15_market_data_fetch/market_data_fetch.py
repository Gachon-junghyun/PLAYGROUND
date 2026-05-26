"""OHLCV fetcher — ticker + days → CSV (PLAY14 compatible 헤더).

source 순위:
  1) yfinance (설치돼 있으면 import 시도)
  2) KRX 일별시세 (urllib 직접 호출)  — 한국 6자리 ticker 자동 분기
  3) deterministic 더미 (seed=ticker hash)  — 위 둘 다 실패하거나 --source dummy

권유 layer 아님. 단순 데이터 페치 + CSV 정규화.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path


CSV_HEADER = ["date", "open", "high", "low", "close", "volume"]


# ----------------- source 1: yfinance -----------------
def fetch_yfinance(ticker, days):
    """yfinance 설치돼 있으면 사용. 미설치/실패 시 RuntimeError."""
    try:
        import yfinance as yf  # type: ignore
    except ImportError as e:
        raise RuntimeError(f"yfinance not installed: {e}")
    end = datetime.utcnow().date()
    start = end - timedelta(days=int(days * 1.6) + 10)  # 주말/공휴일 버퍼
    df = yf.download(ticker, start=start.isoformat(), end=(end + timedelta(days=1)).isoformat(),
                     progress=False, auto_adjust=False)
    if df is None or len(df) == 0:
        raise RuntimeError(f"yfinance empty for {ticker}")
    rows = []
    for idx, row in df.iterrows():
        rows.append({
            "date": idx.strftime("%Y-%m-%d"),
            "open": float(row["Open"]),
            "high": float(row["High"]),
            "low": float(row["Low"]),
            "close": float(row["Close"]),
            "volume": float(row["Volume"]),
        })
    return rows[-days:]


# ----------------- source 2: KRX 일별시세 (urllib) -----------------
def fetch_krx(ticker, days):
    """KRX 공식 OTP API 일별시세. 한국 6자리 ticker 가정.

    주의: KRX는 클라이언트가 OTP를 받아오는 2-step. 네트워크 차단/UA 검사로
    실패할 수 있음. 실패 시 RuntimeError로 fallback 트리거.
    """
    if not (ticker.isdigit() and len(ticker) == 6):
        raise RuntimeError(f"KRX expects 6-digit ticker, got {ticker!r}")

    end = datetime.utcnow().date()
    start = end - timedelta(days=int(days * 1.6) + 10)
    otp_url = "https://data.krx.co.kr/comm/fileDn/GenerateOTP/generate.cmd"
    otp_payload = {
        "bld": "dbms/MDC/STAT/standard/MDCSTAT01701",
        "isuCd": f"KR7{ticker}{_krx_check(ticker)}",
        "isuCd2": "",
        "strtDd": start.strftime("%Y%m%d"),
        "endDd": end.strftime("%Y%m%d"),
        "share": "1",
        "money": "1",
        "csvxls_isNo": "false",
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "http://data.krx.co.kr/contents/MDC/MDI/mdiLoader",
    }
    try:
        # KRX는 ISIN 체크섬을 요구하지만 OTP 발급 자체는 보통 통과 → 직접 시세 endpoint 호출
        url = "http://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd"
        body = urllib.parse.urlencode({
            "bld": "dbms/MDC/STAT/standard/MDCSTAT01701",
            "isuCd": f"KR7{ticker}000",  # 체크섬 자리 임시 — endpoint가 isuCd2/조회방법 호환
            "isuCd2": ticker,
            "strtDd": start.strftime("%Y%m%d"),
            "endDd": end.strftime("%Y%m%d"),
            "share": "1",
            "money": "1",
        }).encode()
        req = urllib.request.Request(url, data=body, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.load(resp)
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError) as e:
        raise RuntimeError(f"KRX fetch failed: {e}")

    blocks = data.get("output") or data.get("OutBlock_1") or []
    if not blocks:
        raise RuntimeError(f"KRX response no rows: keys={list(data.keys())[:5]}")

    rows = []
    for b in blocks:
        try:
            d = b.get("TRD_DD") or b.get("trdDd")
            o = float(str(b.get("OPNPRC") or b.get("opnprc") or "0").replace(",", ""))
            h = float(str(b.get("HGPRC") or b.get("hgprc") or "0").replace(",", ""))
            lo = float(str(b.get("LWPRC") or b.get("lwprc") or "0").replace(",", ""))
            c = float(str(b.get("TDD_CLSPRC") or b.get("clsprc") or "0").replace(",", ""))
            v = float(str(b.get("ACC_TRDVOL") or b.get("trdvol") or "0").replace(",", ""))
            rows.append({"date": d.replace("/", "-"), "open": o, "high": h,
                         "low": lo, "close": c, "volume": v})
        except (ValueError, AttributeError):
            continue

    rows.sort(key=lambda r: r["date"])
    return rows[-days:] if rows else []


def _krx_check(ticker):
    # ISIN 체크섬 placeholder. KRX OTP가 검증을 안 하는 endpoint를 쓰므로 더미값.
    return "0"


# ----------------- source 3: 결정론적 더미 -----------------
def fetch_dummy(ticker, days, start_price=None):
    """ticker hash 시드로 재현 가능 가우시안 워크. 휴일 skip 안 함."""
    seed = int(hashlib.md5(ticker.encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)
    if start_price is None:
        start_price = 50 + (seed % 300)  # 50~349
    drift = (rng.random() - 0.5) * 0.002  # ±0.1%/day
    vol = 0.015 + rng.random() * 0.015    # 1.5~3% daily sigma

    rows = []
    price = float(start_price)
    today = datetime.utcnow().date()
    # 영업일만 — 주말 skip
    d = today - timedelta(days=days * 2)
    while len(rows) < days:
        if d.weekday() < 5:  # Mon-Fri
            ret = rng.gauss(drift, vol)
            o = price
            c = price * (1 + ret)
            h = max(o, c) * (1 + abs(rng.gauss(0, vol / 3)))
            lo = min(o, c) * (1 - abs(rng.gauss(0, vol / 3)))
            v = int(50000 + rng.random() * 200000)
            rows.append({
                "date": d.isoformat(),
                "open": round(o, 2), "high": round(h, 2),
                "low": round(lo, 2), "close": round(c, 2),
                "volume": v,
            })
            price = c
        d += timedelta(days=1)
    return rows[-days:]


# ----------------- 디스패치 -----------------
def fetch(ticker, days=60, source="auto"):
    """source: auto | yfinance | krx | dummy
    auto = yfinance → krx(한국 6자리만) → dummy 순으로 fallback.
    각 단계 실패는 stderr로 보고 후 다음 단계.
    """
    attempts = []
    order = []
    if source == "auto":
        order = ["yfinance"]
        if ticker.isdigit() and len(ticker) == 6:
            order.append("krx")
        order.append("dummy")
    else:
        order = [source]

    for src in order:
        try:
            if src == "yfinance":
                rows = fetch_yfinance(ticker, days)
            elif src == "krx":
                rows = fetch_krx(ticker, days)
            elif src == "dummy":
                rows = fetch_dummy(ticker, days)
            else:
                raise RuntimeError(f"unknown source {src!r}")
            if rows:
                return rows, src, attempts
            attempts.append(f"{src}: empty rows")
        except Exception as e:
            attempts.append(f"{src}: {e}")
            print(f"[fetch] {src} failed: {e}", file=sys.stderr)
    raise RuntimeError(f"all sources failed: {attempts}")


def write_csv(rows, out_path):
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_HEADER)
        w.writeheader()
        for r in rows:
            w.writerow({k: r[k] for k in CSV_HEADER})


def main(argv=None):
    p = argparse.ArgumentParser(description="OHLCV fetcher → CSV (PLAY14 호환)")
    p.add_argument("ticker", help="종목 코드. 한국은 6자리 (예: 298040), 미국은 심볼 (예: AAPL)")
    p.add_argument("--days", type=int, default=60)
    p.add_argument("--source", choices=["auto", "yfinance", "krx", "dummy"], default="auto")
    p.add_argument("--out", default=None, help="출력 경로. 미지정 시 stdout으로 CSV.")
    args = p.parse_args(argv)

    rows, used, attempts = fetch(args.ticker, args.days, args.source)
    print(f"[fetch] source={used} rows={len(rows)} ticker={args.ticker}", file=sys.stderr)
    if attempts:
        for a in attempts:
            print(f"[fetch]   tried: {a}", file=sys.stderr)

    if args.out:
        write_csv(rows, args.out)
        print(f"[fetch] wrote {args.out}", file=sys.stderr)
    else:
        w = csv.DictWriter(sys.stdout, fieldnames=CSV_HEADER)
        w.writeheader()
        for r in rows:
            w.writerow({k: r[k] for k in CSV_HEADER})


if __name__ == "__main__":
    main()
