"""(후속 B-1) 정규화 가격 시계열 + PCA + KMeans.

각 (code, year_month) 샘플의 일봉 close를 그 달 첫 거래일=1로 정규화 → 길이 20으로 우측 패딩(마지막 값 반복) → z-score(샘플 내부) → PCA 8 → MiniBatchKMeans K=20.

다음달 라벨(ret_next, sign_next)은 기존 cache/samples.parquet 에서 그대로 재사용 — 클러스터링만 새 임베딩으로.
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
TARGET_LEN = 20


def build_series_matrix(samples: pd.DataFrame, ohlcv: pd.DataFrame) -> np.ndarray:
    """샘플 순서대로 길이 TARGET_LEN 정규화+z-score 시계열 행렬 반환."""
    ohlcv = ohlcv.copy()
    ohlcv["date"] = pd.to_datetime(ohlcv["date"])
    ohlcv["year_month"] = ohlcv["date"].dt.to_period("M").astype(str)

    closes_by_code: dict[str, pd.DataFrame] = {
        c: g.sort_values("date") for c, g in ohlcv.groupby("code")
    }

    N = len(samples)
    X = np.zeros((N, TARGET_LEN), dtype=np.float32)
    bad = 0
    for i, row in enumerate(samples.itertuples(index=False)):
        sub = closes_by_code.get(row.code)
        if sub is None:
            bad += 1
            continue
        cur = sub[sub["year_month"] == row.year_month]["close"].values.astype(np.float64)
        if len(cur) == 0:
            bad += 1
            continue
        # cap at 22 (build_charts 와 동일하게 마지막 22일만 — 단 TARGET_LEN=20)
        cur = cur[-TARGET_LEN:] if len(cur) >= TARGET_LEN else cur
        norm = cur / cur[0]  # 첫일=1
        if len(norm) < TARGET_LEN:
            pad = np.full(TARGET_LEN - len(norm), norm[-1])
            norm = np.concatenate([norm, pad])
        # z-score
        mu = norm.mean()
        sd = norm.std()
        if sd > 0:
            norm = (norm - mu) / sd
        else:
            norm = norm - mu
        X[i] = norm.astype(np.float32)
    if bad:
        print(f"[warn] {bad} 샘플 매칭 실패", flush=True)
    return X


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", default=str(CACHE / "samples.parquet"))
    ap.add_argument("--ohlcv", default=str(CACHE / "ohlcv.parquet"))
    ap.add_argument("--k", type=int, default=20)
    ap.add_argument("--pca", type=int, default=8)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--cache_dir", default=str(CACHE / "emb_norm_series"))
    ap.add_argument("--out_dir", default=str(OUT / "emb_norm_series"))
    args = ap.parse_args()

    cache_dir = Path(args.cache_dir)
    out_dir = Path(args.out_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("[start] loading", flush=True)
    samples = pd.read_parquet(args.samples)
    ohlcv = pd.read_parquet(args.ohlcv)
    print(f"[loaded] samples={samples.shape}, ohlcv={ohlcv.shape}", flush=True)

    t0 = time.time()
    X = build_series_matrix(samples, ohlcv)
    print(f"[series] X.shape={X.shape} ({time.time()-t0:.1f}s)", flush=True)

    from sklearn.decomposition import PCA
    from sklearn.cluster import MiniBatchKMeans

    t0 = time.time()
    pca = PCA(n_components=args.pca, random_state=args.seed)
    Xp = pca.fit_transform(X)
    ev = float(pca.explained_variance_ratio_.sum())
    print(f"[pca] X.shape={Xp.shape} ev_sum={ev:.3f} ({time.time()-t0:.1f}s)", flush=True)

    np.save(cache_dir / "embeddings.npy", Xp.astype(np.float32))

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

    # cluster_summary
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

    # PCA explained variance 메모
    (cache_dir / "meta.txt").write_text(
        f"pca_dim={args.pca}\nev_sum={ev:.4f}\nN={len(out)}\nK={args.k}\n",
        encoding="utf-8",
    )
    print("DONE", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
