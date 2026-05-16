"""(시장 통제) cluster_summary_{simple,capm}.csv 생성.

입력:
  cache/emb_norm_series/clusters_simple.csv
  cache/emb_norm_series/clusters_capm.csv

출력:
  output/market_neutral/cluster_summary_simple.csv
  output/market_neutral/cluster_summary_capm.csv

분석 로직: analyze.py 와 동일 — 클러스터별 N, up_rate (잔차>0 비율),
mean_ret (잔차 평균), median, p25, p75. 베이스라인은 전체 평균.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
OUT = HERE / "output" / "market_neutral"


def summarize(clusters_csv: Path, out_csv: Path) -> None:
    df = pd.read_csv(clusters_csv, dtype={"code": str, "year_month": str})
    base = {
        "N": len(df),
        "up_rate": (df["sign_next"] == "U").mean(),
        "mean_ret": df["ret_next"].mean(),
        "median_ret": df["ret_next"].median(),
    }
    print(f"[{clusters_csv.name}] baseline: {base}", flush=True)

    rows = []
    for cid, sub in df.groupby("cluster_id"):
        n = len(sub)
        up = int((sub["sign_next"] == "U").sum())
        down = int((sub["sign_next"] == "D").sum())
        rows.append({
            "cluster_id": int(cid),
            "n_samples": n,
            "up_count": up,
            "up_rate": round(up / n, 4),
            "down_count": down,
            "down_rate": round(down / n, 4),
            "mean_ret": round(sub["ret_next"].mean(), 4),
            "median_ret": round(sub["ret_next"].median(), 4),
            "p25_ret": round(sub["ret_next"].quantile(0.25), 4),
            "p75_ret": round(sub["ret_next"].quantile(0.75), 4),
        })
    out = pd.DataFrame(rows).sort_values("up_rate", ascending=False)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_csv, index=False, encoding="utf-8-sig")
    print(f"[save] {out_csv}", flush=True)
    print(out.head(3).to_string(index=False), flush=True)
    print(out.tail(3).to_string(index=False), flush=True)


def main() -> int:
    summarize(CACHE / "emb_norm_series" / "clusters_simple.csv",
              OUT / "cluster_summary_simple.csv")
    summarize(CACHE / "emb_norm_series" / "clusters_capm.csv",
              OUT / "cluster_summary_capm.csv")
    print("DONE", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
