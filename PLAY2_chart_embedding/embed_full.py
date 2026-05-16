"""풀 차트(27×22) 임베딩 + 클러스터링.

charts_full.npz (int8 [N,27,22], alphabet) → 셀 원-핫 평탄화 (N, 27*22*A) sparse
→ TruncatedSVD (n_components=64) → MiniBatchKMeans (K=20) → cluster_summary

산출:
  cache/full/embedding_pca.npy            (N, 64) float32
  cache/full/clusters_K20.npy             (N,) int32
  output/full/cluster_summary_K20.csv     클러스터별 통계
  output/full/cluster_centroids.txt       클러스터당 5개 샘플 텍스트 차트
"""
from __future__ import annotations
import json, sys, time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix, identity
from sklearn.decomposition import TruncatedSVD
from sklearn.cluster import MiniBatchKMeans

HERE = Path(__file__).resolve().parent
CACHE_FULL = HERE / "cache" / "full"
OUT_FULL = HERE / "output" / "full"

K = 20
PCA_DIM = 64
SEED = 42


def main():
    t0 = time.time()
    OUT_FULL.mkdir(parents=True, exist_ok=True)

    # 1) load grids
    z = np.load(CACHE_FULL / "charts_full.npz", allow_pickle=False)
    grids = z["grids"]            # (N, 27, 22) int8
    alphabet = list(z["alphabet"])
    A = len(alphabet)
    N, R, C = grids.shape
    print(f"grids={grids.shape} alphabet={A} elapsed={time.time()-t0:.1f}s", flush=True)

    # 2) sparse one-hot flatten: each sample → R*C*A dim sparse vector
    # row indices: i (sample), col indices: r*C*A + c*A + grids[i,r,c]
    flat = grids.reshape(N, R * C).astype(np.int32)   # (N, 594)
    cell_idx = np.arange(R * C, dtype=np.int32)        # 0..593
    base = cell_idx * A                                # offset per cell
    col_indices = (flat + base[None, :]).reshape(-1)   # (N*594,)
    row_indices = np.repeat(np.arange(N, dtype=np.int32), R * C)
    data = np.ones(N * R * C, dtype=np.float32)
    X = csr_matrix((data, (row_indices, col_indices)), shape=(N, R * C * A))
    print(f"sparse shape={X.shape} nnz={X.nnz} elapsed={time.time()-t0:.1f}s", flush=True)

    # 3) TruncatedSVD (works on sparse, fast)
    svd = TruncatedSVD(n_components=PCA_DIM, random_state=SEED)
    emb = svd.fit_transform(X).astype(np.float32)
    print(f"SVD done emb={emb.shape} explained_var={svd.explained_variance_ratio_.sum():.3f} elapsed={time.time()-t0:.1f}s", flush=True)
    np.save(CACHE_FULL / "embedding_pca.npy", emb)

    # 4) MiniBatchKMeans K=20
    km = MiniBatchKMeans(n_clusters=K, n_init=3, random_state=SEED, batch_size=1024, max_iter=300)
    labels = km.fit_predict(emb).astype(np.int32)
    print(f"KMeans done inertia={km.inertia_:.0f} elapsed={time.time()-t0:.1f}s", flush=True)
    np.save(CACHE_FULL / "clusters_K20.npy", labels)

    # 5) cluster summary
    samples = pd.read_parquet(HERE / "cache" / "samples.parquet")
    samples = samples.iloc[:N].reset_index(drop=True)
    samples["cluster"] = labels

    rows = []
    for cid in range(K):
        sub = samples[samples["cluster"] == cid]
        n = len(sub)
        if n == 0:
            continue
        ret = sub["ret_next"].values
        sign = sub["sign_next"].values
        up = (sign == "U").sum()
        down = (sign == "D").sum()
        rows.append({
            "cluster": cid, "n_samples": n,
            "up_count": int(up), "up_rate": up / n,
            "down_count": int(down), "down_rate": down / n,
            "mean_ret": float(np.mean(ret)),
            "median_ret": float(np.median(ret)),
            "p25_ret": float(np.percentile(ret, 25)),
            "p75_ret": float(np.percentile(ret, 75)),
        })
    df = pd.DataFrame(rows).sort_values("up_rate", ascending=False)
    df.to_csv(OUT_FULL / "cluster_summary_K20.csv", index=False)
    print(f"cluster_summary saved", flush=True)
    print(df.to_string(index=False), flush=True)

    # 6) centroids text — 클러스터당 5개 샘플의 그리드 텍스트로 출력
    rng = np.random.default_rng(SEED)
    centroids_lines = []
    for cid in df["cluster"].tolist():
        sub_idx = np.where(labels == cid)[0]
        pick = rng.choice(sub_idx, size=min(5, len(sub_idx)), replace=False)
        centroids_lines.append(f"=== cluster {cid} (n={len(sub_idx)}, up_rate={df[df['cluster']==cid]['up_rate'].iloc[0]:.4f}) ===")
        for k, idx in enumerate(pick):
            g = grids[idx]
            centroids_lines.append(f"-- sample {k+1}: code={samples.iloc[idx]['code']} ym={samples.iloc[idx]['year_month']} ret={samples.iloc[idx]['ret_next']:.4f} --")
            for r in range(R):
                centroids_lines.append("".join(alphabet[t] for t in g[r]))
        centroids_lines.append("")
    (OUT_FULL / "cluster_centroids.txt").write_text("\n".join(centroids_lines), encoding="utf-8")
    print(f"centroids text saved", flush=True)
    print(f"DONE elapsed={time.time()-t0:.1f}s", flush=True)


if __name__ == "__main__":
    main()
