"""(개선 1) K sweep: 한 번에 한 K만 돌리는 단일 K KMeans 실행기.

기존 cache/embeddings.npy (PCA 64) 와 cache/samples.parquet 을 그대로 사용.
디스패치 ~45초 한도 안에 끝내려고 K마다 별도 호출하는 구조.

사용:
  python -u sweep_k.py --k 10
  python -u sweep_k.py --k 20
  python -u sweep_k.py --k 40
  python -u sweep_k.py --k 80

출력:
  cache/sweep/clusters_K{K}.csv
  cache/sweep/inertia_K{K}.txt
  output/sweep/cluster_summary_K{K}.csv

집계는 별도로 aggregate_sweep.py에서.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import MiniBatchKMeans

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
OUT = HERE / "output"
CACHE_SWEEP = CACHE / "sweep"
OUT_SWEEP = OUT / "sweep"
CACHE_SWEEP.mkdir(parents=True, exist_ok=True)
OUT_SWEEP.mkdir(parents=True, exist_ok=True)


def cluster_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for cid, sub in df.groupby("cluster_id"):
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
    return pd.DataFrame(rows).sort_values("up_rate", ascending=False)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, required=True)
    ap.add_argument("--emb_path", default=str(CACHE / "embeddings.npy"))
    ap.add_argument("--samples_path", default=str(CACHE / "samples.parquet"))
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--n_init", type=int, default=3)
    args = ap.parse_args()

    K = args.k

    print(f"[start] K={K}", flush=True)
    t0 = time.time()
    X = np.load(args.emb_path)
    df = pd.read_parquet(args.samples_path)
    print(f"[load] X={X.shape} samples={df.shape} ({time.time()-t0:.1f}s)", flush=True)

    t1 = time.time()
    km = MiniBatchKMeans(
        n_clusters=K, n_init=args.n_init,
        random_state=args.seed, batch_size=1024, max_iter=100,
    )
    labels = km.fit_predict(X)
    fit_sec = time.time() - t1
    inertia = float(km.inertia_)
    print(f"[fit] K={K} inertia={inertia:.1f} ({fit_sec:.1f}s)", flush=True)

    out = df[["code", "name", "year_month", "n_days", "ret_next", "sign_next"]].copy()
    out["cluster_id"] = labels
    clusters_path = CACHE_SWEEP / f"clusters_K{K}.csv"
    out.to_csv(clusters_path, index=False, encoding="utf-8-sig")
    print(f"[save] {clusters_path.name}", flush=True)

    summary = cluster_summary(out)
    summary_path = OUT_SWEEP / f"cluster_summary_K{K}.csv"
    summary.to_csv(summary_path, index=False, encoding="utf-8-sig")
    print(f"[save] {summary_path.name}", flush=True)

    inertia_path = CACHE_SWEEP / f"inertia_K{K}.txt"
    inertia_path.write_text(
        f"K={K}\ninertia={inertia}\nfit_sec={fit_sec:.2f}\n",
        encoding="utf-8",
    )

    print(
        f"[result] K={K} max_up_rate={summary['up_rate'].max():.4f} "
        f"min_up_rate={summary['up_rate'].min():.4f}",
        flush=True,
    )
    print("DONE", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
