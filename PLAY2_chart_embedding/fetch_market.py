"""(시장 통제) KOSPI 종합지수 일봉 fetch.

samples.parquet 의 기간(2020-01 ~ 2026-03 라벨)을 커버.
출력: cache/market/kospi.parquet 컬럼: date, close, ret_daily

FDR 의 pyopenssl 의존이 이 환경에선 깨져 있으므로, urllib3.contrib.pyopenssl 을 더미로 패치.
"""
from __future__ import annotations

import sys
import types
from pathlib import Path


def _patch_pyopenssl() -> None:
    mod = types.ModuleType("urllib3.contrib.pyopenssl")
    mod.inject_into_urllib3 = lambda: None
    mod.extract_from_urllib3 = lambda: None
    sys.modules["urllib3.contrib.pyopenssl"] = mod
    try:
        import urllib3.contrib  # noqa
        urllib3.contrib.pyopenssl = mod
    except Exception:
        pass


def main() -> int:
    _patch_pyopenssl()
    import FinanceDataReader as fdr  # noqa: E402
    import pandas as pd  # noqa: E402

    here = Path(__file__).resolve().parent
    out_dir = here / "cache" / "market"
    out_dir.mkdir(parents=True, exist_ok=True)

    # 라벨이 다음달 수익률이라 2026-03 라벨 → 2026-04 시계열까지 필요. 2026-05 까지 fetch.
    df = fdr.DataReader("KS11", "2019-12-01", "2026-05-08")
    if len(df) == 0:
        print("FAILED: empty KOSPI series", flush=True)
        return 1
    df = df.reset_index()[["Date", "Close"]].rename(columns={"Date": "date", "Close": "close"})
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    df = df.sort_values("date").reset_index(drop=True)
    df["ret_daily"] = df["close"].pct_change()

    out = out_dir / "kospi.parquet"
    df.to_parquet(out, index=False)
    print(f"[save] {out} rows={len(df)} date_range={df['date'].min().date()}..{df['date'].max().date()}", flush=True)
    print("DONE", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
