"""간이 백테스트 — 한 줄 룰 + OHLCV → 거래 리스트 + 승률·평균 R.

룰 DSL (mini):
  entry: 'sma_cross_up:20,60'  | 'sma_cross_down:20,60'
         'breakout_high:20'    | 'breakdown_low:20'
  exit:  ATR(14) × stop_atr 손절, ATR × take_atr 익절. 둘 중 먼저 도달.
         max_hold_days 도달 시 시장가 청산 (close).

slippage_pct: 양방향 (entry/exit 둘 다 적용).

look-ahead 회피:
  - 시그널은 bar t의 종가에서 판단 → t+1 *시가*로 entry.
  - 손절/익절도 t+1 이후 bar의 high/low로 확인.

권유 X. 단순 룰 시뮬레이터.
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


def sma(values, w):
    out = [None] * len(values)
    if w <= 0:
        return out
    csum = 0.0
    for i, v in enumerate(values):
        csum += v
        if i >= w:
            csum -= values[i - w]
        if i >= w - 1:
            out[i] = csum / w
    return out


def wilder_atr(rows, n=14):
    """returns list of len(rows). atr[i] = ATR at the close of bar i. None until i >= n."""
    out = [None] * len(rows)
    trs = []
    for i in range(1, len(rows)):
        h, l = rows[i]["high"], rows[i]["low"]
        c_prev = rows[i - 1]["close"]
        tr = max(h - l, abs(h - c_prev), abs(l - c_prev))
        trs.append(tr)
    if len(trs) < n:
        return out
    atr = sum(trs[:n]) / n
    out[n] = atr
    for i in range(n + 1, len(rows)):
        tr = trs[i - 1]
        atr = (atr * (n - 1) + tr) / n
        out[i] = atr
    return out


def parse_rule(spec):
    name, _, args = spec.partition(":")
    parts = [int(x) for x in args.split(",") if x.strip()]
    return name.strip(), parts


def signal_at(rule_name, rule_args, rows, i, smas):
    """bar i의 종가 시점에서 entry 시그널 boolean. look-ahead 없음."""
    if i < 1:
        return False
    if rule_name == "sma_cross_up":
        fast, slow = rule_args
        s1, s2 = smas[fast][i], smas[slow][i]
        s1p, s2p = smas[fast][i - 1], smas[slow][i - 1]
        if None in (s1, s2, s1p, s2p):
            return False
        return s1p <= s2p and s1 > s2
    if rule_name == "sma_cross_down":
        fast, slow = rule_args
        s1, s2 = smas[fast][i], smas[slow][i]
        s1p, s2p = smas[fast][i - 1], smas[slow][i - 1]
        if None in (s1, s2, s1p, s2p):
            return False
        return s1p >= s2p and s1 < s2
    if rule_name == "breakout_high":
        (w,) = rule_args
        if i < w:
            return False
        window = [rows[j]["high"] for j in range(i - w, i)]
        return rows[i]["close"] > max(window)
    if rule_name == "breakdown_low":
        (w,) = rule_args
        if i < w:
            return False
        window = [rows[j]["low"] for j in range(i - w, i)]
        return rows[i]["close"] < min(window)
    raise ValueError(f"unknown rule {rule_name!r}")


def backtest(rows, entry_rule, direction="long",
             atr_period=14, stop_atr=1.5, take_atr=3.0,
             max_hold_days=20, slippage_pct=0.001):
    name, args = parse_rule(entry_rule)
    # 필요한 모든 SMA window 미리 계산
    needed = set()
    if name in ("sma_cross_up", "sma_cross_down"):
        needed.update(args)
    closes = [r["close"] for r in rows]
    smas = {w: sma(closes, w) for w in needed}
    atrs = wilder_atr(rows, atr_period)

    trades = []
    i = 1
    n = len(rows)
    while i < n - 1:
        if not signal_at(name, args, rows, i, smas):
            i += 1
            continue
        atr = atrs[i]
        if atr is None or atr <= 0:
            i += 1
            continue
        # entry: 다음 bar 시가
        entry_idx = i + 1
        entry_price_raw = rows[entry_idx]["open"]
        slip = 1 + slippage_pct if direction == "long" else 1 - slippage_pct
        entry_price = entry_price_raw * slip
        stop_dist = atr * stop_atr
        take_dist = atr * take_atr
        if direction == "long":
            stop = entry_price - stop_dist
            take = entry_price + take_dist
        else:
            stop = entry_price + stop_dist
            take = entry_price - take_dist

        # 시뮬레이션
        exit_idx, exit_price, exit_reason = None, None, None
        for j in range(entry_idx, min(entry_idx + max_hold_days, n)):
            h, l = rows[j]["high"], rows[j]["low"]
            if direction == "long":
                # 같은 bar에 stop/take 둘 다 hit하면 보수적으로 stop 우선
                if l <= stop:
                    exit_idx, exit_price, exit_reason = j, stop, "stop"
                    break
                if h >= take:
                    exit_idx, exit_price, exit_reason = j, take, "take"
                    break
            else:
                if h >= stop:
                    exit_idx, exit_price, exit_reason = j, stop, "stop"
                    break
                if l <= take:
                    exit_idx, exit_price, exit_reason = j, take, "take"
                    break
        if exit_idx is None:
            exit_idx = min(entry_idx + max_hold_days, n - 1)
            exit_price = rows[exit_idx]["close"]
            exit_reason = "time"
        # exit slippage 반대 방향
        exit_slip = 1 - slippage_pct if direction == "long" else 1 + slippage_pct
        exit_price *= exit_slip

        if direction == "long":
            pnl_per_share = exit_price - entry_price
        else:
            pnl_per_share = entry_price - exit_price
        r_multiple = pnl_per_share / stop_dist if stop_dist > 0 else 0

        trades.append({
            "signal_date": rows[i]["date"],
            "entry_date": rows[entry_idx]["date"],
            "exit_date": rows[exit_idx]["date"],
            "direction": direction,
            "entry": round(entry_price, 4),
            "stop": round(stop, 4),
            "take": round(take, 4),
            "exit": round(exit_price, 4),
            "exit_reason": exit_reason,
            "atr_at_entry": round(atr, 4),
            "pnl_per_share": round(pnl_per_share, 4),
            "r_multiple": round(r_multiple, 3),
            "hold_days": exit_idx - entry_idx,
        })
        # 다음 시그널은 청산 이후부터
        i = exit_idx + 1

    return trades


def summarize(trades):
    if not trades:
        return {"n_trades": 0, "win_rate": 0, "avg_r": 0, "sum_r": 0,
                "wins": 0, "losses": 0, "time_exits": 0, "best_r": 0, "worst_r": 0}
    rs = [t["r_multiple"] for t in trades]
    wins = sum(1 for r in rs if r > 0)
    losses = sum(1 for r in rs if r <= 0)
    return {
        "n_trades": len(trades),
        "win_rate": round(wins / len(rs), 3),
        "avg_r": round(sum(rs) / len(rs), 3),
        "sum_r": round(sum(rs), 3),
        "wins": wins,
        "losses": losses,
        "time_exits": sum(1 for t in trades if t["exit_reason"] == "time"),
        "best_r": round(max(rs), 3),
        "worst_r": round(min(rs), 3),
    }


def main(argv=None):
    p = argparse.ArgumentParser(description="간이 백테스트 (룰 1줄 + OHLCV)")
    p.add_argument("csv")
    p.add_argument("--rule", required=True,
                   help="entry 룰. 예: 'sma_cross_up:20,60', 'breakout_high:20'")
    p.add_argument("--direction", choices=["long", "short"], default="long")
    p.add_argument("--atr-period", type=int, default=14)
    p.add_argument("--stop-atr", type=float, default=1.5)
    p.add_argument("--take-atr", type=float, default=3.0)
    p.add_argument("--max-hold-days", type=int, default=20)
    p.add_argument("--slippage-pct", type=float, default=0.001)
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    rows = load_ohlcv(args.csv)
    trades = backtest(rows, args.rule, args.direction,
                      atr_period=args.atr_period, stop_atr=args.stop_atr,
                      take_atr=args.take_atr, max_hold_days=args.max_hold_days,
                      slippage_pct=args.slippage_pct)
    s = summarize(trades)

    if args.json:
        print(json.dumps({"summary": s, "trades": trades}, ensure_ascii=False, indent=2))
        return

    print(f"rule={args.rule}  dir={args.direction}  rows={len(rows)}  "
          f"stop_atr={args.stop_atr}R  take_atr={args.take_atr}R  "
          f"max_hold={args.max_hold_days}d  slip={args.slippage_pct*100:.2f}%")
    print(f"trades={s['n_trades']}  win_rate={s['win_rate']:.1%}  "
          f"avg_R={s['avg_r']:+.2f}  sum_R={s['sum_r']:+.2f}  "
          f"wins/losses={s['wins']}/{s['losses']}  time_exits={s['time_exits']}  "
          f"best_R={s['best_r']:+.2f}  worst_R={s['worst_r']:+.2f}")
    print("-" * 88)
    print(f"{'signal':10} {'entry':10} {'exit':10} {'dir':4} {'entry':>10} "
          f"{'exit':>10} {'why':5} {'R':>6} {'days':>4}")
    for t in trades:
        print(f"{t['signal_date']:10} {t['entry_date']:10} {t['exit_date']:10} "
              f"{t['direction']:4} {t['entry']:>10.2f} {t['exit']:>10.2f} "
              f"{t['exit_reason']:5} {t['r_multiple']:+6.2f} {t['hold_days']:>4}")


if __name__ == "__main__":
    main()
