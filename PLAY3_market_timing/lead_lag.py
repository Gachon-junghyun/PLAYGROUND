"""(2) Lead-Lag cross-correlation.

각 cluster_pct 시계열과 KOSPI 월간 수익률의 lag 상관 (lag = -3 ~ +3).

- lag = -k: cluster_pct가 k개월 먼저 움직임 → KOSPI 수익률을 lead (예측력 가능)
- lag =  0: 동시기 상관 (예측 불가)
- lag = +k: KOSPI가 먼저, cluster_pct가 따라옴 (lag 신호)

수식: corr(cluster_pct[t], kospi_ret[t + lag])  (음의 lag일수록 cluster가 미래 KOSPI를 예측)

입력: cache/timing_panel.parquet
출력: output/lead_lag_correlation.csv
"""
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import pearsonr

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / "cache"
OUT = ROOT / "output"
OUT.mkdir(parents=True, exist_ok=True)

K = 20
LAGS = [-3, -2, -1, 0, 1, 2, 3]


def lagged_corr(x: pd.Series, y: pd.Series, lag: int):
    """corr(x[t], y[t+lag]). lag>0 이면 y를 미래로 lag만큼 끌어당김 (=y를 -lag만큼 shift)."""
    if lag >= 0:
        x_a = x.iloc[: len(x) - lag if lag > 0 else len(x)].reset_index(drop=True)
        y_a = y.iloc[lag:].reset_index(drop=True)
    else:
        x_a = x.iloc[-lag:].reset_index(drop=True)
        y_a = y.iloc[: len(y) + lag].reset_index(drop=True)
    df = pd.DataFrame({"x": x_a, "y": y_a}).dropna()
    if len(df) < 5 or df["x"].std() == 0 or df["y"].std() == 0:
        return np.nan, np.nan, len(df)
    r, p = pearsonr(df["x"], df["y"])
    return r, p, len(df)


def main():
    panel = pd.read_parquet(CACHE / "timing_panel.parquet").sort_values("year_month").reset_index(drop=True)
    meta = pd.read_csv(CACHE / "panel_meta.csv", header=None, index_col=0).iloc[:, 0]
    top1_id = int(meta["top1_cluster_id"])
    bot1_id = int(meta["bot1_cluster_id"])

    rows = []
    cluster_keys = [f"cluster_{c}_pct" for c in range(K)] + ["top1_pct", "bot1_pct"]
    for col in cluster_keys:
        x = panel[col]
        y = panel["kospi_ret"]
        for lag in LAGS:
            r, p, n = lagged_corr(x, y, lag)
            rows.append(dict(cluster=col, lag=lag, pearson_r=r, p_value=p, n=n))

    df = pd.DataFrame(rows)
    df.to_csv(OUT / "lead_lag_correlation.csv", index=False)
    print(f"[leadlag] saved: {OUT / 'lead_lag_correlation.csv'}, rows={len(df)}")

    # 강한 시그널 요약: top1, bot1, 그리고 |r|이 가장 큰 클러스터 lag
    print("\n=== Top1 / Bot1 cluster lag profile ===")
    for col in ["top1_pct", "bot1_pct"]:
        sub = df[df["cluster"] == col].sort_values("lag")
        print(f"\n{col} (top1={top1_id}, bot1={bot1_id})")
        print(sub[["lag", "pearson_r", "p_value", "n"]].to_string(index=False))

    # 가장 강한 (|r| 큰) cluster x lag 조합
    df_full = df[df["cluster"].str.startswith("cluster_")].copy()
    df_full["abs_r"] = df_full["pearson_r"].abs()
    top10 = df_full.sort_values("abs_r", ascending=False).head(10)
    print("\n=== |r| top10 (cluster x lag) ===")
    print(top10[["cluster", "lag", "pearson_r", "p_value", "n"]].to_string(index=False))

    # lag별 |r| 평균 — 신호 lag 분포 요약
    lag_summary = df_full.groupby("lag")["abs_r"].agg(["mean", "median", "max"]).reset_index()
    print("\n=== |r| distribution by lag (across all 20 clusters) ===")
    print(lag_summary.to_string(index=False))
    lag_summary.to_csv(OUT / "lead_lag_lag_summary.csv", index=False)


if __name__ == "__main__":
    main()
