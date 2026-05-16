"""풀 텍스트 차트(27×22, RSI/OBV/MA/볼린저 포함) 재생성 — 청크 모드.

각 청크는 cache/full/_chunks/chunk_NNNNN_NNNNN.npy (str dtype) 로 저장.
마지막에 --merge 로 합쳐서 cache/full/charts_full.npz 생성.

Usage:
  python -u build_charts_full2.py --start 0 --end 5000
  python -u build_charts_full2.py --start 5000 --end 10000
  python -u build_charts_full2.py --start 10000 --end 13971
  python -u build_charts_full2.py --merge
"""
from __future__ import annotations
import argparse, json, sys, time, traceback
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from text_chart import build_full_grid

PRICE_ROWS, VOL_ROWS, RSI_ROWS, COLS = 16, 4, 7, 22
TOTAL_ROWS = PRICE_ROWS + VOL_ROWS + RSI_ROWS  # 27

CACHE_FULL = HERE / "cache" / "full"
CHUNK_DIR = CACHE_FULL / "_chunks"


def build_chunk(start: int, end: int):
    t0 = time.time()
    samples = pd.read_parquet(HERE / "cache" / "samples.parquet")
    ohlcv = pd.read_parquet(HERE / "cache" / "ohlcv.parquet")
    print(f"loaded samples={len(samples)} ohlcv={len(ohlcv)} elapsed={time.time()-t0:.1f}s", flush=True)

    if end < 0 or end > len(samples):
        end = len(samples)
    samples = samples.iloc[start:end].reset_index(drop=True)
    N = len(samples)
    print(f"chunk [{start}:{end}] N={N}", flush=True)

    ohlcv["date"] = pd.to_datetime(ohlcv["date"])
    ohlcv["year_month"] = ohlcv["date"].dt.strftime("%Y-%m")
    ohlcv = ohlcv.sort_values(["code", "date"]).reset_index(drop=True)

    needed_codes = set(samples["code"].unique())
    ohlcv = ohlcv[ohlcv["code"].isin(needed_codes)]
    gb = dict(list(ohlcv.groupby(["code", "year_month"])))
    print(f"groupby done elapsed={time.time()-t0:.1f}s groups={len(gb)}", flush=True)

    grids = np.full((N, TOTAL_ROWS, COLS), " ", dtype="<U1")
    skipped = 0
    for i, row in enumerate(samples.itertuples(index=False)):
        try:
            sub = gb.get((row.code, row.year_month))
            if sub is None or len(sub) == 0:
                skipped += 1
                continue
            grids[i] = build_full_grid(
                sub[["open", "high", "low", "close", "volume"]],
                price_rows=PRICE_ROWS, vol_rows=VOL_ROWS,
                rsi_rows=RSI_ROWS, cols=COLS,
            )
        except Exception as e:
            skipped += 1
            if skipped <= 3:
                print(f"  skip {row.code} {row.year_month}: {e}", flush=True)

        if (i + 1) % 1000 == 0:
            elapsed = time.time() - t0
            rate = (i + 1) / max(elapsed - 1.7, 0.1)
            eta = (N - (i + 1)) / max(rate, 1e-6)
            print(f"  {i+1}/{N}  elapsed={elapsed:.1f}s  rate={rate:.0f}/s  eta={eta:.1f}s", flush=True)

    CHUNK_DIR.mkdir(parents=True, exist_ok=True)
    out = CHUNK_DIR / f"chunk_{start:05d}_{end:05d}.npy"
    np.save(out, grids)
    print(f"saved {out}  shape={grids.shape}  skipped={skipped}", flush=True)
    print(f"DONE elapsed={time.time()-t0:.1f}s", flush=True)


def merge():
    t0 = time.time()
    samples = pd.read_parquet(HERE / "cache" / "samples.parquet")
    N = len(samples)

    # 청크 파일 모으기
    chunk_files = sorted(CHUNK_DIR.glob("chunk_*.npy"))
    print(f"found {len(chunk_files)} chunks", flush=True)

    grids_full = np.full((N, TOTAL_ROWS, COLS), " ", dtype="<U1")
    for cf in chunk_files:
        # 파일명에서 start/end 파싱
        name = cf.stem  # chunk_00000_05000
        parts = name.split("_")
        start, end = int(parts[1]), int(parts[2])
        arr = np.load(cf)
        if arr.shape[0] != end - start:
            print("WARN " + cf.name + " shape=" + str(arr.shape) + " expected len " + str(end-start), flush=True)
        grids_full[start:end] = arr
        print(f"merged {cf.name} -> [{start}:{end}]", flush=True)

    # 알파벳 수집 + 정수 인코딩
    alphabet = sorted(np.unique(grids_full).tolist())
    print(f"alphabet({len(alphabet)})={alphabet}", flush=True)
    char_to_id = {c: i for i, c in enumerate(alphabet)}
    grids_int = np.zeros(grids_full.shape, dtype=np.int8)
    for c, i in char_to_id.items():
        grids_int[grids_full == c] = i

    out_path = CACHE_FULL / "charts_full.npz"
    np.savez_compressed(out_path, grids=grids_int, alphabet=np.array(alphabet))
    with open(CACHE_FULL / "alphabet.json", "w", encoding="utf-8") as f:
        json.dump(alphabet, f, ensure_ascii=False)
    print(f"saved {out_path}  shape={grids_int.shape}", flush=True)
    print(f"DONE elapsed={time.time()-t0:.1f}s", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--end", type=int, default=-1)
    ap.add_argument("--merge", action="store_true")
    args = ap.parse_args()
    if args.merge:
        merge()
    else:
        build_chunk(args.start, args.end)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("FAILED")
        traceback.print_exc()
        sys.exit(1)
