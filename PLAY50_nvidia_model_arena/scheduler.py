"""4시간마다 digest.run_once() 를 돌리는 자체 스케줄러.

백그라운드 패턴 — 진행 라인은 flush 로 흘리고, 매 사이클 끝에 sentinel(OK/FAIL)을 찍는다.
그래서 `python -u scheduler.py > run.log 2>&1` 로 띄워두고 중간에 죽어도 로그로 상태를 안다.

    # 포그라운드 (Ctrl-C 로 종료)
    python -u scheduler.py

    # 백그라운드 로그로 (PowerShell)
    Start-Process -NoNewWindow python "-u scheduler.py" -RedirectStandardOutput run.log -RedirectStandardError run.err

    # 검증용: 1시간 간격으로 2사이클만
    python -u scheduler.py --interval-hours 1 --max-cycles 2
"""
from __future__ import annotations

import argparse
import sys
import time
import traceback
from datetime import datetime

import digest

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def _log(msg: str):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def main():
    ap = argparse.ArgumentParser(description="다이제스트 4시간 주기 스케줄러")
    ap.add_argument("--interval-hours", type=float, default=4.0)
    ap.add_argument("--max-cycles", type=int, default=0, help="0=무한, N=N회 후 종료(검증용)")
    ap.add_argument("--window-hours", type=float, default=None,
                    help="뉴스 조회 윈도우(기본=interval-hours 와 동일)")
    ap.add_argument("--frac", type=float, default=0.35, help="제목 랜덤 샘플 비율(1.0=전체)")
    ap.add_argument("--chunk-size", type=int, default=200)
    ap.add_argument("--important-k", type=int, default=15)
    ap.add_argument("--chart-tickers", type=int, default=6)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    window = args.window_hours if args.window_hours is not None else args.interval_hours
    interval_s = args.interval_hours * 3600
    _log(f"스케줄러 시작 — 간격 {args.interval_hours}h, 윈도우 {window}h, "
         f"dry_run={args.dry_run}, max_cycles={args.max_cycles or '무한'}")

    cycle = 0
    while True:
        cycle += 1
        _log(f"===== 사이클 {cycle} 시작 =====")
        try:
            path = digest.run_once(
                window_hours=window, frac=args.frac, chunk_size=args.chunk_size,
                important_k=args.important_k, chart_tickers=args.chart_tickers,
                dry_run=args.dry_run,
            )
            _log(f"CYCLE {cycle} OK — {path}")
        except KeyboardInterrupt:
            raise
        except Exception:
            _log(f"CYCLE {cycle} FAIL\n{traceback.format_exc()}")

        if args.max_cycles and cycle >= args.max_cycles:
            _log(f"max_cycles({args.max_cycles}) 도달 — 종료")
            break

        _log(f"다음 사이클까지 {args.interval_hours}h 대기...")
        try:
            time.sleep(interval_s)
        except KeyboardInterrupt:
            _log("Ctrl-C — 스케줄러 종료")
            break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[스케줄러 종료]", flush=True)
