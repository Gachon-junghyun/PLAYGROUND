"""(개선 1) sweep_k.py 결과들을 묶어 K 비교표 생성.

입력: cache/sweep/clusters_K{K}.csv, cache/sweep/inertia_K{K}.txt (각 K)
출력: output/sweep/k_comparison.csv

컬럼: K, baseline_up_rate, baseline_mean_ret, n_total,
      max_up_cluster_id, max_up_rate, max_up_n, max_up_diff_pp,
      min_up_cluster_id, min_up_rate, min_up_n, min_up_diff_pp,
      max_mean_ret, min_mean_ret, inertia, fit_sec
"""
from __future__ import annotations

import sys
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
CACHE_SWEEP = HERE / "cache" / "sweep"
OUT_SWEEP = HERE / "output" / "sweep"


def parse_inertia(path: Path) -> tuple[float, float]:
    inertia, fit_sec = float("nan"), float("nan")
    if not path.exists():
        return inertia, fit_sec
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("inertia="):
            inertia = float(line.split("=", 1)[1])
        elif line.startswith("fit_sec="):
            fit_sec = float(line.split("=", 1)[1])
    return inertia, fit_sec


def main() -> int:
    rows = []
    for k_path in sorted(CACHE_SWEEP.glob("clusters_K*.csv")):
        K = int(k_path.stem.replace("clusters_K", ""))
        df = pd.read_csv(k_path, dtype={"code": str, "year_month": str})
        n_total = len(df)
        base_up = (df["sign_next"] == "U").mean()
        base_mean = df["ret_next"].mean()

        per_c = (
            df.groupby("cluster_id")
            .agg(
                n=("ret_next", "size"),
                up_rate=("sign_next", lambda s: (s == "U").mean()),
                mean_ret=("ret_next", "mean"),
            )
            .reset_index()
        )
        max_up_row = per_c.loc[per_c["up_rate"].idxmax()]
        min_up_row = per_c.loc[per_c["up_rate"].idxmin()]

        inertia, fit_sec = parse_inertia(CACHE_SWEEP / f"inertia_K{K}.txt")

        rows.append({
            "K": K,
            "n_total": n_total,
            "baseline_up_rate": round(base_up, 4),
            "baseline_mean_ret": round(base_mean, 4),
            "max_up_cluster_id": int(max_up_row["cluster_id"]),
            "max_up_rate": round(max_up_row["up_rate"], 4),
            "max_up_n": int(max_up_row["n"]),
            "max_up_mean_ret": round(max_up_row["mean_ret"], 4),
            "max_up_diff_pp": round((max_up_row["up_rate"] - base_up) * 100, 2),
            "min_up_cluster_id": int(min_up_row["cluster_id"]),
            "min_up_rate": round(min_up_row["up_rate"], 4),
            "min_up_n": int(min_up_row["n"]),
            "min_up_mean_ret": round(min_up_row["mean_ret"], 4),
            "min_up_diff_pp": round((min_up_row["up_rate"] - base_up) * 100, 2),
            "max_mean_ret_in_any_cluster": round(per_c["mean_ret"].max(), 4),
            "min_mean_ret_in_any_cluster": round(per_c["mean_ret"].min(), 4),
            "inertia": round(inertia, 1),
            "fit_sec": fit_sec,
        })

    out = pd.DataFrame(rows).sort_values("K")
    out_path = OUT_SWEEP / "k_comparison.csv"
    out.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"[save] {out_path}", flush=True)
    print(out.to_string(index=False), flush=True)
    print("DONE", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
