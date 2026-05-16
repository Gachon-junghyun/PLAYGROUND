"""(1) 시점별 클러스터 분포 시계열 + KOSPI 월간 수익률 join.

입력:
  - PLAY2_chart_embedding/cache/samples.parquet
  - PLAY2_chart_embedding/cache/full/clusters_K20_full.npy
  - PLAY2_chart_embedding/cache/market/kospi.parquet
출력:
  - PLAY3_market_timing/cache/cluster_dist_by_month.parquet
  - PLAY3_market_timing/cache/timing_panel.parquet
  - PLAY3_market_timing/cache/cluster_ranking.csv  (cluster_id 별 평균 ret_next)
"""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
PLAY_ROOT = ROOT.parent  # PLAYGROUND
PLAY2 = PLAY_ROOT / "PLAY2_chart_embedding"
CACHE = ROOT / "cache"
CACHE.mkdir(parents=True, exist_ok=True)

K = 20


def main():
    samples = pd.read_parquet(PLAY2 / "cache" / "samples.parquet")
    clusters = np.load(PLAY2 / "cache" / "full" / "clusters_K20_full.npy")
    assert len(samples) == len(clusters), f"len mismatch: {len(samples)} vs {len(clusters)}"
    samples = samples.copy()
    samples["cluster_id"] = clusters

    # --- 클러스터별 평균 다음달 수익률 → top1/bot1 매핑 ---
    cluster_ret = (
        samples.groupby("cluster_id")["ret_next"]
        .agg(["mean", "count"])
        .reset_index()
        .sort_values("mean", ascending=False)
    )
    top1_id = int(cluster_ret.iloc[0]["cluster_id"])
    bot1_id = int(cluster_ret.iloc[-1]["cluster_id"])
    cluster_ret.to_csv(CACHE / "cluster_ranking.csv", index=False)
    print(f"[panel] top1 cluster={top1_id} mean_ret={cluster_ret.iloc[0]['mean']:.4f}, "
          f"bot1 cluster={bot1_id} mean_ret={cluster_ret.iloc[-1]['mean']:.4f}")

    # --- 시점별 cluster 분포 ---
    grp = samples.groupby(["year_month", "cluster_id"]).size().unstack(fill_value=0)
    # ensure all clusters 0..K-1 present
    for k in range(K):
        if k not in grp.columns:
            grp[k] = 0
    grp = grp.reindex(sorted(grp.columns), axis=1)
    grp["n_stocks"] = grp.sum(axis=1)
    pct = grp[list(range(K))].div(grp["n_stocks"], axis=0)
    pct.columns = [f"cluster_{c}_pct" for c in pct.columns]
    pct["n_stocks"] = grp["n_stocks"]
    pct["top1_pct"] = pct[f"cluster_{top1_id}_pct"]
    pct["bot1_pct"] = pct[f"cluster_{bot1_id}_pct"]
    pct = pct.reset_index().sort_values("year_month").reset_index(drop=True)
    pct.to_parquet(CACHE / "cluster_dist_by_month.parquet", index=False)
    print(f"[panel] cluster_dist_by_month: {pct.shape} months={pct['year_month'].nunique()}")

    # --- KOSPI 월간 수익률 ---
    kospi = pd.read_parquet(PLAY2 / "cache" / "market" / "kospi.parquet")
    kospi["date"] = pd.to_datetime(kospi["date"])
    kospi["year_month"] = kospi["date"].dt.strftime("%Y-%m")
    # 월 마지막 영업일 종가
    monthly = kospi.groupby("year_month").agg(close_last=("close", "last"),
                                              date_last=("date", "last")).reset_index()
    monthly = monthly.sort_values("year_month").reset_index(drop=True)
    monthly["kospi_ret"] = monthly["close_last"].pct_change()
    monthly["kospi_ret_next"] = monthly["kospi_ret"].shift(-1)
    monthly["kospi_ret_lag1"] = monthly["kospi_ret"].shift(1)
    monthly["kospi_ret_lag3"] = monthly["close_last"].pct_change(3).shift(1)
    monthly = monthly[["year_month", "close_last", "kospi_ret",
                       "kospi_ret_next", "kospi_ret_lag1", "kospi_ret_lag3"]]

    panel = pct.merge(monthly, on="year_month", how="left")
    panel.to_parquet(CACHE / "timing_panel.parquet", index=False)
    print(f"[panel] timing_panel: {panel.shape}")
    print(panel[["year_month", "n_stocks", "top1_pct", "bot1_pct",
                 "kospi_ret", "kospi_ret_next"]].head(3))
    print(panel[["year_month", "n_stocks", "top1_pct", "bot1_pct",
                 "kospi_ret", "kospi_ret_next"]].tail(3))

    # 메타 출력
    meta = {"top1_cluster_id": top1_id, "bot1_cluster_id": bot1_id, "K": K}
    pd.Series(meta).to_csv(CACHE / "panel_meta.csv", header=False)


if __name__ == "__main__":
    main()
