# FILE: projects/chart_pipeline/module_text_chart/__init__.py
"""
Self-contained 텍스트 차트 모듈.

폴더째 다른 레포에 복사해도 동작한다 — core/* 에 의존하지 않는다.
외부 의존: pandas, numpy, yfinance.

빠른 사용:
    from module_text_chart import save_text_chart
    save_text_chart("005930.KS", out_dir="output")

직접 차트 함수 호출:
    from module_text_chart import plot_combined_chart, fetch_ohlcv
    df = fetch_ohlcv("AAPL")
    print(plot_combined_chart(df, cols=80))
"""
from .make_chart import save_text_chart
from .renderer import plot_text_chart, plot_combined_chart
from .indicators import add_ma, add_bollinger, add_rsi_line
from .metadata import generate_metadata
from ._ohlcv import fetch_ohlcv

__all__ = [
    "save_text_chart",
    "plot_text_chart",
    "plot_combined_chart",
    "add_ma",
    "add_bollinger",
    "add_rsi_line",
    "generate_metadata",
    "fetch_ohlcv",
]
