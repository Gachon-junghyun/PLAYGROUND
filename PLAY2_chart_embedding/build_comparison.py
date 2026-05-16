"""(시장 통제 4) comparison.csv 생성.

원시 라벨 (이전 후속 실험) vs 시장 효과 제거 후 / cross-sectional / 회귀 결과 통합.
B-1 임베딩 K=20 기준.

출력: output/market_neutral/comparison.csv
컬럼: analysis, label, baseline_stat, top_cluster_stat, n_sig_clusters, note
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
OUT = HERE / "output"


def main() -> int:
    rows = []

    # 원시 (B-1) baseline + significance — 이전 후속 실험 결과 재인용
    raw_clusters = pd.read_csv(CACHE / "emb_norm_series" / "clusters.csv",
                               dtype={"code": str, "year_month": str})
    n_raw = len(raw_clusters)
    base_up_raw = (raw_clusters["sign_next"] == "U").mean()
    base_mean_raw = raw_clusters["ret_next"].mean()
    sig_raw = pd.read_csv(OUT / "emb_norm_series" / "significance.csv")
    n_sig_t_raw = int(sig_raw["sig_t_bh_a05"].sum())
    n_sig_p_raw = int(sig_raw["sig_p_bh_a05"].sum())
    top_up_raw = sig_raw["up_rate"].max()
    rows.append({
        "analysis": "cluster (raw)", "label": "ret_next",
        "baseline_stat": f"up_rate={base_up_raw:.4f} mean={base_mean_raw:.4f}",
        "top_cluster_stat": f"up_rate={top_up_raw:.4f}",
        "n_sig_clusters_BH": f"prop:{n_sig_p_raw}/20, t:{n_sig_t_raw}/20",
        "note": "이전 후속 (B-1)",
    })

    # simple residual cluster
    sim_cl = pd.read_csv(CACHE / "emb_norm_series" / "clusters_simple.csv",
                         dtype={"code": str, "year_month": str})
    base_up_sim = (sim_cl["sign_next"] == "U").mean()
    base_mean_sim = sim_cl["ret_next"].mean()
    sig_sim = pd.read_csv(OUT / "market_neutral" / "significance_simple.csv")
    top_up_sim = sig_sim["up_rate"].max()
    rows.append({
        "analysis": "cluster (mkt_neutral)", "label": "ret_residual_simple",
        "baseline_stat": f"up_rate={base_up_sim:.4f} mean={base_mean_sim:.4f}",
        "top_cluster_stat": f"up_rate={top_up_sim:.4f}",
        "n_sig_clusters_BH": f"prop:{int(sig_sim['sig_p_bh_a05'].sum())}/20, t:{int(sig_sim['sig_t_bh_a05'].sum())}/20",
        "note": "ret_next - ret_market_next",
    })

    # CAPM residual cluster
    capm_cl = pd.read_csv(CACHE / "emb_norm_series" / "clusters_capm.csv",
                          dtype={"code": str, "year_month": str})
    base_up_capm = (capm_cl["sign_next"] == "U").mean()
    base_mean_capm = capm_cl["ret_next"].mean()
    sig_capm = pd.read_csv(OUT / "market_neutral" / "significance_capm.csv")
    top_up_capm = sig_capm["up_rate"].max()
    rows.append({
        "analysis": "cluster (mkt_neutral)", "label": "ret_residual_capm",
        "baseline_stat": f"up_rate={base_up_capm:.4f} mean={base_mean_capm:.4f}",
        "top_cluster_stat": f"up_rate={top_up_capm:.4f}",
        "n_sig_clusters_BH": f"prop:{int(sig_capm['sig_p_bh_a05'].sum())}/20, t:{int(sig_capm['sig_t_bh_a05'].sum())}/20",
        "note": "ret_next - beta_60d * ret_market_next",
    })

    # cross-sectional
    cs = pd.read_csv(OUT / "cross_sectional" / "cluster_cs_summary.csv")
    cs_top = cs["mean_cs_residual"].max()
    n_sig_bh_cs = int(cs["sig_bh_a05"].sum())
    n_sig_boot_cs = int(cs["sig_boot_a05"].sum())
    rows.append({
        "analysis": "cross_sectional", "label": "cs_residual (mean)",
        "baseline_stat": "0 (정의상)",
        "top_cluster_stat": f"mean_cs_residual={cs_top:.5f}",
        "n_sig_clusters_BH": f"BH:{n_sig_bh_cs}/20, boot:{n_sig_boot_cs}/20",
        "note": "min_n=5 시점 필터 (37% 제외)",
    })

    # regression
    reg = pd.read_csv(OUT / "regression" / "results.csv")
    for label_name, sub in reg.groupby("label_type"):
        idx = sub["R2"].idxmax()
        best = sub.loc[idx]
        rows.append({
            "analysis": "regression", "label": label_name,
            "baseline_stat": "R²=0 (mean predictor)",
            "top_cluster_stat": (
                f"best={best['model']} R²={best['R2']:.4f} "
                f"sign_acc={best['sign_accuracy']:.3f} q_spread={best['top_minus_bottom_quintile']:.4f}"
            ),
            "n_sig_clusters_BH": "—",
            "note": "time-series split 80/20",
        })

    out = pd.DataFrame(rows)
    out_path = OUT / "market_neutral" / "comparison.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"[save] {out_path}", flush=True)
    print(out.to_string(index=False), flush=True)
    print("DONE", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
