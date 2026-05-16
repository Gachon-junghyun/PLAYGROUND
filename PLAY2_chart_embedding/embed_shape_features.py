"""(후속 B-2) 수동 shape features → KMeans.

샘플별 ~10개 피처:
  ret_month       : 월 수익률 (close[-1]/close[0]-1)
  max_drawdown    : 월중 고점 대비 최대 저점 비율
  recovery        : (close[-1]-low_min)/(high_max-low_min) — 0~1
  vol_daily       : 일간 수익률 표준편차
  skew            : 일간 수익률 왜도
  kurt            : 일간 수익률 첨도 (Fisher excess)
  high_pos        : argmax(high)/N (0~1)
  low_pos         : argmin(low)/N (0~1)
  bull_ratio      : (close>open)인 일수 비율
  vol_zscore      : 거래량의 월 내부 z-score 평균(=0). → "월 내부 변동성"으로 대체:
                     log(volume) 의 월 내부 표준편차로 한다.

표준화: 전체 N 샘플에 걸쳐 z-score → MiniBatchKMeans K=20.
다음달 라벨은 기존 samples.parquet 의 ret_next/sign_next 그대로.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import skew, kurtosis

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
OUT = HERE / "output"

FEATURE_NAMES = [
    "ret_month", "max_drawdown", "recovery",
    "vol_daily", "skew", "kurt",
    "high_pos", "low_pos", "bull_ratio", "vol_logstd",
]


def compute_features(o: np.ndarray, h: np.ndarray, l: np.ndarray,
                     c: np.ndarray, v: np.ndarray) -> np.ndarray:
    n = len(c)
    if n == 0:
        return np.full(len(FEATURE_NAMES), np.nan)
    ret_month = c[-1] / c[0] - 1.0
    high_max = h.max()
    low_min = l.min()
    # max drawdown: 매 시점까지의 high 의 cummax 대비 low 비율의 최저
    cum_high = np.maximum.accumulate(h)
    dd = l / cum_high - 1.0  # ≤ 0
    max_dd = float(dd.min())
    if high_max - low_min > 0:
        recovery = float((c[-1] - low_min) / (high_max - low_min))
    else:
        recovery = 0.5
    # 일간 수익률
    if n >= 2:
        ret_d = c[1:] / c[:-1] - 1.0
        vol_daily = float(ret_d.std())
        sk = float(skew(ret_d, bias=False)) if vol_daily > 0 else 0.0
        kt = float(kurtosis(ret_d, fisher=True, bias=False)) if vol_daily > 0 else 0.0
    else:
        vol_daily = sk = kt = 0.0
    high_pos = float(np.argmax(h)) / max(n - 1, 1)
    low_pos = float(np.argmin(l)) / max(n - 1, 1)
    bull_ratio = float(np.mean(c > o))
    vlog = np.log1p(v)
    vol_logstd = float(vlog.std())
    return np.array([
        ret_month, max_dd, recovery,
        vol_daily, sk, kt,
        high_pos, low_pos, bull_ratio, vol_logstd,
    ], dtype=np.float64)


def build_features_matrix(samples: pd.DataFrame, ohlcv: pd.DataFrame) -> np.ndarray:
    ohlcv = ohlcv.copy()
    ohlcv["date"] = pd.to_datetime(ohlcv["date"])
    ohlcv["year_month"] = ohlcv["date"].dt.to_period("M").astype(str)
    by_code: dict[str, pd.DataFrame] = {
        c: g.sort_values("date") for c, g in ohlcv.groupby("code")
    }
    N = len(samples)
    F = len(FEATURE_NAMES)
    X = np.zeros((N, F), dtype=np.float64)
    bad = 0
    for i, row in enumerate(samples.itertuples(index=False)):
        sub = by_code.get(row.code)
        if sub is None:
            bad += 1
            continue
        cur = sub[sub["year_month"] == row.year_month]
        if len(cur) == 0:
            bad += 1
            continue
        # build_charts 와 동일하게 마지막 22일까지만 — 사실 그대로 다 써도 무방.
        cur = cur.tail(22)
        feats = compute_features(
            cur["open"].values.astype(np.float64),
            cur["high"].values.astype(np.float64),
            cur["low"].values.astype(np.float64),
            cur["close"].values.astype(np.float64),
            cur["volume"].values.astype(np.float64),
        )
        X[i] = feats
    if bad:
        print(f"[warn] {bad} 매칭 실패", flush=True)
    return X


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", default=str(CACHE / "samples.parquet"))
    ap.add_argument("--ohlcv", default=str(CACHE / "ohlcv.parquet"))
    ap.add_argument("--k", type=int, default=20)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--cache_dir", default=str(CACHE / "emb_shape_features"))
    ap.add_argument("--out_dir", default=str(OUT / "emb_shape_features"))
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
    X = build_features_matrix(samples, ohlcv)
    print(f"[features] X.shape={X.shape} ({time.time()-t0:.1f}s)", flush=True)

    # NaN/Inf 안전
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    # z-score across N
    mu = X.mean(axis=0)
    sd = X.std(axis=0)
    sd = np.where(sd == 0, 1.0, sd)
    Xz = (X - mu) / sd
    np.save(cache_dir / "embeddings.npy", Xz.astype(np.float32))
    # feature 이름 기록
    (cache_dir / "feature_names.txt").write_text(
        "\n".join(FEATURE_NAMES), encoding="utf-8"
    )

    from sklearn.cluster import MiniBatchKMeans
    t0 = time.time()
    km = MiniBatchKMeans(n_clusters=args.k, n_init=3, random_state=args.seed,
                         batch_size=1024, max_iter=100)
    labels = km.fit_predict(Xz)
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
    print("DONE", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
