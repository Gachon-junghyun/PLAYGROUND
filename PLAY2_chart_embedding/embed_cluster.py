"""3단계: 토큰 그리드를 임베딩 → KMeans 클러스터링.

임베딩: 각 셀(440개)의 정수 토큰을 길이-7 원-핫으로 펼쳐 평탄화 (3080차원).
        대형 행렬에 KMeans n_init=10이 디스패치 45초를 초과하므로,
        기본은 MiniBatchKMeans + n_init=3. 필요시 --no-minibatch.
선택: --pca N 로 N차원 PCA 후 클러스터링.

출력:
  cache/embeddings.npy  — float32 임베딩 (PCA 적용 후 차원이면 그 차원)
  cache/clusters.csv    — code, name, year_month, n_days, ret_next, sign_next, cluster_id
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans, MiniBatchKMeans

from text_chart._constants import TOKEN_VOCAB

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"


def tokens_to_onehot(tokens_list, vocab_size):
    n = len(tokens_list)
    L = len(tokens_list[0])
    arr = np.zeros((n, L, vocab_size), dtype=np.float32)
    for i, toks in enumerate(tokens_list):
        for j, t in enumerate(toks):
            if 0 <= t < vocab_size:
                arr[i, j, t] = 1.0
    return arr.reshape(n, L * vocab_size)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in_path", default=str(CACHE / "samples.parquet"))
    ap.add_argument("--emb_path", default=str(CACHE / "embeddings.npy"))
    ap.add_argument("--clusters_path", default=str(CACHE / "clusters.csv"))
    ap.add_argument("--k", type=int, default=20)
    ap.add_argument("--pca", type=int, default=0)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--n_init", type=int, default=3)
    ap.add_argument("--no_minibatch", action="store_true",
                    help="기본은 MiniBatchKMeans. 풀 KMeans 쓰려면 이 플래그.")
    args = ap.parse_args()

    in_path = Path(args.in_path)
    if not in_path.exists():
        print(f"FAILED: {in_path} 없음. build_charts.py 먼저.", flush=True)
        return 1

    print(f"[start] reading {in_path.name}", flush=True)
    df = pd.read_parquet(in_path)
    print(f"[loaded] N={len(df)}", flush=True)

    tokens_list = df["grid_tokens"].tolist()
    L = len(tokens_list[0])
    bad = [i for i, t in enumerate(tokens_list) if len(t) != L]
    if bad:
        print(f"FAILED: 토큰 길이 불일치 {len(bad)}건.", flush=True)
        return 1

    t0 = time.time()
    X = tokens_to_onehot(tokens_list, len(TOKEN_VOCAB))
    print(f"[onehot] X.shape={X.shape} ({time.time()-t0:.1f}s)", flush=True)

    if args.pca > 0:
        from sklearn.decomposition import PCA
        t0 = time.time()
        pca = PCA(n_components=args.pca, random_state=args.seed)
        X = pca.fit_transform(X)
        print(f"[pca] X.shape={X.shape} ev_sum={pca.explained_variance_ratio_.sum():.3f} ({time.time()-t0:.1f}s)", flush=True)

    np.save(args.emb_path, X.astype(np.float32))
    print(f"[save] {Path(args.emb_path).name}", flush=True)

    t0 = time.time()
    if args.no_minibatch:
        km = KMeans(n_clusters=args.k, n_init=args.n_init, random_state=args.seed)
        algo = "kmeans"
    else:
        km = MiniBatchKMeans(n_clusters=args.k, n_init=args.n_init,
                             random_state=args.seed, batch_size=1024, max_iter=100)
        algo = "minibatch"
    labels = km.fit_predict(X)
    print(f"[{algo}] k={args.k} inertia={km.inertia_:.1f} ({time.time()-t0:.1f}s)", flush=True)

    out = df[["code", "name", "year_month", "n_days", "ret_next", "sign_next"]].copy()
    out["cluster_id"] = labels
    out.to_csv(args.clusters_path, index=False, encoding="utf-8-sig")
    print(f"[save] {Path(args.clusters_path).name} shape={out.shape}", flush=True)
    print("DONE", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
