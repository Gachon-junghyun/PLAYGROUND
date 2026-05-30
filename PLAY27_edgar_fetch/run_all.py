"""5종목 일괄 실행 (AAPL/NVDA/MSFT/TSLA/META)."""
from __future__ import annotations

import sys
import time
from pathlib import Path

from edgar_fetch import fetch_filings
from _renderer import render_markdown

TICKERS = ["AAPL", "NVDA", "MSFT", "TSLA", "META"]
DAYS = 90


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    out_dir = Path(__file__).parent
    ok = 0
    totals: list[tuple[str, int, int]] = []  # (ticker, total, 8K count)
    cat_totals: dict[str, int] = {}
    for t in TICKERS:
        try:
            rows, cik, name = fetch_filings(t, days=DAYS)
            md = render_markdown(t, cik, rows, DAYS, company_name=name)
            out_path = out_dir / f"report_{t}.md"
            out_path.write_text(md, encoding="utf-8")
            eightk = sum(1 for r in rows if r.form.upper().startswith("8-K"))
            totals.append((t, len(rows), eightk))
            for r in rows:
                cat_totals[r.category] = cat_totals.get(r.category, 0) + 1
            print(f"  {t}: {len(rows)} filings ({eightk} 8-K) -> {out_path.name}")
            ok += 1
        except Exception as e:
            print(f"  {t}: FAILED - {e}", file=sys.stderr)
        time.sleep(0.3)

    print()
    print("== Summary ==")
    for t, total, eightk in totals:
        print(f"  {t}: total={total}, 8-K={eightk}")
    print(f"  Category totals: {cat_totals}")
    print(f"DONE: {ok}/{len(TICKERS)}")


if __name__ == "__main__":
    main()
