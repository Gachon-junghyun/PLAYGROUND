"""ATR 기반 진입/손절/익절/포지션사이즈 계산기.

매매 funnel 3~5단계 (진입가·타이밍·청산/사이즈)의 *계산 layer*.
사용자가 가설을 가지고 진입 의사가 있을 때, "이 가설대로 들어가면
얼마를 잃을 수 있고, 몇 R 목표가 어느 가격인가"를 산술적으로만 답한다.
권유 X, 시그널 생성 X, 백테스트 X.
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
        raise ValueError("CSV has no data rows")
    return rows


def compute_atr(rows, n=14):
    """Wilder ATR. 첫 n개 TR의 단순평균으로 시드 → 이후 Wilder smoothing."""
    if len(rows) < n + 1:
        raise ValueError(f"need >= {n + 1} rows for ATR({n}); got {len(rows)}")
    trs = []
    for i in range(1, len(rows)):
        h, l = rows[i]["high"], rows[i]["low"]
        c_prev = rows[i - 1]["close"]
        tr = max(h - l, abs(h - c_prev), abs(l - c_prev))
        trs.append(tr)
    atr = sum(trs[:n]) / n
    for tr in trs[n:]:
        atr = (atr * (n - 1) + tr) / n
    return atr


def recent_volatility(rows, lookback=20):
    """최근 종가 기준 일간 수익률 표준편차(연환산 X)."""
    if len(rows) < lookback + 1:
        lookback = len(rows) - 1
    closes = [r["close"] for r in rows[-(lookback + 1):]]
    rets = [(closes[i] / closes[i - 1] - 1.0) for i in range(1, len(closes))]
    if not rets:
        return 0.0
    mean = sum(rets) / len(rets)
    var = sum((x - mean) ** 2 for x in rets) / len(rets)
    return var ** 0.5


def plan_trade(
    rows,
    direction="long",
    entry_price=None,
    account_equity=10_000_000.0,
    risk_pct=0.01,
    stop_atr_mult=1.5,
    target_r_multiples=(1.0, 2.0, 3.0),
    atr_period=14,
):
    """
    Parameters
    ----------
    rows : list of OHLCV dicts (load_ohlcv 결과)
    direction : 'long' | 'short'
    entry_price : float | None — None이면 마지막 종가 사용
    account_equity : 계좌 자본 (원/달러 단위 무관, 일관성만 유지)
    risk_pct : 거래당 잃을 의향이 있는 자본 비율 (예: 0.01 = 1%)
    stop_atr_mult : 손절 거리 = ATR × stop_atr_mult.
                     이 거리가 곧 1R이 된다.
    target_r_multiples : R-multiple 목표가 리스트 (1R, 2R, 3R 등)
    atr_period : ATR 윈도 (보통 14)
    """
    if direction not in ("long", "short"):
        raise ValueError("direction must be 'long' or 'short'")
    if risk_pct <= 0 or risk_pct > 0.1:
        # 가드: 한 거래에 자본 10% 이상 거는 건 거의 항상 실수.
        raise ValueError(f"risk_pct out of sane range (0, 0.1]: {risk_pct}")

    atr = compute_atr(rows, n=atr_period)
    last_close = rows[-1]["close"]
    entry = float(entry_price) if entry_price is not None else last_close

    stop_distance = atr * stop_atr_mult  # = 1R
    if direction == "long":
        stop = entry - stop_distance
        targets = [(m, entry + m * stop_distance) for m in target_r_multiples]
    else:
        stop = entry + stop_distance
        targets = [(m, entry - m * stop_distance) for m in target_r_multiples]

    risk_per_share = abs(entry - stop)
    risk_amount = account_equity * risk_pct
    position_size = risk_amount / risk_per_share if risk_per_share > 0 else 0.0
    position_value = position_size * entry

    daily_sigma = recent_volatility(rows, lookback=20)
    # 진입가 대비 손절거리가 일간 sigma의 몇 배인가 — 너무 타이트하면 노이즈에 잘릴 가능성.
    stop_in_sigma = (stop_distance / entry) / daily_sigma if daily_sigma > 0 else float("inf")

    return {
        "as_of": rows[-1]["date"],
        "last_close": round(last_close, 4),
        "atr": round(atr, 4),
        "atr_period": atr_period,
        "daily_return_sigma_20d": round(daily_sigma, 5),
        "direction": direction,
        "entry": round(entry, 4),
        "stop": round(stop, 4),
        "stop_distance": round(stop_distance, 4),
        "stop_in_daily_sigma": round(stop_in_sigma, 2),
        "risk_per_share": round(risk_per_share, 4),
        "account_equity": account_equity,
        "risk_pct": risk_pct,
        "risk_amount": round(risk_amount, 2),
        "position_size_shares": round(position_size, 4),
        "position_value": round(position_value, 2),
        "exposure_pct_of_equity": round(position_value / account_equity * 100, 2)
        if account_equity > 0 else None,
        "targets": [
            {
                "R_multiple": round(m, 2),
                "price": round(p, 4),
                "profit_per_share": round(
                    (p - entry) if direction == "long" else (entry - p), 4
                ),
                "total_profit_at_target": round(
                    position_size * abs(p - entry), 2
                ),
            }
            for m, p in targets
        ],
        "notes": _build_notes(stop_in_sigma, position_value, account_equity, direction, entry, last_close),
    }


def _build_notes(stop_in_sigma, position_value, account_equity, direction, entry, last_close):
    notes = []
    if stop_in_sigma < 1.0:
        notes.append(
            f"stop이 일간 표준편차의 {stop_in_sigma:.2f}배. 일상 노이즈에 잘려나갈 확률 높음. "
            "stop_atr_mult를 키우거나, 진입을 미루는 게 합리적일 수 있음."
        )
    elif stop_in_sigma < 1.5:
        notes.append(f"stop이 일간 sigma의 {stop_in_sigma:.2f}배. 다소 타이트한 편.")
    if account_equity > 0 and position_value > account_equity:
        notes.append(
            f"position_value({position_value:,.0f})가 account_equity({account_equity:,.0f}) 초과. "
            "레버리지/마진 가정. 실제 거래계좌 한도 확인 필요."
        )
    if direction == "long" and entry < last_close * 0.95:
        notes.append(f"entry({entry})가 last_close({last_close})보다 5% 이상 낮음. 지정가 체결 가정인지 확인.")
    if direction == "long" and entry > last_close * 1.05:
        notes.append(f"entry({entry})가 last_close({last_close})보다 5% 이상 높음. 추격매수 형태.")
    if direction == "short" and entry > last_close * 1.05:
        notes.append(f"entry({entry})가 last_close({last_close})보다 5% 이상 높음. 공매도 지정가 가정.")
    return notes


def render_text(plan):
    L = []
    L.append(f"as_of={plan['as_of']}  last_close={plan['last_close']}  "
             f"ATR({plan['atr_period']})={plan['atr']}  "
             f"sigma_20d={plan['daily_return_sigma_20d']:.4f}")
    L.append(f"direction={plan['direction']}  entry={plan['entry']}  "
             f"stop={plan['stop']} (dist={plan['stop_distance']}, "
             f"= {plan['stop_in_daily_sigma']}× daily sigma)")
    L.append(f"risk_per_share={plan['risk_per_share']}  "
             f"× shares = risk_amount={plan['risk_amount']:,} "
             f"({plan['risk_pct']:.2%} of equity {plan['account_equity']:,.0f})")
    expo = plan['exposure_pct_of_equity']
    L.append(f"position_size={plan['position_size_shares']} shares  "
             f"value={plan['position_value']:,.2f}  exposure={expo}% of equity")
    L.append("targets (R-multiple ladder):")
    for t in plan['targets']:
        L.append(f"  {t['R_multiple']}R @ {t['price']}  "
                 f"per-share {t['profit_per_share']:+}  "
                 f"total_at_target {t['total_profit_at_target']:,.2f}")
    if plan['notes']:
        L.append("notes:")
        for n in plan['notes']:
            L.append(f"  - {n}")
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="trade_planner",
        description="ATR 기반 진입/손절/익절/사이즈 계산기 (매매 권유 X, 산술 layer)",
    )
    ap.add_argument("--csv", help="OHLCV CSV 경로. 헤더: date,open,high,low,close,volume")
    ap.add_argument("--demo", action="store_true",
                    help="번들된 sample_ohlcv.csv로 실행")
    ap.add_argument("--direction", choices=["long", "short"], default="long")
    ap.add_argument("--entry", type=float, default=None,
                    help="진입가. 미지정 시 마지막 종가 사용")
    ap.add_argument("--equity", type=float, default=10_000_000.0,
                    help="계좌 자본 (default 1천만)")
    ap.add_argument("--risk-pct", type=float, default=0.01,
                    help="거래당 리스크 비율 (default 0.01 = 1%%). 상한 0.1")
    ap.add_argument("--stop-atr", type=float, default=1.5,
                    help="손절 거리 = ATR × 이 값 (default 1.5)")
    ap.add_argument("--targets", type=str, default="1,2,3",
                    help="목표 R-multiple, 콤마 구분 (default 1,2,3)")
    ap.add_argument("--atr-period", type=int, default=14)
    ap.add_argument("--json", action="store_true", help="JSON 출력")
    args = ap.parse_args(argv)

    if not args.csv and not args.demo:
        ap.error("--csv 또는 --demo 중 하나는 필수")

    csv_path = Path(args.csv) if args.csv else Path(__file__).parent / "sample_ohlcv.csv"
    if not csv_path.exists():
        print(f"CSV not found: {csv_path}", file=sys.stderr)
        return 2

    rows = load_ohlcv(csv_path)
    try:
        target_mults = tuple(float(x.strip()) for x in args.targets.split(",") if x.strip())
    except ValueError:
        print(f"--targets parse error: {args.targets!r}", file=sys.stderr)
        return 2

    plan = plan_trade(
        rows,
        direction=args.direction,
        entry_price=args.entry,
        account_equity=args.equity,
        risk_pct=args.risk_pct,
        stop_atr_mult=args.stop_atr,
        target_r_multiples=target_mults,
        atr_period=args.atr_period,
    )
    if args.json:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
    else:
        print(render_text(plan))
    return 0


if __name__ == "__main__":
    sys.exit(main())
