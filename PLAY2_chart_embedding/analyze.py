"""4단계: 클러스터별 다음달 수익률 통계 + 클러스터 대표 차트 출력.

요약 CSV: output/cluster_summary.csv
대표 차트: output/cluster_centroids.txt
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
OUT = HERE / "output"
OUT.mkdir(exist_ok=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--clusters_path", default=str(CACHE / "clusters.csv"))
    ap.add_argument("--samples_path", default=str(CACHE / "samples.parquet"))
    ap.add_argument("--summary_path", default=str(OUT / "cluster_summary.csv"))
    ap.add_argument("--centroids_path", default=str(OUT / "cluster_centroids.txt"))
    ap.add_argument("--examples_per_cluster", type=int, default=5)
    args = ap.parse_args()

    if not Path(args.clusters_path).exists():
        print(f"FAILED: {args.clusters_path} 없음", flush=True)
        return 1
    if not Path(args.samples_path).exists():
        print(f"FAILED: {args.samples_path} 없음", flush=True)
        return 1

    print("[start] loading", flush=True)
    cl = pd.read_csv(args.clusters_path, dtype={"code": str, "year_month": str})
    samples = pd.read_parquet(args.samples_path)[["code", "year_month", "chart_text"]]
    samples["code"] = samples["code"].astype(str)
    samples["year_month"] = samples["year_month"].astype(str)
    merged = cl.merge(samples, on=["code", "year_month"], how="left")
    print(f"[loaded] clusters={cl.shape}, merged={merged.shape}", flush=True)

    rows = []
    for cid, sub in merged.groupby("cluster_id"):
        n = len(sub)
        up = (sub["sign_next"] == "U").sum()
        dn = (sub["sign_next"] == "D").sum()
        flat = (sub["sign_next"] == "F").sum()
        rows.append({
            "cluster_id": int(cid),
            "n_samples": n,
            "up_count": int(up),
            "down_count": int(dn),
            "flat_count": int(flat),
            "up_rate": round(up / n, 4),
            "down_rate": round(dn / n, 4),
            "mean_ret": round(sub["ret_next"].mean(), 4),
            "median_ret": round(sub["ret_next"].median(), 4),
            "p25_ret": round(sub["ret_next"].quantile(0.25), 4),
            "p75_ret": round(sub["ret_next"].quantile(0.75), 4),
        })
    summary = pd.DataFrame(rows).sort_values("up_rate", ascending=False)
    summary.to_csv(args.summary_path, index=False, encoding="utf-8-sig")
    print(f"[save] {Path(args.summary_path).name}", flush=True)

    n_all = len(merged)
    base_up = (merged["sign_next"] == "U").mean()
    base_mean = merged["ret_next"].mean()
    print(f"[baseline] N={n_all} up_rate={base_up:.4f} mean_ret={base_mean:.4f}", flush=True)

    rng = np.random.default_rng(0)
    lines = []
    lines.append(f"# 클러스터 대표 샘플 (각 클러스터에서 임의 {args.examples_per_cluster}개)")
    lines.append(f"# 베이스라인 N={n_all} up_rate={base_up:.4f} mean_ret={base_mean:.4f}")
    lines.append("")
    for cid in sorted(merged["cluster_id"].unique()):
        sub = merged[merged["cluster_id"] == cid].reset_index(drop=True)
        n = len(sub)
        up_rate = (sub["sign_next"] == "U").mean()
        mean_ret = sub["ret_next"].mean()
        lines.append("=" * 70)
        lines.append(f"cluster {cid} | N={n} | up_rate={up_rate:.4f} | mean_ret={mean_ret:.4f}")
        lines.append("=" * 70)
        idx = rng.choice(n, size=min(args.examples_per_cluster, n), replace=False)
        for i in sorted(idx):
            row = sub.iloc[i]
            lines.append(f"-- {row['code']} {row.get('name','')} {row['year_month']} "
                         f"ret_next={row['ret_next']:+.4f} sign={row['sign_next']}")
            lines.append(str(row["chart_text"]))
            lines.append("")
    Path(args.centroids_path).write_text("\n".join(lines), encoding="utf-8")
    print(f"[save] {Path(args.centroids_path).name}", flush=True)
    print("DONE", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
