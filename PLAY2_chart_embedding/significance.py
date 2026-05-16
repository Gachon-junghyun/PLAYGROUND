"""(개선 2) 클러스터별 통계적 유의성 검정.

각 클러스터 vs 나머지 전체:
  - 다음달 수익률(ret_next): Welch's two-sample t-test (scipy.stats.ttest_ind, equal_var=False)
  - 상승 비율(up_rate): two-proportion z-test (수동 구현)

다중검정 보정:
  - Bonferroni: p_bonf = min(1, p * K)
  - BH (Benjamini-Hochberg, FDR=0.05): 정렬 기반.

α=0.05 기준 유의여부도 함께 기록 (sig_ttest_bh, sig_prop_bh).

사용:
  python -u significance.py --clusters cache/clusters.csv --out output/significance_K20.csv
  # K sweep:
  python -u significance.py --clusters cache/sweep/clusters_K10.csv --out output/sweep/significance_K10.csv
  ...

generic 하므로 K나 시나리오에 무관하게 사용 가능.
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

HERE = Path(__file__).resolve().parent


def two_proportion_z(x1: int, n1: int, x2: int, n2: int) -> float:
    """두 비율 차이의 z-test 양측 p-value. n1+n2 둘 다 0보다 커야."""
    if n1 == 0 or n2 == 0:
        return float("nan")
    p1 = x1 / n1
    p2 = x2 / n2
    p_pool = (x1 + x2) / (n1 + n2)
    se = math.sqrt(p_pool * (1 - p_pool) * (1 / n1 + 1 / n2))
    if se == 0:
        # 모두 같은 값이면 p=1 (차이 없음).
        return 1.0
    z = (p1 - p2) / se
    # 양측
    p = 2 * (1 - stats.norm.cdf(abs(z)))
    return float(p)


def bh_adjust(pvals: np.ndarray) -> np.ndarray:
    """Benjamini-Hochberg FDR 보정 p-value (각 가설별로 보정된 p)."""
    pvals = np.asarray(pvals, dtype=float)
    n = len(pvals)
    order = np.argsort(pvals)
    ranked = pvals[order]
    # 보정값: min(1, p_i * n / rank_i)
    bh_sorted = np.minimum.accumulate(
        (ranked * n / (np.arange(n) + 1))[::-1]
    )[::-1]
    bh_sorted = np.minimum(bh_sorted, 1.0)
    # 원래 순서로 복원
    out = np.empty_like(bh_sorted)
    out[order] = bh_sorted
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--clusters", required=True,
                    help="clusters.csv 경로 (cluster_id, ret_next, sign_next 필수)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--alpha", type=float, default=0.05)
    args = ap.parse_args()

    df = pd.read_csv(args.clusters, dtype={"code": str, "year_month": str})
    if "cluster_id" not in df.columns:
        print(f"FAILED: cluster_id 컬럼 없음", flush=True)
        return 1

    n_total = len(df)
    base_up = (df["sign_next"] == "U").mean()
    base_mean = df["ret_next"].mean()
    print(f"[start] N={n_total} baseline up_rate={base_up:.4f} mean_ret={base_mean:.4f}",
          flush=True)

    cluster_ids = sorted(df["cluster_id"].unique())
    K = len(cluster_ids)
    print(f"[clusters] K={K}", flush=True)

    rows = []
    for cid in cluster_ids:
        sub = df[df["cluster_id"] == cid]
        rest = df[df["cluster_id"] != cid]
        n_c = len(sub)
        n_r = len(rest)
        up_c = int((sub["sign_next"] == "U").sum())
        up_r = int((rest["sign_next"] == "U").sum())
        up_rate_c = up_c / n_c if n_c else float("nan")
        mean_ret_c = sub["ret_next"].mean()

        # Welch t-test on ret_next
        if n_c >= 2 and n_r >= 2:
            t_res = stats.ttest_ind(
                sub["ret_next"].values, rest["ret_next"].values,
                equal_var=False, nan_policy="omit",
            )
            p_t = float(t_res.pvalue)
        else:
            p_t = float("nan")

        # Two-proportion z-test on up_rate
        p_p = two_proportion_z(up_c, n_c, up_r, n_r)

        rows.append({
            "cluster_id": int(cid),
            "n": n_c,
            "up_rate": round(up_rate_c, 4),
            "mean_ret": round(mean_ret_c, 4),
            "diff_up_pp": round((up_rate_c - base_up) * 100, 2),
            "diff_mean_ret_pp": round((mean_ret_c - base_mean) * 100, 2),
            "p_value_ttest": p_t,
            "p_value_proportion": p_p,
        })

    out = pd.DataFrame(rows)

    # Bonferroni / BH 보정
    p_t_arr = out["p_value_ttest"].values
    p_p_arr = out["p_value_proportion"].values
    out["p_t_bonf"] = np.minimum(p_t_arr * K, 1.0)
    out["p_p_bonf"] = np.minimum(p_p_arr * K, 1.0)
    # NaN 안전: NaN은 그대로 둠 (n<2 같은 경우)
    valid_t = ~np.isnan(p_t_arr)
    valid_p = ~np.isnan(p_p_arr)
    p_t_bh = np.full_like(p_t_arr, np.nan)
    p_p_bh = np.full_like(p_p_arr, np.nan)
    if valid_t.any():
        p_t_bh[valid_t] = bh_adjust(p_t_arr[valid_t])
    if valid_p.any():
        p_p_bh[valid_p] = bh_adjust(p_p_arr[valid_p])
    out["p_t_bh"] = p_t_bh
    out["p_p_bh"] = p_p_bh

    out["sig_t_bh_a05"] = out["p_t_bh"] < args.alpha
    out["sig_p_bh_a05"] = out["p_p_bh"] < args.alpha
    out["sig_t_bonf_a05"] = out["p_t_bonf"] < args.alpha
    out["sig_p_bonf_a05"] = out["p_p_bonf"] < args.alpha

    # 정렬 — up_rate 내림차순
    out = out.sort_values("up_rate", ascending=False)

    # p-value 자릿수 정리 (CSV 가독성)
    for c in ["p_value_ttest", "p_value_proportion",
              "p_t_bonf", "p_p_bonf", "p_t_bh", "p_p_bh"]:
        out[c] = out[c].apply(lambda x: f"{x:.4g}" if pd.notna(x) else "nan")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"[save] {out_path}", flush=True)

    n_sig_t_bh = int(out["sig_t_bh_a05"].sum())
    n_sig_p_bh = int(out["sig_p_bh_a05"].sum())
    n_sig_t_bonf = int(out["sig_t_bonf_a05"].sum())
    n_sig_p_bonf = int(out["sig_p_bonf_a05"].sum())
    print(
        f"[result] α=0.05 기준 유의 클러스터 수: "
        f"t-test BH={n_sig_t_bh}/{K}, prop BH={n_sig_p_bh}/{K}, "
        f"t-test Bonf={n_sig_t_bonf}/{K}, prop Bonf={n_sig_p_bonf}/{K}",
        flush=True,
    )
    print("DONE", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
