"""text 차트 + SMA(20/60/120) overlay + 우측 매물대 사이드바.

mvp module_text_chart 스타일 참고 — *독립 구현* (PLAY 간 import 금지).
표준 라이브러리만, pandas/numpy 없음. 캔들 문자도 mvp와 동일 코딩
(BULL=█, BEAR=░, WICK=│, DOJI=0).

매물대는 우측 6칸 사이드바로 같은 가격 그리드 위에 정렬.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

BULL = "█"
BEAR = "░"
WICK = "│"
DOJI = "0"
EMPTY = " "

# SMA overlay 문자
SMA_CHARS = {20: "·", 60: "+", 120: "*"}


def load_ohlcv(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append({
                "date": r["date"],
                "open": float(r["open"]),
                "high": float(r["high"]),
                "low": float(r["low"]),
                "close": float(r["close"]),
                "volume": float(r["volume"]),
            })
    return rows


def sma(values, window):
    out = [None] * len(values)
    if window <= 0 or window > len(values):
        return out
    csum = 0.0
    for i, v in enumerate(values):
        csum += v
        if i >= window:
            csum -= values[i - window]
        if i >= window - 1:
            out[i] = csum / window
    return out


def price_to_row(p, lo, hi, rows):
    """가격 → 그리드 row index (0=top=high)."""
    if hi <= lo:
        return rows // 2
    ratio = (p - lo) / (hi - lo)
    row = int((1 - ratio) * (rows - 1) + 0.5)
    return max(0, min(rows - 1, row))


def render(rows, sma_windows=(20, 60, 120), height=24, vp_bins=None, vp_width=6):
    if not rows:
        return "(empty)"
    closes = [r["close"] for r in rows]
    lows = [r["low"] for r in rows]
    highs = [r["high"] for r in rows]
    lo, hi = min(lows), max(highs)
    n = len(rows)
    width = n

    # 캔들 그리드
    grid = [[EMPTY] * width for _ in range(height)]
    for x, r in enumerate(rows):
        hr = price_to_row(r["high"], lo, hi, height)
        lr = price_to_row(r["low"], lo, hi, height)
        ot = price_to_row(max(r["open"], r["close"]), lo, hi, height)
        ob = price_to_row(min(r["open"], r["close"]), lo, hi, height)
        # wick
        for y in range(hr, lr + 1):
            grid[y][x] = WICK
        # body
        if abs(r["close"] - r["open"]) / (abs(r["open"]) + 1e-10) < 1e-4:
            for y in range(min(ot, ob), max(ot, ob) + 1):
                grid[y][x] = DOJI
        else:
            ch = BULL if r["close"] >= r["open"] else BEAR
            for y in range(ot, ob + 1):
                grid[y][x] = ch

    # SMA overlay — 각 window 별 다른 문자
    sma_series = {w: sma(closes, w) for w in sma_windows}
    for w, series in sma_series.items():
        ch = SMA_CHARS.get(w, "x")
        for x, v in enumerate(series):
            if v is None:
                continue
            y = price_to_row(v, lo, hi, height)
            # 캔들 위에 안 덮어쓰도록 EMPTY일 때만
            if grid[y][x] == EMPTY:
                grid[y][x] = ch

    # 매물대 사이드바
    vp_bins = vp_bins or height
    counts = [0.0] * vp_bins
    for r in rows:
        tp = (r["high"] + r["low"] + r["close"]) / 3.0
        idx = price_to_row(tp, lo, hi, vp_bins)  # 0=top
        counts[idx] += r["volume"]
    max_v = max(counts) or 1
    sidebar = []
    for i in range(height):
        # height → vp_bins 매핑 (보통 동일)
        src = int(i * vp_bins / height)
        bar = int((counts[src] / max_v) * vp_width)
        sidebar.append("▏" + ("█" * bar).ljust(vp_width, "·"))

    # POC mark
    poc_idx = max(range(vp_bins), key=lambda i: counts[i])

    # 출력 — 좌측 가격 라벨, 캔들, 사이드바
    out = []
    out.append(f"as_of={rows[-1]['date']}  range={lo:.2f}~{hi:.2f}  n={n}  SMA: "
               + " ".join(f"{w}={SMA_CHARS[w]}" for w in sma_windows))
    out.append(f"매물대 우측바 (width={vp_width}, POC row={poc_idx}, "
               f"last_close={rows[-1]['close']:.2f})")
    for y in range(height):
        price = lo + (hi - lo) * (1 - y / (height - 1))
        line = f"{price:>10.2f} |" + "".join(grid[y]) + "|" + sidebar[y]
        if y == poc_idx:
            line += " ◀POC"
        out.append(line)
    out.append("           " + "-" * width)
    # X축 라벨 — 첫·중간·마지막
    label = [" "] * width
    for x in (0, n // 2, n - 1):
        s = rows[x]["date"][5:]  # MM-DD
        for j, c in enumerate(s):
            if x + j < width:
                label[x + j] = c
    out.append("           " + "".join(label))
    return "\n".join(out)


def main(argv=None):
    p = argparse.ArgumentParser(description="text 차트 + SMA + 매물대 overlay")
    p.add_argument("csv")
    p.add_argument("--height", type=int, default=24)
    p.add_argument("--sma", default="20,60,120",
                   help="SMA windows 쉼표 구분. 빈 문자열이면 SMA 비활성.")
    p.add_argument("--vp-width", type=int, default=6)
    args = p.parse_args(argv)

    rows = load_ohlcv(args.csv)
    sma_w = tuple(int(x) for x in args.sma.split(",") if x.strip()) if args.sma else ()
    print(render(rows, sma_windows=sma_w, height=args.height, vp_width=args.vp_width))


if __name__ == "__main__":
    main()
