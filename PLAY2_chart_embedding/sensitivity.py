"""(개선 4) Sensitivity 시나리오 한 개를 돌리는 단일 시나리오 실행기.

K=20 고정, 풀 universe 사용. 차트 크기 변형은 build → embed → cluster 전체 재실행,
라벨 변형은 기존 임베딩/클러스터 재사용 + 라벨만 재계산.

시나리오:
  baseline      — 기존 cache/clusters.csv + cache/samples.parquet 그대로 (복사용)
  chart_small   — price_rows=8, vol_rows=4, cols=22  (12×22)
  chart_large   — price_rows=24, vol_rows=6, cols=22 (30×22)
  chart_wide    — price_rows=16, vol_rows=4, cols=40 (20×40)
  label_5d      — 다음 5거래일 (close_5/close_1 - 1)
  label_20d     — 다음 20거래일
  label_3class  — 기존 ret_next 에 대해 |x|<0.005 면 F, 아니면 U/D

사용:
  python -u sensitivity.py --scenario chart_small

출력:
  cache/sensitivity/{scenario}/(필요시) samples.parquet, embeddings.npy, clusters.csv
  output/sensitivity/cluster_summary_{scenario}.csv
"""
from __future__ import annotations

import argparse
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
CACHE_S = CACHE / "sensitivity"
OUT_S = OUT / "sensitivity"
CACHE_S.mkdir(parents=True, exist_ok=True)
OUT_S.mkdir(parents=True, exist_ok=True)

MIN_DAYS = 10
K = 20
PCA_DIM = 64
SEED = 42

CHART_CONFIGS = {
    "chart_small": {"price_rows": 8,  "vol_rows": 4, "cols": 22},
    "chart_large": {"price_rows": 24, "vol_rows": 6, "cols": 22},
    "chart_wide":  {"price_rows": 16, "vol_rows": 4, "cols": 40},
}

# 라벨 변형은 기본 차트(16+4 × 22) 사용
DEFAULT_CHART = {"price_rows": 16, "vol_rows": 4, "cols": 22}


def grid_to_tokens(grid):
    out = []
    for row in grid:
        for ch in row:
            out.append(TOKEN_ID.get(ch, 0))
    return out


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
        })
    return pd.DataFrame(rows).sort_values("up_rate", ascending=False)


def build_samples(df: pd.DataFrame, cfg: dict, label_mode: str = "cal_month",
                  label_horizon_days: int = 0,
                  neutral_pct: float = 0.0) -> pd.DataFrame:
    """월별 샘플 생성. cfg = {price_rows, vol_rows, cols}.

    label_mode:
      - 'cal_month': 다음 캘린더 월의 last_close/first_close - 1 (기본)
      - 'next_n_days': 현재 월 마지막일 다음 거래일부터 N개 거래일 (close[N-1]/close[0]-1)
                       label_horizon_days 만큼.
      - 'cal_month_3class': cal_month 와 동일 ret_next 이지만 |x|<neutral_pct 이면 F.
    """
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["year_month"] = df["date"].dt.to_period("M").astype(str)

    samples = []
    codes = sorted(df["code"].unique())
    cols = cfg["cols"]
    price_rows = cfg["price_rows"]
    vol_rows = cfg["vol_rows"]

    for code in codes:
        sub = df[df["code"] == code].sort_values("date").reset_index(drop=True)
        if len(sub) == 0:
            continue
        name = sub["name"].iloc[0]
        months = sorted(sub["year_month"].unique())
        m_to_idx = {m: i for i, m in enumerate(months)}
        month_groups = {m: sub[sub["year_month"] == m] for m in months}

        # 종목별 close 시리즈를 거래일 순으로
        all_closes = sub["close"].values.astype(float)
        all_dates = sub["date"].values  # datetime64
        date_to_idx = {d: i for i, d in enumerate(all_dates)}

        for m in months:
            cur = month_groups[m]
            if len(cur) < MIN_DAYS:
                continue

            # 라벨 계산
            if label_mode == "cal_month" or label_mode == "cal_month_3class":
                i = m_to_idx[m]
                if i + 1 >= len(months):
                    continue
                nxt = month_groups[months[i + 1]]
                if len(nxt) < MIN_DAYS:
                    continue
                ret_next = float(nxt["close"].iloc[-1] / nxt["close"].iloc[0] - 1)
                if label_mode == "cal_month_3class":
                    if abs(ret_next) < neutral_pct:
                        sign_next = "F"
                    elif ret_next > 0:
                        sign_next = "U"
                    else:
                        sign_next = "D"
                else:
                    sign_next = "U" if ret_next > 0 else ("D" if ret_next < 0 else "F")
            elif label_mode == "next_n_days":
                # 현재 월 마지막일 다음 거래일부터 N개
                last_date = cur["date"].iloc[-1]
                last_idx = date_to_idx[np.datetime64(last_date)]
                start_idx = last_idx + 1
                end_idx = start_idx + label_horizon_days - 1
                if end_idx >= len(all_closes):
                    continue
                ret_next = float(all_closes[end_idx] / all_closes[start_idx] - 1)
                sign_next = "U" if ret_next > 0 else ("D" if ret_next < 0 else "F")
            else:
                raise ValueError(f"unknown label_mode={label_mode}")

            grid = candle_grid(
                cur["open"].values.astype(float),
                cur["high"].values.astype(float),
                cur["low"].values.astype(float),
                cur["close"].values.astype(float),
                cur["volume"].values.astype(float),
                cols, price_rows, vol_rows,
            )
            tokens = grid_to_tokens(grid)
            samples.append({
                "code": code, "name": name, "year_month": m,
                "n_days": len(cur), "ret_next": ret_next, "sign_next": sign_next,
                "grid_tokens": tokens,
            })
    return pd.DataFrame(samples)


def run_chart_variant(scenario: str, ohlcv: pd.DataFrame) -> pd.DataFrame:
    cfg = CHART_CONFIGS[scenario]
    print(f"[chart] cfg={cfg}", flush=True)
    t1 = time.time()
    samples = build_samples(ohlcv, cfg, label_mode="cal_month")
    print(f"[build] N={len(samples)} ({time.time()-t1:.1f}s)", flush=True)

    sdir = CACHE_S / scenario
    sdir.mkdir(parents=True, exist_ok=True)
    samples.drop(columns=["grid_tokens"]).to_parquet(sdir / "samples_meta.parquet",
                                                      index=False)

    t1 = time.time()
    X = tokens_to_onehot(samples["grid_tokens"].tolist(), len(TOKEN_VOCAB))
    print(f"[onehot] X={X.shape} ({time.time()-t1:.1f}s)", flush=True)
    t1 = time.time()
    pca_dim = min(PCA_DIM, X.shape[1], X.shape[0])
    pca = PCA(n_components=pca_dim, random_state=SEED)
    Xp = pca.fit_transform(X).astype(np.float32)
    print(f"[pca] X={Xp.shape} ev_sum={pca.explained_variance_ratio_.sum():.3f} "
          f"({time.time()-t1:.1f}s)", flush=True)
    np.save(sdir / "embeddings.npy", Xp)

    t1 = time.time()
    km = MiniBatchKMeans(n_clusters=K, n_init=3, random_state=SEED,
                          batch_size=1024, max_iter=100)
    labels = km.fit_predict(Xp)
    print(f"[kmeans] K={K} inertia={km.inertia_:.1f} ({time.time()-t1:.1f}s)",
          flush=True)
    cl = samples[["code", "name", "year_month", "n_days", "ret_next", "sign_next"]].copy()
    cl["cluster_id"] = labels
    cl.to_csv(sdir / "clusters.csv", index=False, encoding="utf-8-sig")
    return cl


def run_label_variant(scenario: str, ohlcv: pd.DataFrame) -> pd.DataFrame:
    if scenario == "label_5d":
        params = {"label_mode": "next_n_days", "label_horizon_days": 5}
    elif scenario == "label_20d":
        params = {"label_mode": "next_n_days", "label_horizon_days": 20}
    elif scenario == "label_3class":
        params = {"label_mode": "cal_month_3class", "neutral_pct": 0.005}
    else:
        raise ValueError(scenario)

    cfg = DEFAULT_CHART
    print(f"[label variant] params={params}", flush=True)
    t1 = time.time()
    samples = build_samples(ohlcv, cfg, **params)
    print(f"[build] N={len(samples)} ({time.time()-t1:.1f}s)", flush=True)

    sdir = CACHE_S / scenario
    sdir.mkdir(parents=True, exist_ok=True)

    # 임베딩/클러스터링: 기본 차트 사이즈와 동일하므로 기존 cache/clusters.csv를
    # (code, year_month) 기준으로 매칭. 기본 클러스터는 'cal_month' 라벨로 만든
    # 13971개 샘플과 호환됨. 새로 라벨이 정의되는 샘플 집합은 다를 수 있어 inner join.
    base_cl = pd.read_csv(CACHE / "clusters.csv",
                          dtype={"code": str, "year_month": str})
    base_cl = base_cl[["code", "year_month", "cluster_id"]]
    samples["code"] = samples["code"].astype(str)
    samples["year_month"] = samples["year_month"].astype(str)

    cl = samples.merge(base_cl, on=["code", "year_month"], how="inner")
    print(f"[merge] new label N={len(samples)} ∩ base cluster = {len(cl)}",
          flush=True)
    cl = cl[["code", "name", "year_month", "n_days", "ret_next", "sign_next",
             "cluster_id"]]
    cl.to_csv(sdir / "clusters.csv", index=False, encoding="utf-8-sig")
    return cl


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", required=True,
                    choices=["baseline",
                             "chart_small", "chart_large", "chart_wide",
                             "label_5d", "label_20d", "label_3class"])
    args = ap.parse_args()
    s = args.scenario
    print(f"[scenario] {s}", flush=True)

    if s == "baseline":
        # 기존 출력 그대로 복사
        src = OUT / "cluster_summary.csv"
        if not src.exists():
            print(f"FAILED: {src} 없음", flush=True)
            return 1
        df = pd.read_csv(src, encoding="utf-8-sig")
        # 기존 cluster_summary는 이미 베이스라인.
        out = OUT_S / "cluster_summary_baseline.csv"
        df.to_csv(out, index=False, encoding="utf-8-sig")
        # 베이스라인 메타
        cl = pd.read_csv(CACHE / "clusters.csv", dtype={"code": str, "year_month": str})
        n_total = len(cl)
        base_up = (cl["sign_next"] == "U").mean()
        base_mean = cl["ret_next"].mean()
        meta = OUT_S / f"meta_baseline.txt"
        meta.write_text(
            f"scenario=baseline\nn_total={n_total}\n"
            f"baseline_up_rate={base_up:.4f}\nbaseline_mean_ret={base_mean:.4f}\n"
            f"max_up_rate={df['up_rate'].max():.4f}\n"
            f"min_up_rate={df['up_rate'].min():.4f}\n",
            encoding="utf-8",
        )
        print(f"[baseline] N={n_total} up_rate={base_up:.4f} max_cluster_up={df['up_rate'].max():.4f}",
              flush=True)
        print("DONE", flush=True)
        return 0

    print("[load] cache/ohlcv.parquet", flush=True)
    ohlcv = pd.read_parquet(CACHE / "ohlcv.parquet")
    ohlcv["code"] = ohlcv["code"].astype(str)

    if s in CHART_CONFIGS:
        cl = run_chart_variant(s, ohlcv)
    else:
        cl = run_label_variant(s, ohlcv)

    n_total = len(cl)
    base_up = (cl["sign_next"] == "U").mean()
    base_mean = cl["ret_next"].mean()
    summary = cluster_summary(cl)
    summary.to_csv(OUT_S / f"cluster_summary_{s}.csv", index=False, encoding="utf-8-sig")
    meta = OUT_S / f"meta_{s}.txt"
    meta.write_text(
        f"scenario={s}\nn_total={n_total}\n"
        f"baseline_up_rate={base_up:.4f}\nbaseline_mean_ret={base_mean:.4f}\n"
        f"max_up_rate={summary['up_rate'].max():.4f}\n"
        f"min_up_rate={summary['up_rate'].min():.4f}\n",
        encoding="utf-8",
    )
    print(f"[result] {s} N={n_total} up={base_up:.4f} "
          f"max={summary['up_rate'].max():.4f} min={summary['up_rate'].min():.4f}",
          flush=True)
    print("DONE", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
