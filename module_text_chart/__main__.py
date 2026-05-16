# FILE: projects/chart_pipeline/module_text_chart/__main__.py
"""CLI 진입점.  사용:  python -m module_text_chart <ticker>"""
from __future__ import annotations

import sys

from .make_chart import save_text_chart


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: python -m module_text_chart <ticker>   (예: 005930.KS)")
        sys.exit(1)
    saved = save_text_chart(sys.argv[1])
    print(f"saved: {saved}")


if __name__ == "__main__":
    main()
