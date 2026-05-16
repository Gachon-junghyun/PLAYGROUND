"""(후속 B-3) DTW prototype 거리 임베딩.

각 샘플의 정규화 가격 시계열(=B-1과 동일하게 만든 길이 20 + z-score) 기반.
무작위 P=200 prototype 선택 → 모든 샘플 × prototype DTW 거리 행렬 (N × P)
→ PCA 16 → MiniBatchKMeans K=20.

DTW: dtaidistance.dtw.distance_matrix_fast (C 구현).
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
OUT = HERE / "output"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", default=str(CACHE / "samples.parquet"))
    ap.add_argument("--norm_series", default=str(CACHE / "emb_norm_series" / "embeddings.npy"),
                    help="(미사용) — 항상 raw 정규화 시계열을 다시 만든다 (PCA 적용 전)")
    ap.add_argument("--ohlcv", default=str(CACHE / "ohlcv.parquet"))
    ap.add_argument("--n_prototypes", type=int, default=200)
    ap.add_argument("--k", type=int, default=20)
    ap.add_argument("--pca", type=int, default=16)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--cache_dir", default=str(CACHE / "emb_dtw_prototype"))
    ap.add_argument("--out_dir", default=str(OUT / "emb_dtw_prototype"))
    args = ap.parse_args()

    cache_dir = Path(args.cache_dir)
    out_dir = Path(args.out_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    # raw 정규화 시계열 (PCA 전) 다시 만들기 위해 embed_norm_series.build_series_matrix 재사용
    from embed_norm_series import build_series_matrix

    print("[start] loading", flush=True)
    samples = pd.read_parquet(args.samples)
    ohlcv = pd.read_parquet(args.ohlcv)
    print(f"[loaded] samples={samples.shape}, ohlcv={ohlcv.shape}", flush=True)

    t0 = time.time()
    X = build_series_matrix(samples, ohlcv).astype(np.float64)
    print(f"[series] X.shape={X.shape} ({time.time()-t0:.1f}s)", flush=True)

    rng = np.random.default_rng(args.seed)
    proto_idx = rng.choice(len(X), size=args.n_prototypes, replace=False)
    proto = X[proto_idx]

    from dtaidistance import dtw
    t0 = time.time()
    N = len(X)
    P = args.n_prototypes
    # block 인자로 (0..N) × (N..N+P) 슬롯의 거리만 계산
    combined = np.vstack([X, proto]).copy()
    Dfull = dtw.distance_matrix_fast(combined, block=((0, N), (N, N + P)))
    # 결과 N+P × N+P 에서 위 블록 추출
    D = np.asarray(Dfull[:N, N:N + P])
    print(f"[dtw] D.shape={D.shape} ({time.time()-t0:.1f}s)", flush=True)

    # PCA 16
    from sklearn.decomposition import PCA
    from sklearn.cluster import MiniBatchKMeans

    t0 = time.time()
    pca = PCA(n_components=args.pca, random_state=args.seed)
    Xp = pca.fit_transform(D)
    ev = float(pca.explained_variance_ratio_.sum())
    print(f"[pca] X.shape={Xp.shape} ev_sum={ev:.3f} ({time.time()-t0:.1f}s)", flush=True)
    np.save(cache_dir / "embeddings.npy", Xp.astype(np.float32))
    np.save(cache_dir / "proto_idx.npy", proto_idx.astype(np.int64))

    t0 = time.time()
    km = MiniBatchKMeans(n_clusters=args.k, n_init=3, random_state=args.seed,
                         batch_size=1024, max_iter=100)
    labels = km.fit_predict(Xp)
    print(f"[kmeans] k={args.k} inertia={km.inertia_:.1f} ({time.time()-t0:.1f}s)", flush=True)

    out = samples[["code", "name", "year_month", "n_days", "ret_next", "sign_next"]].copy()
    out["cluster_id"] = labels
    clusters_path = cache_dir / "clusters.csv"
    out.to_csv(clusters_path, index=False, encoding="utf-8-sig")
    print(f"[save] {clusters_path}", flush=True)

    rows = []
    for cid, sub in out.groupby("cluster_id"):
        n = len(sub)
        up = int((sub["sign_next"] == "U").sum())
        dn = int((sub["sign_next"] == "D").sum())
        rows.append({
            "cluster_id": int(cid),
            "n_samples": n,
            "up_count": up,
            "down_count": dn,
            "up_rate": round(up / n, 4),
            "down_rate": round(dn / n, 4),
            "mean_ret": round(sub["ret_next"].mean(), 4),
            "median_ret": round(sub["ret_next"].median(), 4),
        })
    summary = pd.DataFrame(rows).sort_values("up_rate", ascending=False)
    summary_path = out_dir / "cluster_summary.csv"
    summary.to_csv(summary_path, index=False, encoding="utf-8-sig")
    print(f"[save] {summary_path}", flush=True)

    (cache_dir / "meta.txt").write_text(
        f"n_prototypes={P}\npca_dim={args.pca}\nev_sum={ev:.4f}\n",
        encoding="utf-8",
    )
    print("DONE", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
