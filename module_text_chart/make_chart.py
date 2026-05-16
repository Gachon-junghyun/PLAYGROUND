# FILE: projects/chart_pipeline/module_text_chart/make_chart.py
"""
티커 1개 → 결과 폴더에 텍스트 차트 1개 저장.

Self-contained — core/* 에 의존하지 않는다. 폴더째 다른 레포로 옮겨도 동작.
외부 의존: pandas, numpy, yfinance.

기본은 plot_combined_chart (캔들 + MA20/60 + 볼린저밴드 + 거래량 + RSI + Rolling OBV)
+ 메타데이터 (이평선 / 볼린저 / 거래량 / 모멘텀 / RSI / 캔들힌트).

CLI:
    python -m module_text_chart 005930.KS
"""
from __future__ import annotations

from pathlib import Path

from ._ohlcv import fetch_ohlcv
from .renderer import plot_combined_chart
from .metadata import generate_metadata

DEFAULT_OUT_DIR = Path(__file__).parent / "output"
DEFAULT_COLS = 80


def save_text_chart(
    ticker: str,
    out_dir: Path | str = DEFAULT_OUT_DIR,
    cols: int = DEFAULT_COLS,
    include_metadata: bool = True,
) -> Path:
    """티커 하나 → 텍스트 차트 1개 파일 저장. 저장 경로 반환.

    ticker            : yfinance 심볼 (KOSPI 면 ``"005930.KS"``)
    out_dir           : 결과 폴더. 없으면 생성한다.
    cols              : 표시할 최근 캔들 수.
    include_metadata  : True 면 차트 하단에 generate_metadata() 결과를 덧붙인다.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    df = fetch_ohlcv(ticker)
    if df.empty:
        raise RuntimeError(f"OHLCV 데이터 없음: {ticker}")

    chart_text = plot_combined_chart(df, cols=cols)

    body = f"{ticker}\n\n{chart_text}"
    if include_metadata:
        body += "\n\n" + "── 메타데이터 " + "─" * 44 + "\n" + generate_metadata(df)

    safe = ticker.replace(".", "_")
    out_path = out_dir / f"{safe}_chart.txt"
    out_path.write_text(body, encoding="utf-8")
    return out_path
