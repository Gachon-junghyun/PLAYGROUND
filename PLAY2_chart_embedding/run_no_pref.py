"""(개선 3) 우선주 제외 후 전체 파이프라인 재실행.

우선주 정의 (둘 중 하나라도 해당하면 제외):
  - 종목코드 마지막 자리가 '5' (한국 우선주 관행: 005935, 005385, 000155 등)
  - 종목명이 '우' 또는 '우B' 로 끝남 (현대차2우B, 미래에셋증권2우B 등)

기존 cache/ohlcv.parquet, cache/universe.csv 를 그대로 읽어 필터링만 새로 함.
fetch는 다시 안 함.

출력:
  cache/no_pref/universe.csv
  cache/no_pref/samples.parquet
  cache/no_pref/embeddings.npy
  cache/no_pref/clusters.csv
  output/no_pref/cluster_summary.csv
  output/no_pref/significance.csv
  output/no_pref/dropped_codes.csv

K=20 고정. PCA=64. MiniBatchKMeans + n_init=3 (기존 풀 파이프라인과 동일).
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import MiniBatchKMeans
from sklearn.decomposition import PCA

from text_chart.renderer import candle_grid
from text_chart._constants import TOKEN_VOCAB, TOKEN_ID

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
OUT = HERE / "output"
CACHE_NP = CACHE / "no_pref"
OUT_NP = OUT / "no_pref"
CACHE_NP.mkdir(parents=True, exist_ok=True)
OUT_NP.mkdir(parents=True, exist_ok=True)

# build_charts.py의 상수와 동일
MIN_DAYS = 10
COLS = 22
PRICE_ROWS = 16
VOL_ROWS = 4

K = 20
PCA_DIM = 64
SEED = 42


def is_preferred(code: str, name: str) -> bool:
    if code.endswith("5"):
        return True
    if name.endswith("우") or name.endswith("우B"):
        return True
    return False


def grid_to_tokens(grid):
    out = []
    for row in grid:
        for ch in row:
            out.append(TOKEN_ID.get(ch, 0))
    return out


def build_samples(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["year_month"] = df["date"].dt.to_period("M").astype(str)
    samples = []
    codes = sorted(df["code"].unique())
    for code in codes:
        sub = df[df["code"] == code].sort_values("date").reset_index(drop=True)
        if len(sub) == 0:
            continue
        name = sub["name"].iloc[0]
        months = sorted(sub["year_month"].unique())
        m_to_idx = {m: i for i, m in enumerate(months)}
        month_groups = {m: sub[sub["year_month"] == m] for m in months}
        for m in months:
            cur = month_groups[m]
            if len(cur) < MIN_DAYS:
                continue
            i = m_to_idx[m]
            if i + 1 >= len(months):
                continue
            nxt = month_groups[months[i + 1]]
            if len(nxt) < MIN_DAYS:
                continue
            ret_next = float(nxt["close"].iloc[-1] / nxt["close"].iloc[0] - 1)
            sign_next = "U" if ret_next > 0 else ("D" if ret_next < 0 else "F")
            grid = candle_grid(
                cur["open"].values.astype(float),
                cur["high"].values.astype(float),
                cur["low"].values.astype(float),
                cur["close"].values.astype(float),
                cur["volume"].values.astype(float),
                COLS, PRICE_ROWS, VOL_ROWS,
            )
            tokens = grid_to_tokens(grid)
            samples.append({
                "code": code, "name": name, "year_month": m,
                "n_days": len(cur), "ret_next": ret_next, "sign_next": sign_next,
                "grid_tokens": tokens,
            })
    return pd.DataFrame(samples)


def tokens_to_onehot(tokens_list, vocab_size):
    n = len(tokens_list)
    L = len(tokens_list[0])
    arr = np.zeros((n, L, vocab_size), dtype=np.float32)
    for i, toks in enumerate(tokens_list):
        for j, t in enumerate(toks):
            if 0 <= t < vocab_size:
                arr[i, j, t] = 1.0
    return arr.reshape(n, L * vocab_size)


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
    t_total = time.time()

    print("[start] reading cache/universe.csv + cache/ohlcv.parquet", flush=True)
    universe = pd.read_csv(CACHE / "universe.csv", dtype={"Code": str})
    ohlcv = pd.read_parquet(CACHE / "ohlcv.parquet")
    ohlcv["code"] = ohlcv["code"].astype(str)
    print(f"[load] universe={len(universe)} ohlcv={ohlcv.shape}", flush=True)

    pref_mask = universe.apply(
        lambda r: is_preferred(r["Code"], r["Name"]), axis=1
    )
    dropped = universe[pref_mask].copy()
    kept = universe[~pref_mask].copy()
    dropped.to_csv(OUT_NP / "dropped_codes.csv", index=False, encoding="utf-8-sig")
    print(f"[filter] dropped={len(dropped)} kept={len(kept)}", flush=True)
    print(dropped[["Code", "Name"]].to_string(index=False), flush=True)

    kept_codes = set(kept["Code"])
    ohlcv_f = ohlcv[ohlcv["code"].isin(kept_codes)].copy()
    print(f"[filter ohlcv] {ohlcv.shape} → {ohlcv_f.shape}", flush=True)

    kept.to_csv(CACHE_NP / "universe.csv", index=False, encoding="utf-8-sig")

    t1 = time.time()
    samples = build_samples(ohlcv_f)
    print(f"[build] N={len(samples)} ({time.time()-t1:.1f}s)", flush=True)
    if len(samples) == 0:
        print("FAILED: 샘플 0개", flush=True)
        return 1
    samples.to_parquet(CACHE_NP / "samples.parquet", index=False)

    t1 = time.time()
    X = tokens_to_onehot(samples["grid_tokens"].tolist(), len(TOKEN_VOCAB))
    print(f"[onehot] X={X.shape} ({time.time()-t1:.1f}s)", flush=True)

    t1 = time.time()
    pca = PCA(n_components=PCA_DIM, random_state=SEED)
    Xp = pca.fit_transform(X).astype(np.float32)
    print(f"[pca] X={Xp.shape} ev_sum={pca.explained_variance_ratio_.sum():.3f} "
          f"({time.time()-t1:.1f}s)", flush=True)
    np.save(CACHE_NP / "embeddings.npy", Xp)

    t1 = time.time()
    km = MiniBatchKMeans(
        n_clusters=K, n_init=3, random_state=SEED, batch_size=1024, max_iter=100,
    )
    labels = km.fit_predict(Xp)
    print(f"[kmeans] K={K} inertia={km.inertia_:.1f} ({time.time()-t1:.1f}s)",
          flush=True)

    cl = samples[["code", "name", "year_month", "n_days", "ret_next", "sign_next"]].copy()
    cl["cluster_id"] = labels
    cl.to_csv(CACHE_NP / "clusters.csv", index=False, encoding="utf-8-sig")

    summary = cluster_summary(cl)
    summary.to_csv(OUT_NP / "cluster_summary.csv", index=False, encoding="utf-8-sig")

    n_all = len(cl)
    base_up = (cl["sign_next"] == "U").mean()
    base_mean = cl["ret_next"].mean()
    print(f"[baseline] N={n_all} up_rate={base_up:.4f} mean_ret={base_mean:.4f}",
          flush=True)
    print(f"[result] best up_rate={summary['up_rate'].max():.4f} "
          f"worst up_rate={summary['up_rate'].min():.4f}",
          flush=True)
    print(f"[total] {time.time()-t_total:.1f}s", flush=True)
    print("DONE", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
