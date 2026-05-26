"""CLI 진입점 — python -m PLAY21_unified_text_chart <ticker>"""
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

# PLAYGROUND 루트를 sys.path에 추가 (cwd가 어디든 PLAY21·module_text_chart import 가능)
_PLAYGROUND_ROOT = Path(__file__).resolve().parent.parent
if str(_PLAYGROUND_ROOT) not in sys.path:
    sys.path.insert(0, str(_PLAYGROUND_ROOT))

from PLAY21_unified_text_chart.unified_chart import save_unified_chart


def main() -> None:
    p = argparse.ArgumentParser(
        description=(
            "통합 텍스트 차트 — 캔들 + MA20/60 + (옵션) MA{extra_ma} + 볼린저 + "
            "거래량 + RSI + OBV + (옵션) 매물대 사이드바 + 메타데이터."
        )
    )
    p.add_argument("ticker", help="yfinance 심볼 (예: 005930.KS, AAPL).")
    p.add_argument("--cols", type=int, default=80, help="표시 캔들 수. default 80.")
    p.add_argument(
        "--no-vp", action="store_true",
        help="매물대 사이드바 비활성. extra-ma 도 0이면 legacy(plot_combined_chart) byte-identical.",
    )
    p.add_argument("--no-meta", action="store_true", help="하단 메타데이터 비활성.")
    p.add_argument(
        "--extra-ma", type=int, default=120,
        help="추가 SMA window. 0이면 비활성. default 120.",
    )
    p.add_argument(
        "--out", default=None,
        help="저장 디렉토리. 미지정 시 PLAY21_unified_text_chart/output/.",
    )
    args = p.parse_args()

    saved = save_unified_chart(
        args.ticker,
        out_dir=args.out,
        cols=args.cols,
        include_metadata=not args.no_meta,
        include_vp=not args.no_vp,
        extra_ma=args.extra_ma if args.extra_ma > 0 else None,
    )
    print(f"saved: {saved}")


if __name__ == "__main__":
    main()
