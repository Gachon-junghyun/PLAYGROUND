"""1단계: 코스피 200 종목 일봉 OHLCV 수집.

종목 선정: FinanceDataReader StockListing('KOSPI')에서 시가총액 상위 200종목.
  → 사용자 합의: '현재 구성종목 기준이면 충분'. 과거 KOSPI 200 변경은 무시.
  → 한계: 우선주(005935 등)도 시총 상위면 포함됨. 일반적인 KOSPI 200과는 종목이 다소 다를 수 있음.

기간: 2020-01-01 ~ ARGS.end (기본 오늘).
출력: cache/ohlcv.parquet 단일 파일. 컬럼: code, name, date, open, high, low, close, volume.

진행 출력: 매 종목마다 [n/200] 형태 라인. flush=True. 끝나면 'DONE' 또는 'FAILED' sentinel.
재실행 시: cache/ohlcv.parquet이 이미 있고 --force 없으면 스킵.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pandas as pd
import FinanceDataReader as fdr

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
CACHE.mkdir(exist_ok=True)


def select_universe(top_n: int = 200) -> pd.DataFrame:
    listing = fdr.StockListing("KOSPI")
    listing = listing.dropna(subset=["Marcap"])
    listing = listing.sort_values("Marcap", ascending=False).head(top_n)
    return listing[["Code", "Name", "Marcap"]].reset_index(drop=True)


def fetch_one(code: str, start: str, end: str) -> pd.DataFrame:
    df = fdr.DataReader(code, start, end)
    if df is None or len(df) == 0:
        return pd.DataFrame()
    df = df.reset_index().rename(columns={
        "Date": "date", "Open": "open", "High": "high",
        "Low": "low", "Close": "close", "Volume": "volume",
    })
    keep = ["date", "open", "high", "low", "close", "volume"]
    df = df[keep]
    df["code"] = code
    return df


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2020-01-01")
    ap.add_argument("--end", default="2026-05-08")
    ap.add_argument("--top", type=int, default=200)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--limit", type=int, default=None,
                    help="디버깅용: 처음 N개 종목만")
    args = ap.parse_args()

    out_path = CACHE / "ohlcv.parquet"
    universe_path = CACHE / "universe.csv"

    if out_path.exists() and not args.force:
        print(f"[skip] {out_path} 이미 있음. --force로 재실행 가능.", flush=True)
        print("DONE", flush=True)
        return 0

    print(f"[start] start={args.start} end={args.end} top={args.top}", flush=True)

    try:
        universe = select_universe(args.top)
        if args.limit:
            universe = universe.head(args.limit)
        universe.to_csv(universe_path, index=False, encoding="utf-8-sig")
        print(f"[universe] {len(universe)} stocks selected → {universe_path.name}", flush=True)

        rows = []
        n = len(universe)
        t0 = time.time()
        for i, (code, name) in enumerate(zip(universe["Code"], universe["Name"]), 1):
            try:
                df = fetch_one(code, args.start, args.end)
                if len(df) > 0:
                    df["name"] = name
                    rows.append(df)
                if i % 10 == 0 or i == n:
                    elapsed = time.time() - t0
                    print(f"[fetch {i}/{n}] {code} {name} rows={len(df)} elapsed={elapsed:.1f}s",
                          flush=True)
            except Exception as e:
                print(f"[warn {i}/{n}] {code} {name} err: {e}", flush=True)

        if not rows:
            print("FAILED: 어떤 종목도 데이터를 받지 못했습니다.", flush=True)
            return 1

        full = pd.concat(rows, ignore_index=True)
        full = full[["code", "name", "date", "open", "high", "low", "close", "volume"]]
        full.to_parquet(out_path, index=False)
        print(f"[save] {out_path.name} shape={full.shape}", flush=True)
        print("DONE", flush=True)
        return 0
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"FAILED: {e}", flush=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
