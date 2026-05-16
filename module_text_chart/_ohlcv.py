# FILE: projects/chart_pipeline/module_text_chart/_ohlcv.py
# COPIED FROM : core/screener/screener.py (Screener.get_ohlcv)
# COPIED AT   : 2026-04-30
# REASON      : 모듈을 다른 레포로 떼어내려면 core.screener 의존을 끊어야 함
# REMERGE?    : no  — 이 모듈은 yfinance 다운로드만 알면 되고, core 와 동기화 필요 없음
from __future__ import annotations

import pandas as pd
import yfinance as yf


def fetch_ohlcv(ticker: str, period: str = "1y") -> pd.DataFrame:
    """yfinance 로 OHLCV 다운로드. 컬럼명 소문자, 빈 결과는 빈 DF.

    ticker 는 yfinance 그대로 — KOSPI 면 ``"005930.KS"`` 처럼 suffix 포함해서 호출.
    """
    df = yf.download(ticker, period=period, progress=False)
    if df is None or df.empty:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [str(c).lower() for c in df.columns]
    return df
