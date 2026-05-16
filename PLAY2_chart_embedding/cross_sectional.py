"""(시장 통제 2) Cross-sectional 분석.

각 (year_month) 시점에 대해:
  - 그 달의 모든 샘플에 대한 시점 평균 ret_next 를 계산.
  - 각 클러스터의 그 달 평균 ret - 시점 평균 = cs_residual.
  - 클러스터에 종목 < min_n (=5) 인 시점은 분산 불안정하니 제외.

집계: cluster_id 별로 cs_residual 시계열 → 평균/표준편차/t-test (vs 0) + BH + block bootstrap (시점 단위).

원시 ret_next 라벨로 수행 (시점 평균 차감 자체가 시장 효과를 제거함).
입력: cache/emb_norm_series/clusters.csv (B-1 K=20)
출력: output/cross_sectional/cluster_cs_summary.csv
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
OUT = HERE / "output" / "cross_sectional"

MIN_N = 5
BLOCK_L = 6
BOOT_B = 500
SEED = 42


def bh_adjust(pvals: np.ndarray) -> np.ndarray:
    pvals = np.asarray(pvals, dtype=float)
    n = len(pvals)
    order = np.argsort(pvals)
    ranked = pvals[order]
    bh_sorted = np.minimum.accumulate(
        (ranked * n / (np.arange(n) + 1))[::-1]
    )[::-1]
    bh_sorted = np.minimum(bh_sorted, 1.0)
    out = np.empty_like(bh_sorted)
    out[order] = bh_sorted
    return out


def main() -> int:
    df = pd.read_csv(CACHE / "emb_norm_series" / "clusters.csv",
                     dtype={"code": str, "year_month": str})
    K = int(df["cluster_id"].max()) + 1
    print(f"[start] N={len(df)} K={K}", flush=True)

    # 시점 평균
    period_mean = df.groupby("year_month")["ret_next"].mean().rename("period_mean")
    df = df.merge(period_mean, on="year_month", how="left")
    df["resid_from_period"] = df["ret_next"] - df["period_mean"]

    # 클러스터 × 시점 mean
    grp = df.groupby(["cluster_id", "year_month"]).agg(
        n=("ret_next", "size"),
        cluster_mean=("ret_next", "mean"),
        period_mean=("period_mean", "first"),
    ).reset_index()
    grp["cs_residual"] = grp["cluster_mean"] - grp["period_mean"]

    # 시점 < MIN_N 필터
    n_total = len(grp)
    grp_filt = grp[grp["n"] >= MIN_N].copy()
    n_excluded = n_total - len(grp_filt)
    print(f"[filter] n_periods (cluster×month) raw={n_total} kept={len(grp_filt)} "
          f"excluded({MIN_N})={n_excluded} excluded_pct={n_excluded/n_total*100:.1f}%",
          flush=True)

    # block bootstrap: 시점 단위로 cs_residual 의 평균을 부트스트랩.
    rng = np.random.default_rng(SEED)
    rows = []
    pvals_t = []

    # 시점 정렬 시퀀스
    months_all = sorted(grp_filt["year_month"].unique())
    month_idx = {m: i for i, m in enumerate(months_all)}

    for cid in range(K):
        sub = grp_filt[grp_filt["cluster_id"] == cid].copy()
        if len(sub) == 0:
            rows.append({
                "cluster_id": cid, "n_periods": 0, "mean_cs_residual": np.nan,
                "std_cs_residual": np.nan, "t_stat": np.nan, "p_value": np.nan,
                "p_bootstrap": np.nan,
            })
            pvals_t.append(np.nan)
            continue

        sub = sub.sort_values("year_month").reset_index(drop=True)
        x = sub["cs_residual"].values.astype(np.float64)
        n = len(x)
        mean_x = float(np.mean(x))
        std_x = float(np.std(x, ddof=1)) if n > 1 else float("nan")

        if n >= 2:
            t_res = stats.ttest_1samp(x, 0.0)
            t_stat = float(t_res.statistic)
            p_t = float(t_res.pvalue)
        else:
            t_stat = float("nan")
            p_t = float("nan")

        # block bootstrap (시점 단위)
        if n >= BLOCK_L and n >= 5:
            boot_means = np.empty(BOOT_B, dtype=np.float64)
            n_blocks = n - BLOCK_L + 1
            n_pick = (n + BLOCK_L - 1) // BLOCK_L
            for b in range(BOOT_B):
                starts = rng.integers(0, n_blocks, size=n_pick)
                idx = (starts[:, None] + np.arange(BLOCK_L)[None, :]).ravel()[:n]
                boot_means[b] = float(np.mean(x[idx]))
            # 양측 p (vs 0)
            diffs = boot_means - 0.0
            p_neg = float(np.mean(diffs <= 0))
            p_pos = float(np.mean(diffs >= 0))
            p_boot = float(min(1.0, 2.0 * min(p_neg, p_pos)))
        else:
            p_boot = float("nan")

        rows.append({
            "cluster_id": cid,
            "n_periods": int(n),
            "mean_cs_residual": round(mean_x, 5),
            "std_cs_residual": round(std_x, 5) if not np.isnan(std_x) else np.nan,
            "t_stat": round(t_stat, 3) if not np.isnan(t_stat) else np.nan,
            "p_value": p_t,
            "p_bootstrap": p_boot,
        })
        pvals_t.append(p_t)

    out = pd.DataFrame(rows)
    pvals_arr = np.array(pvals_t, dtype=float)
    valid = ~np.isnan(pvals_arr)
    p_bh = np.full_like(pvals_arr, np.nan)
    if valid.any():
        p_bh[valid] = bh_adjust(pvals_arr[valid])
    out["p_bh"] = p_bh
    out["sig_bh_a05"] = out["p_bh"] < 0.05
    out["sig_boot_a05"] = out["p_bootstrap"] < 0.05
    out["sig_both"] = out["sig_bh_a05"] & out["sig_boot_a05"]

    # 정렬: mean_cs_residual 내림차순
    out = out.sort_values("mean_cs_residual", ascending=False)

    # 자릿수 정리
    for c in ["p_value", "p_bootstrap", "p_bh"]:
        out[c] = out[c].apply(lambda v: f"{v:.4g}" if pd.notna(v) else "nan")

    OUT.mkdir(parents=True, exist_ok=True)
    out_path = OUT / "cluster_cs_summary.csv"
    out.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"[save] {out_path}", flush=True)
    n_bh = int(out["sig_bh_a05"].sum())
    n_boot = int(out["sig_boot_a05"].sum())
    n_both = int(out["sig_both"].sum())
    print(f"[result] BH<0.05: {n_bh}/{K}, bootstrap<0.05: {n_boot}/{K}, both: {n_both}/{K}",
          flush=True)
    print("DONE", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
