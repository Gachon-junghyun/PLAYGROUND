"""(후속 1) 표본 독립성 보정 부트스트랩.

기존 K=20 cluster_id 그대로 재사용 (cache/clusters.csv).
같은 종목의 다른 달이 여러 번 등장하는 점이 t-test의 표본독립성 가정을 깨므로,
부트스트랩으로 경험적 분포를 추정한다.

method:
  per_ticker — 매 반복마다 종목당 1샘플만 무작위 추출 (B=1000)
  block      — 종목별 시계열을 길이 L 블록으로 잘라 복원추출 (B=500), --block_L 필수

각 반복:
  1) 리샘플된 (cluster_id, ret_next, sign_next) 행렬 구성
  2) 베이스라인 up_rate / mean_ret 계산
  3) 클러스터별 up_rate, mean_ret, diff_baseline 저장

집계:
  cluster_id, n_avg, up_rate_mean, up_rate_ci_low/high (2.5%/97.5%),
  mean_ret_mean, mean_ret_ci_low/high,
  empirical_p_diff_baseline (= 2 * min(P(diff<=0), P(diff>=0)) 양측)

CLI:
  python -u bootstrap_independence.py --method per_ticker --B 1000
  python -u bootstrap_independence.py --method block --block_L 3 --B 500
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


def empirical_p_two_sided(diffs: np.ndarray) -> float:
    """diffs 의 0 대비 양측 경험적 p-value."""
    n = len(diffs)
    if n == 0:
        return float("nan")
    p_neg = float(np.mean(diffs <= 0))
    p_pos = float(np.mean(diffs >= 0))
    return float(min(1.0, 2.0 * min(p_neg, p_pos)))


def aggregate_per_iter(cluster_ids: np.ndarray,
                       up_arr: np.ndarray, ret_arr: np.ndarray,
                       K: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, float, float]:
    """주어진 단일 반복의 (cluster_ids, up, ret) 에서 클러스터별 통계 + 베이스라인."""
    base_up = float(up_arr.mean())
    base_mean = float(ret_arr.mean())
    counts = np.bincount(cluster_ids, minlength=K).astype(float)
    sum_up = np.bincount(cluster_ids, weights=up_arr, minlength=K)
    sum_ret = np.bincount(cluster_ids, weights=ret_arr, minlength=K)
    safe = np.where(counts == 0, np.nan, counts)
    up_rate = sum_up / safe
    mean_ret = sum_ret / safe
    return counts, up_rate, mean_ret, base_up, base_mean


def per_ticker_bootstrap(df: pd.DataFrame, K: int, B: int, seed: int = 42):
    """종목당 1샘플. 종목별 인덱스 그룹을 미리 만들고 매 반복 1개씩 sample."""
    rng = np.random.default_rng(seed)
    cl_arr = df["cluster_id"].values.astype(np.int64)
    up_arr = (df["sign_next"].values == "U").astype(np.float64)
    ret_arr = df["ret_next"].values.astype(np.float64)

    code_to_idx: dict[str, np.ndarray] = {
        c: g.index.values
        for c, g in df.groupby("code", sort=False)
    }
    codes = sorted(code_to_idx.keys())
    M = len(codes)

    up_rates = np.empty((B, K), dtype=np.float64)
    mean_rets = np.empty((B, K), dtype=np.float64)
    counts_all = np.empty((B, K), dtype=np.float64)
    base_ups = np.empty(B, dtype=np.float64)
    base_means = np.empty(B, dtype=np.float64)

    t0 = time.time()
    for b in range(B):
        sel = np.empty(M, dtype=np.int64)
        for i, c in enumerate(codes):
            arr = code_to_idx[c]
            sel[i] = arr[rng.integers(0, len(arr))]
        cl_b = cl_arr[sel]
        up_b = up_arr[sel]
        ret_b = ret_arr[sel]
        counts, ur, mr, bu, bm = aggregate_per_iter(cl_b, up_b, ret_b, K)
        up_rates[b] = ur
        mean_rets[b] = mr
        counts_all[b] = counts
        base_ups[b] = bu
        base_means[b] = bm
        if (b + 1) % 100 == 0:
            print(f"[per_ticker] {b+1}/{B} elapsed={time.time()-t0:.1f}s", flush=True)

    return up_rates, mean_rets, counts_all, base_ups, base_means


def block_bootstrap(df: pd.DataFrame, K: int, B: int, L: int, seed: int = 42):
    """종목별 시계열을 길이 L 블록(overlapping moving block)으로 자르고 복원추출.

    각 종목의 시계열 길이 T 가 L 이상일 때만 부트스트랩에 포함. T<L 인 종목은 그대로 사용.
    """
    rng = np.random.default_rng(seed)
    cl_arr = df["cluster_id"].values.astype(np.int64)
    up_arr = (df["sign_next"].values == "U").astype(np.float64)
    ret_arr = df["ret_next"].values.astype(np.float64)

    # 종목별 시간순 인덱스
    df2 = df.sort_values(["code", "year_month"]).reset_index()
    df2 = df2.rename(columns={"index": "orig_idx"})
    code_groups: list[np.ndarray] = []
    for _, g in df2.groupby("code", sort=False):
        code_groups.append(g["orig_idx"].values.astype(np.int64))
    n_codes = len(code_groups)

    up_rates = np.empty((B, K), dtype=np.float64)
    mean_rets = np.empty((B, K), dtype=np.float64)
    counts_all = np.empty((B, K), dtype=np.float64)
    base_ups = np.empty(B, dtype=np.float64)
    base_means = np.empty(B, dtype=np.float64)

    t0 = time.time()
    for b in range(B):
        chunks: list[np.ndarray] = []
        for arr in code_groups:
            T = len(arr)
            if T < L:
                chunks.append(arr)
                continue
            n_blocks = T - L + 1
            n_pick = (T + L - 1) // L
            starts = rng.integers(0, n_blocks, size=n_pick)
            # gather blocks (vectorized)
            block_idx = (starts[:, None] + np.arange(L)[None, :]).ravel()
            re = arr[block_idx][:T]
            chunks.append(re)
        sel = np.concatenate(chunks)
        cl_b = cl_arr[sel]
        up_b = up_arr[sel]
        ret_b = ret_arr[sel]
        counts, ur, mr, bu, bm = aggregate_per_iter(cl_b, up_b, ret_b, K)
        up_rates[b] = ur
        mean_rets[b] = mr
        counts_all[b] = counts
        base_ups[b] = bu
        base_means[b] = bm
        if (b + 1) % 50 == 0:
            print(f"[block L={L}] {b+1}/{B} elapsed={time.time()-t0:.1f}s", flush=True)

    return up_rates, mean_rets, counts_all, base_ups, base_means


def summarize(up_rates: np.ndarray, mean_rets: np.ndarray,
              counts_all: np.ndarray, base_ups: np.ndarray,
              base_means: np.ndarray, K: int) -> pd.DataFrame:
    rows = []
    for cid in range(K):
        ur = up_rates[:, cid]
        mr = mean_rets[:, cid]
        cn = counts_all[:, cid]
        # NaN 안전 (count=0 인 반복은 NaN)
        ur_valid = ur[~np.isnan(ur)]
        mr_valid = mr[~np.isnan(mr)]

        if len(ur_valid) > 0:
            ur_mean = float(np.mean(ur_valid))
            ur_lo, ur_hi = np.quantile(ur_valid, [0.025, 0.975])
        else:
            ur_mean = ur_lo = ur_hi = float("nan")

        if len(mr_valid) > 0:
            mr_mean = float(np.mean(mr_valid))
            mr_lo, mr_hi = np.quantile(mr_valid, [0.025, 0.975])
        else:
            mr_mean = mr_lo = mr_hi = float("nan")

        # diffs vs each-iteration baseline
        diff_up = ur - base_ups
        diff_mr = mr - base_means
        # NaN 제거
        diff_up = diff_up[~np.isnan(diff_up)]
        diff_mr = diff_mr[~np.isnan(diff_mr)]
        p_up = empirical_p_two_sided(diff_up)
        p_mr = empirical_p_two_sided(diff_mr)

        rows.append({
            "cluster_id": cid,
            "n_avg": round(float(np.mean(cn)), 1),
            "up_rate_mean": round(ur_mean, 4),
            "up_rate_ci_low": round(float(ur_lo), 4),
            "up_rate_ci_high": round(float(ur_hi), 4),
            "mean_ret_mean": round(mr_mean, 4),
            "mean_ret_ci_low": round(float(mr_lo), 4),
            "mean_ret_ci_high": round(float(mr_hi), 4),
            "empirical_p_up_rate": round(p_up, 4),
            "empirical_p_mean_ret": round(p_mr, 4),
            "sig_up_a05": bool(p_up < 0.05) if not np.isnan(p_up) else False,
            "sig_mr_a05": bool(p_mr < 0.05) if not np.isnan(p_mr) else False,
        })
    out = pd.DataFrame(rows).sort_values("up_rate_mean", ascending=False)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--clusters", default=str(CACHE / "clusters.csv"))
    ap.add_argument("--method", choices=["per_ticker", "block"], required=True)
    ap.add_argument("--B", type=int, default=1000)
    ap.add_argument("--block_L", type=int, default=0)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    df = pd.read_csv(args.clusters, dtype={"code": str, "year_month": str})
    df = df.reset_index(drop=True)
    K = int(df["cluster_id"].max()) + 1
    N = len(df)
    print(f"[start] N={N} K={K} method={args.method}", flush=True)

    t0 = time.time()
    if args.method == "per_ticker":
        ur, mr, cn, bu, bm = per_ticker_bootstrap(df, K, args.B, args.seed)
        out_path = Path(args.out or (OUT / "bootstrap" / f"per_ticker_K{K}.csv"))
    else:
        if args.block_L <= 0:
            print("FAILED: --block_L 필수", flush=True)
            return 1
        ur, mr, cn, bu, bm = block_bootstrap(df, K, args.B, args.block_L, args.seed)
        out_path = Path(args.out or (OUT / "bootstrap" / f"block_L{args.block_L}_K{K}.csv"))
    print(f"[bootstrap done] elapsed={time.time()-t0:.1f}s", flush=True)

    summary = summarize(ur, mr, cn, bu, bm, K)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"[save] {out_path}", flush=True)
    n_sig_up = int(summary["sig_up_a05"].sum())
    n_sig_mr = int(summary["sig_mr_a05"].sum())
    print(f"[result] α=0.05 유의 클러스터: up_rate {n_sig_up}/{K}, mean_ret {n_sig_mr}/{K}",
          flush=True)
    print("DONE", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
