"""2단계: 일봉 OHLCV → 월별 텍스트 차트 + 다음달 라벨.

윈도우 규칙:
  - 매 (종목, 캘린더 월) 페어를 한 샘플로. 한 달 안의 거래일이 그 달의 OHLCV를 구성.
  - cols=22로 고정. 한 달 거래일이 22 초과면 마지막 22일만 사용. 미만이면 우측 패딩 (renderer.py).
  - 한 달 안의 거래일이 MIN_DAYS(=10) 미만이면 그 샘플은 버린다 (휴장 많은 달, 신규 상장 등).
  - 라벨: 다음 캘린더 월의 (마지막 close / 첫 close - 1). 다음 달 거래일 < MIN_DAYS면 라벨 없음 → 샘플 버림.

출력: cache/samples.parquet
  컬럼: code, name, year_month (YYYY-MM), n_days, ret_next, sign_next ('U'/'D'), chart_text, grid_tokens (list[int])
  grid_tokens는 (price_rows+vol_rows)*cols 길이의 평탄화된 정수 토큰 리스트.

샘플당 그리드 크기 기본: 16+4=20 행 × 22 열 = 440 토큰.

진행: 50 종목마다 한 줄 찍음. sentinel 'DONE'/'FAILED'.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from text_chart.renderer import candle_grid, monthly_text_chart
from text_chart._constants import TOKEN_ID

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"

MIN_DAYS = 10  # 한 달 안 거래일 최소
COLS = 22
PRICE_ROWS = 16
VOL_ROWS = 4


def grid_to_tokens(grid: list[list[str]]) -> list[int]:
    out = []
    for row in grid:
        for ch in row:
            out.append(TOKEN_ID.get(ch, 0))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in_path", default=str(CACHE / "ohlcv.parquet"))
    ap.add_argument("--out_path", default=str(CACHE / "samples.parquet"))
    ap.add_argument("--limit_codes", type=int, default=None)
    args = ap.parse_args()

    in_path = Path(args.in_path)
    if not in_path.exists():
        print(f"FAILED: {in_path} 없음. 먼저 fetch_data.py 실행.", flush=True)
        return 1

    print(f"[start] reading {in_path.name}", flush=True)
    df = pd.read_parquet(in_path)
    df["date"] = pd.to_datetime(df["date"])
    df["year_month"] = df["date"].dt.to_period("M").astype(str)
    print(f"[loaded] {df.shape}, codes={df['code'].nunique()}", flush=True)

    codes = sorted(df["code"].unique())
    if args.limit_codes:
        codes = codes[:args.limit_codes]

    samples = []
    t0 = time.time()
    for ci, code in enumerate(codes, 1):
        sub = df[df["code"] == code].sort_values("date").reset_index(drop=True)
        if len(sub) == 0:
            continue
        name = sub["name"].iloc[0]
        # 월별 그룹
        months = sorted(sub["year_month"].unique())
        # 다음달 인덱스 매핑
        m_to_idx = {m: i for i, m in enumerate(months)}
        month_groups = {m: sub[sub["year_month"] == m] for m in months}

        for m in months:
            cur = month_groups[m]
            if len(cur) < MIN_DAYS:
                continue
            # 다음달 찾기
            i = m_to_idx[m]
            if i + 1 >= len(months):
                continue
            nxt = month_groups[months[i + 1]]
            if len(nxt) < MIN_DAYS:
                continue
            ret_next = float(nxt["close"].iloc[-1] / nxt["close"].iloc[0] - 1)
            sign_next = "U" if ret_next > 0 else ("D" if ret_next < 0 else "F")

            o = cur["open"].values.astype(float)
            h = cur["high"].values.astype(float)
            l = cur["low"].values.astype(float)
            c = cur["close"].values.astype(float)
            v = cur["volume"].values.astype(float)

            grid = candle_grid(o, h, l, c, v, COLS, PRICE_ROWS, VOL_ROWS)
            tokens = grid_to_tokens(grid)
            chart_text = "\n".join("".join(row) for row in grid)

            samples.append({
                "code": code,
                "name": name,
                "year_month": m,
                "n_days": len(cur),
                "ret_next": ret_next,
                "sign_next": sign_next,
                "chart_text": chart_text,
                "grid_tokens": tokens,
            })

        if ci % 50 == 0 or ci == len(codes):
            elapsed = time.time() - t0
            print(f"[charts {ci}/{len(codes)}] samples={len(samples)} elapsed={elapsed:.1f}s",
                  flush=True)

    if not samples:
        print("FAILED: 만들어진 샘플이 0개입니다.", flush=True)
        return 1

    out = pd.DataFrame(samples)
    out_path = Path(args.out_path)
    out.to_parquet(out_path, index=False)
    print(f"[save] {out_path.name} shape={out.shape}", flush=True)
    # 미리보기
    print(f"[stats] mean ret_next = {out['ret_next'].mean():.4f}, "
          f"up_rate = {(out['sign_next']=='U').mean():.4f}", flush=True)
    print("DONE", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
