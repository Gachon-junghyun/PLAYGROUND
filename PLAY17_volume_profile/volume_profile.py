"""매물대(Volume Profile) — 가격 bin × 누적 거래량.

OHLCV CSV → 가격 범위를 N개 bin으로 분할 → 각 거래일 거래량을
해당 봉의 (high+low+close)/3 가까이에 가중 적재 → 누적 분포.

POC(Point of Control) = 거래량 최대 bin.
VA(Value Area) = 누적 거래량의 중앙 70% 구간 (POC에서 좌우 확장).
매물대 top-3 = 거래량 상위 3 bin.

text bar chart + JSON 출력. 권유 X, 시그널 X.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path


def load_ohlcv(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = {"date", "open", "high", "low", "close", "volume"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"CSV missing columns: {sorted(missing)}")
        for r in reader:
            rows.append({
                "date": r["date"],
                "open": float(r["open"]),
                "high": float(r["high"]),
                "low": float(r["low"]),
                "close": float(r["close"]),
                "volume": float(r["volume"]),
            })
    if not rows:
        raise ValueError("empty OHLCV")
    return rows


def compute_profile(rows, bins=30, weighting="tpv"):
    """가격 bin별 거래량 누적.

    weighting:
      - 'tpv': typical price ((h+l+c)/3)에 거래량 전부 적재 (단순·빠름)
      - 'hl_split': 봉의 high~low 범위에 거래량을 균등 분할 (정확하지만 약간 무거움)
    """
    lo = min(r["low"] for r in rows)
    hi = max(r["high"] for r in rows)
    if hi <= lo:
        raise ValueError(f"invalid price range: lo={lo} hi={hi}")
    width = (hi - lo) / bins
    counts = [0.0] * bins

    if weighting == "tpv":
        for r in rows:
            tp = (r["high"] + r["low"] + r["close"]) / 3.0
            idx = min(int((tp - lo) / width), bins - 1)
            counts[idx] += r["volume"]
    elif weighting == "hl_split":
        for r in rows:
            blo = max(int((r["low"] - lo) / width), 0)
            bhi = min(int((r["high"] - lo) / width), bins - 1)
            n = bhi - blo + 1
            share = r["volume"] / n
            for i in range(blo, bhi + 1):
                counts[i] += share
    else:
        raise ValueError(f"unknown weighting {weighting!r}")

    profile = []
    for i, c in enumerate(counts):
        profile.append({
            "bin": i,
            "price_low": round(lo + i * width, 4),
            "price_high": round(lo + (i + 1) * width, 4),
            "volume": c,
        })

    total = sum(counts)
    poc_idx = max(range(bins), key=lambda i: counts[i])

    # Value Area 70%: POC에서 좌우 큰 쪽으로 확장
    target = total * 0.70
    sel = {poc_idx}
    acc = counts[poc_idx]
    left, right = poc_idx - 1, poc_idx + 1
    while acc < target and (left >= 0 or right < bins):
        lv = counts[left] if left >= 0 else -1
        rv = counts[right] if right < bins else -1
        if lv >= rv and left >= 0:
            sel.add(left)
            acc += counts[left]
            left -= 1
        elif right < bins:
            sel.add(right)
            acc += counts[right]
            right += 1
        else:
            break

    va_low_idx = min(sel)
    va_high_idx = max(sel)

    # 매물대 top-3
    top3_idx = sorted(range(bins), key=lambda i: counts[i], reverse=True)[:3]
    top3 = [profile[i] for i in top3_idx]

    return {
        "bins": bins,
        "weighting": weighting,
        "price_range": [lo, hi],
        "total_volume": total,
        "poc": profile[poc_idx],
        "value_area": {
            "low": profile[va_low_idx]["price_low"],
            "high": profile[va_high_idx]["price_high"],
            "volume_share": round(acc / total, 4) if total else 0,
        },
        "top3": top3,
        "profile": profile,
        "last_close": rows[-1]["close"],
    }


def render_text_chart(result, width=40):
    profile = result["profile"]
    max_v = max(p["volume"] for p in profile) or 1
    poc_price = (result["poc"]["price_low"] + result["poc"]["price_high"]) / 2
    va_lo, va_hi = result["value_area"]["low"], result["value_area"]["high"]
    last_close = result["last_close"]
    top3_bins = {p["bin"] for p in result["top3"]}

    lines = []
    lines.append(f"매물대 (bins={result['bins']}, weighting={result['weighting']})")
    lines.append(f"range {profile[0]['price_low']:>10} ~ {profile[-1]['price_high']:>10}    "
                 f"last_close={last_close}    POC≈{poc_price:.2f}")
    lines.append(f"VA[70%] {va_lo:.2f} ~ {va_hi:.2f}")
    lines.append("-" * (width + 32))

    for p in reversed(profile):  # 위가 고가
        bar_len = int((p["volume"] / max_v) * width) if max_v else 0
        bar = "█" * bar_len + "·" * (width - bar_len)
        markers = []
        mid = (p["price_low"] + p["price_high"]) / 2
        if va_lo <= mid <= va_hi:
            markers.append("VA")
        if p["bin"] == result["poc"]["bin"]:
            markers.append("POC")
        if p["bin"] in top3_bins and p["bin"] != result["poc"]["bin"]:
            markers.append("TOP")
        if p["price_low"] <= last_close < p["price_high"]:
            markers.append("◀NOW")
        tag = " " + " ".join(markers) if markers else ""
        lines.append(f"{p['price_high']:>10.2f} |{bar}|{tag}")
    return "\n".join(lines)


def main(argv=None):
    p = argparse.ArgumentParser(description="Volume Profile (매물대) from OHLCV CSV")
    p.add_argument("csv", help="OHLCV CSV 경로 (date,open,high,low,close,volume)")
    p.add_argument("--bins", type=int, default=30)
    p.add_argument("--weighting", choices=["tpv", "hl_split"], default="tpv")
    p.add_argument("--json", action="store_true", help="JSON으로 출력 (text chart 대신)")
    p.add_argument("--width", type=int, default=40, help="text chart bar 폭")
    args = p.parse_args(argv)

    rows = load_ohlcv(args.csv)
    result = compute_profile(rows, bins=args.bins, weighting=args.weighting)
    if args.json:
        # profile 전체는 너무 길어질 수 있으므로 요약본만
        compact = {k: v for k, v in result.items() if k != "profile"}
        compact["profile_len"] = len(result["profile"])
        print(json.dumps(compact, ensure_ascii=False, indent=2))
    else:
        print(render_text_chart(result, width=args.width))


if __name__ == "__main__":
    main()
