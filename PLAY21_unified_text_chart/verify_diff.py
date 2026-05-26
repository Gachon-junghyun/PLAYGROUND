"""legacy plot_combined_chart vs PLAY21 legacy 호환 모드 byte-identical 검증.

같은 DataFrame을 양쪽에 던져 출력이 동일한지 확인. yfinance 시점에 따라 df는
변할 수 있으므로 fetch 1회 결과를 양쪽에 *같이* 전달해 비교.

사용:
    cd PLAYGROUND
    python PLAY21_unified_text_chart/verify_diff.py 005930.KS
    python PLAY21_unified_text_chart/verify_diff.py AAPL --cols 60
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Windows cp949 콘솔에서 UTF-8 (── ◀ █ 등) 출력 깨지지 않도록 강제.
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# PLAYGROUND 루트 import path
_PLAYGROUND_ROOT = Path(__file__).resolve().parent.parent
if str(_PLAYGROUND_ROOT) not in sys.path:
    sys.path.insert(0, str(_PLAYGROUND_ROOT))

from module_text_chart._ohlcv import fetch_ohlcv
from module_text_chart.renderer import plot_combined_chart
from PLAY21_unified_text_chart.unified_chart import plot_unified_chart


def diff_check(ticker: str, cols: int) -> bool:
    print(f"=== {ticker}  cols={cols}  byte-identical 검증 ===")
    df = fetch_ohlcv(ticker)
    if df.empty:
        print(f"FAIL: OHLCV 데이터 없음 — {ticker}")
        return False

    legacy = plot_combined_chart(df, cols=cols)
    unified = plot_unified_chart(df, cols=cols, include_vp=False, extra_ma=None)

    if legacy == unified:
        print(
            f"PASS: {len(legacy)} chars 동일 — "
            f"legacy ≡ unified(include_vp=False, extra_ma=None)"
        )
        return True

    legacy_lines = legacy.splitlines()
    unified_lines = unified.splitlines()
    print(f"FAIL: legacy {len(legacy_lines)}줄 vs unified {len(unified_lines)}줄")
    for i, (l, u) in enumerate(zip(legacy_lines, unified_lines)):
        if l != u:
            print(f"  line {i + 1} 다름:")
            print(f"    legacy:  {l!r}")
            print(f"    unified: {u!r}")
            break
    if len(legacy_lines) != len(unified_lines):
        diff = abs(len(legacy_lines) - len(unified_lines))
        print(f"  줄 수 {diff}줄 차이.")
    return False


def main() -> None:
    p = argparse.ArgumentParser(description="legacy vs unified byte-identical 검증")
    p.add_argument("ticker", nargs="?", default="005930.KS")
    p.add_argument("--cols", type=int, default=80)
    args = p.parse_args()
    ok = diff_check(args.ticker, args.cols)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
