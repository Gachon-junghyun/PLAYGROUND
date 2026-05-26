"""PLAY21 unified_text_chart 핵심 로직.

module_text_chart의 plot_combined_chart(캔들+MA20/60+볼린저+거래량+RSI+OBV)에
PLAY19_chart_overlays의 매물대 사이드바와 추가 SMA(예: MA120) overlay를 통합.

legacy 호환 모드 (include_vp=False AND extra_ma=None)에선 plot_combined_chart를
직접 위임 호출 → byte-identical 자동 보장.
"""
from __future__ import annotations

import sys
from pathlib import Path

# PLAYGROUND 루트를 sys.path에 추가 (어디서 import 하든 module_text_chart 찾기 위함).
_PLAYGROUND_ROOT = Path(__file__).resolve().parent.parent
if str(_PLAYGROUND_ROOT) not in sys.path:
    sys.path.insert(0, str(_PLAYGROUND_ROOT))

import numpy as np
import pandas as pd

from module_text_chart._utils import (
    _price_to_row, _row_to_price, _fmt_price, _fmt_vol, _norm,
)
from module_text_chart._constants import (
    EMPTY, WICK, BULL_BODY, BEAR_BODY, DOJI_BODY,
    VOL_BULL, VOL_BEAR, _CANDLE_CHARS, _COMBINED_IND_CHARS,
    RSI_DOT, RSI_OB, RSI_OS,
    OBV_BULL, OBV_BEAR,
)
from module_text_chart.indicators import add_ma, add_bollinger
from module_text_chart.metadata import generate_metadata
from module_text_chart.renderer import (
    plot_combined_chart,
    _render_candle, _render_rsi_subplot, _render_obv_subplot,
)
from module_text_chart._ohlcv import fetch_ohlcv


# PLAY21 신규 — 매물대 사이드바 문자
VP_BAR = "█"
VP_EMPTY = "·"
VP_MARK = "▏"
POC_TAG = " ◀POC"

# PLAY21 신규 — 추가 MA(extra_ma) overlay 문자. _COMBINED_IND_CHARS에 없는 키일 때 사용.
EXTRA_MA_CHAR = "~"


def _compute_volume_profile(
    df: pd.DataFrame, rows: int, min_p: float, max_p: float
) -> tuple[list[float], int]:
    """가격 그리드 행별 누적 거래량 + POC row index.

    typical price = (high + low + close) / 3 를 _price_to_row 로 행에 매핑.
    """
    _df = _norm(df)
    h_arr = _df["high"].values.astype(float)
    l_arr = _df["low"].values.astype(float)
    c_arr = _df["close"].values.astype(float)
    vol_arr = _df["volume"].values.astype(float)
    counts = [0.0] * rows
    for ci in range(len(_df)):
        tp = (h_arr[ci] + l_arr[ci] + c_arr[ci]) / 3.0
        idx = _price_to_row(tp, min_p, max_p, rows)
        counts[idx] += vol_arr[ci]
    poc = max(range(rows), key=lambda i: counts[i])
    return counts, poc


def plot_unified_chart(
    df: pd.DataFrame,
    *,
    rows: int = 20,
    cols: int | None = None,
    vol_rows: int = 4,
    rsi_rows: int = 15,
    rsi_window: int = 14,
    obv_rows: int = 10,
    obv_window: int = 20,
    include_vp: bool = True,
    vp_width: int = 6,
    extra_ma: int | None = None,
) -> str:
    """캔들 + MA20/60 + (옵션) MA{extra_ma} + 볼린저 + 거래량 + RSI + OBV + (옵션) 매물대.

    legacy 호환 모드 (include_vp=False AND extra_ma=None)에선 plot_combined_chart를
    직접 위임 호출. byte-identical 보장.
    """
    # ── legacy 호환 분기 ──────────────────────────────────────────────────────
    if not include_vp and extra_ma is None:
        return plot_combined_chart(
            df,
            rows=rows,
            cols=cols,
            vol_rows=vol_rows,
            rsi_rows=rsi_rows,
            rsi_window=rsi_window,
            obv_rows=obv_rows,
            obv_window=obv_window,
        )

    # ── 통합 모드 — plot_combined_chart 로직 재현 + vp/extra_ma 추가 ───────────
    _df = _norm(df)
    if cols is not None:
        _df = _df.iloc[-cols:].reset_index(drop=True)

    n = len(_df)
    if n == 0:
        raise ValueError("DataFrame이 비어 있습니다.")

    o_arr = _df["open"].values.astype(float)
    h_arr = _df["high"].values.astype(float)
    l_arr = _df["low"].values.astype(float)
    c_arr = _df["close"].values.astype(float)
    min_p = float(l_arr.min())
    max_p = float(h_arr.max())

    # 캔들 그리드
    grid: list[list[str]] = [[EMPTY] * n for _ in range(rows)]
    for ci in range(n):
        col = [EMPTY] * rows
        _render_candle(
            col, o_arr[ci], h_arr[ci], l_arr[ci], c_arr[ci],
            min_p, max_p, rows,
        )
        for r in range(rows):
            grid[r][ci] = col[r]

    # MA + 볼린저 overlay (extra_ma 있으면 MA windows에 추가)
    ma_windows = [20, 60]
    if extra_ma is not None and extra_ma not in ma_windows:
        ma_windows.append(extra_ma)
    indicators = {**add_ma(_df, ma_windows), **add_bollinger(_df)}
    for name, series in indicators.items():
        ch = _COMBINED_IND_CHARS.get(name, EXTRA_MA_CHAR)
        arr = series.values.astype(float)
        for ci in range(min(n, len(arr))):
            v = arr[ci]
            if np.isnan(v):
                continue
            ri = _price_to_row(v, min_p, max_p, rows)
            if grid[ri][ci] not in _CANDLE_CHARS:
                grid[ri][ci] = ch

    # 가격 축 라벨
    label_row_set = {0, rows // 4, rows // 2, 3 * rows // 4, rows - 1}
    label_prices = {r: _row_to_price(r, min_p, max_p, rows) for r in label_row_set}
    lw = max(len(_fmt_price(p)) for p in label_prices.values())

    # 매물대 사이드바 사전 계산
    vp_lines: list[str] | None = None
    if include_vp and "volume" in _df.columns:
        counts, poc_row = _compute_volume_profile(_df, rows, min_p, max_p)
        max_v = max(counts) or 1.0
        vp_lines = []
        for r in range(rows):
            bar_n = int((counts[r] / max_v) * vp_width)
            line = VP_MARK + (VP_BAR * bar_n).ljust(vp_width, VP_EMPTY)
            if r == poc_row:
                line += POC_TAG
            vp_lines.append(line)

    # 가격 행 라인 합성 (vp 있으면 |grid|sidebar, 없으면 |grid 그대로)
    lines: list[str] = []
    for ri in range(rows):
        row_str = "".join(grid[ri])
        lbl = (
            _fmt_price(label_prices[ri]).rjust(lw)
            if ri in label_row_set else " " * lw
        )
        if vp_lines is not None:
            lines.append(f"{lbl} |{row_str}|{vp_lines[ri]}")
        else:
            lines.append(f"{lbl} |{row_str}")

    lines.append(" " * lw + "-+" + "-" * n)

    # 거래량 바
    if vol_rows > 0 and "volume" in _df.columns:
        v_arr = _df["volume"].values.astype(float)
        max_vol = v_arr.max()
        vgrid = [[" "] * n for _ in range(vol_rows)]
        for ci in range(n):
            if v_arr[ci] <= 0 or max_vol == 0:
                continue
            bar = max(1, round(v_arr[ci] / max_vol * vol_rows))
            v_ch = VOL_BULL if c_arr[ci] >= o_arr[ci] else VOL_BEAR
            for r in range(vol_rows - bar, vol_rows):
                vgrid[r][ci] = v_ch
        vol_lbl = _fmt_vol(max_vol)
        for ri, vrow in enumerate(vgrid):
            lbl = vol_lbl.rjust(lw) if ri == 0 else " " * lw
            lines.append(f"{lbl} |{''.join(vrow)}")

    # RSI / OBV 서브차트 (legacy 함수 그대로 호출)
    if rsi_rows > 0:
        lines.extend(_render_rsi_subplot(_df, lw, n, rsi_rows, rsi_window))
    if obv_rows > 0:
        lines.extend(_render_obv_subplot(_df, lw, n, obv_rows, obv_window))

    # 범례
    lines.append("")
    lines.append(
        f"  캔들: {BULL_BODY}=양봉  {BEAR_BODY}=음봉  {DOJI_BODY}=도지  {WICK}=꼬리"
    )
    ind_legend = "  지표: [.]MA20  [-]MA60"
    if extra_ma is not None:
        ind_legend += f"  [{EXTRA_MA_CHAR}]MA{extra_ma}"
    ind_legend += "  [^]BB상단  [·]BB중단  [v]BB하단"
    lines.append(ind_legend)
    lines.append(
        f"  RSI:  [{RSI_DOT}]중립  [{RSI_OB}]과매수(>70)  [{RSI_OS}]과매도(<30)  "
        f"[─]30/70선  [:]50선"
    )
    lines.append(
        f"  OBV:  [{OBV_BULL}]매수압력  [{OBV_BEAR}]매도압력  [─]중립선  "
        f"({obv_window}일 롤링)"
    )
    if vp_lines is not None:
        lines.append(
            f"  매물대 우측바: [{VP_BAR}]거래량 누적  [{VP_EMPTY}]빈공간  "
            f"◀POC=거래량 최대 가격대"
        )

    return "\n".join(lines)


def save_unified_chart(
    ticker: str,
    out_dir: str | Path | None = None,
    cols: int = 80,
    include_metadata: bool = True,
    include_vp: bool = True,
    extra_ma: int | None = 120,
) -> Path:
    """티커 1개 → 통합 차트 파일 저장 + 메타데이터.

    파라미터는 module_text_chart.make_chart.save_text_chart와 호환되도록 확장:
    - include_vp: 매물대 사이드바 (default True)
    - extra_ma: 추가 SMA window (default 120). None이면 비활성.
    """
    out_dir = Path(out_dir) if out_dir else Path(__file__).parent / "output"
    out_dir.mkdir(parents=True, exist_ok=True)

    df = fetch_ohlcv(ticker)
    if df.empty:
        raise RuntimeError(f"OHLCV 데이터 없음: {ticker}")

    chart_text = plot_unified_chart(
        df, cols=cols, include_vp=include_vp, extra_ma=extra_ma,
    )
    body = f"{ticker}\n\n{chart_text}"
    if include_metadata:
        body += "\n\n" + "── 메타데이터 " + "─" * 44 + "\n" + generate_metadata(df)

    safe = ticker.replace(".", "_")
    out_path = out_dir / f"{safe}_chart_unified.txt"
    out_path.write_text(body, encoding="utf-8")
    return out_path
