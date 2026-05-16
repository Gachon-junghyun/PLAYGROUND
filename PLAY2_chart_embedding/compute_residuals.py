"""(시장 통제) simple/CAPM 잔차 라벨 생성.

기준 임베딩: B-1 norm_series clusters (cache/emb_norm_series/clusters.csv).
재클러스터링 안 함. 라벨만 교체.

simple : ret_residual = ret_next - ret_market_next
CAPM   : ret_residual = ret_next - beta * ret_market_next
         beta = 종목 daily ret vs market daily ret, 60거래일 rolling, 윈도우 끝 = year_month 마지막 거래일 (라벨 이전).

출력:
  cache/market/labels_residual.csv  — code, year_month, ret_next, ret_market_next, beta_60d, ret_residual_simple, ret_residual_capm
  cache/emb_norm_series/clusters_simple.csv  — 기존 clusters.csv 의 ret_next/sign_next 를 simple 잔차로 교체
  cache/emb_norm_series/clusters_capm.csv    — capm 잔차 버전
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"


def main() -> int:
    samples = pd.read_parquet(CACHE / "samples.parquet")
    ohlcv = pd.read_parquet(CACHE / "ohlcv.parquet")
    market = pd.read_parquet(CACHE / "market" / "kospi.parquet")
    clusters_b1 = pd.read_csv(CACHE / "emb_norm_series" / "clusters.csv",
                              dtype={"code": str, "year_month": str})

    # 시장 일봉 정렬, ret_daily 채움
    market = market.sort_values("date").reset_index(drop=True)
    market["ret_daily"] = market["close"].pct_change()
    market["year_month"] = market["date"].dt.to_period("M").astype(str)

    # (year_month → label_month) 다음달 수익률
    # ret_market_next = (label_month 마지막 close) / (label_month 첫 close) - 1
    mkt_grp = market.groupby("year_month")
    mkt_month = mkt_grp.agg(first_close=("close", "first"),
                             last_close=("close", "last"),
                             n=("close", "size")).reset_index()
    mkt_month["ret_month"] = mkt_month["last_close"] / mkt_month["first_close"] - 1

    # year_month → ret_next: shift 한 달
    # year_month is 'YYYY-MM'. period 로 변환 후 +1 month.
    mkt_month["period"] = pd.PeriodIndex(mkt_month["year_month"], freq="M")
    mkt_month = mkt_month.sort_values("period").reset_index(drop=True)
    # 매핑: chart_month → label_month = chart_month + 1
    mkt_month["chart_month"] = (mkt_month["period"] - 1).astype(str)
    chart_to_market_next = dict(zip(mkt_month["chart_month"], mkt_month["ret_month"]))

    samples = samples[["code", "name", "year_month", "ret_next", "sign_next"]].copy()
    samples["ret_market_next"] = samples["year_month"].map(chart_to_market_next)
    n_missing_mkt = samples["ret_market_next"].isna().sum()
    print(f"[market_next] missing={n_missing_mkt} (날짜 매핑 실패)", flush=True)

    # 종목별 daily ret
    ohlcv = ohlcv.sort_values(["code", "date"]).reset_index(drop=True)
    ohlcv["ret_d"] = ohlcv.groupby("code")["close"].pct_change()
    ohlcv["year_month"] = ohlcv["date"].dt.to_period("M").astype(str)

    # 시장 daily ret 매핑
    market_d = market[["date", "ret_daily"]].rename(columns={"ret_daily": "ret_d_mkt"})
    ohlcv = ohlcv.merge(market_d, on="date", how="left")

    # rolling 60거래일 beta: cov(stock, market)/var(market) per code
    # 각 종목별로 rolling. pandas rolling cov 는 정확히 이 형태.
    def _calc_beta(g: pd.DataFrame, win: int = 60) -> pd.DataFrame:
        s = g["ret_d"]
        m = g["ret_d_mkt"]
        cov = s.rolling(win, min_periods=win).cov(m)
        var = m.rolling(win, min_periods=win).var()
        # zero-var 방지
        beta = cov / var.replace(0.0, np.nan)
        g = g.copy()
        g["beta_60d"] = beta
        return g

    print("[beta] rolling 60d 계산...", flush=True)
    ohlcv = ohlcv.groupby("code", group_keys=False).apply(_calc_beta)

    # 각 (code, year_month) 의 마지막 거래일에서의 beta
    beta_at_month_end = (
        ohlcv.dropna(subset=["beta_60d"])
        .groupby(["code", "year_month"])
        .agg(beta_60d=("beta_60d", "last"))
        .reset_index()
    )
    samples = samples.merge(beta_at_month_end, on=["code", "year_month"], how="left")
    n_missing_beta = samples["beta_60d"].isna().sum()
    print(f"[beta] missing={n_missing_beta} (60일 미달 등)", flush=True)

    # 잔차 라벨
    samples["ret_residual_simple"] = samples["ret_next"] - samples["ret_market_next"]
    # CAPM beta missing 인 경우 → 그 샘플은 NaN. 통계에서 자동 제외.
    samples["ret_residual_capm"] = samples["ret_next"] - samples["beta_60d"] * samples["ret_market_next"]

    print("[stats] simple residual: mean={:.4f} pct_pos={:.3f} N_valid={}".format(
        samples["ret_residual_simple"].mean(),
        (samples["ret_residual_simple"] > 0).mean(),
        samples["ret_residual_simple"].notna().sum()), flush=True)
    print("[stats] CAPM residual: mean={:.4f} pct_pos={:.3f} N_valid={}".format(
        samples["ret_residual_capm"].mean(),
        (samples["ret_residual_capm"] > 0).mean(),
        samples["ret_residual_capm"].notna().sum()), flush=True)

    out_csv = CACHE / "market" / "labels_residual.csv"
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    samples.to_csv(out_csv, index=False, encoding="utf-8-sig")
    print(f"[save] {out_csv}", flush=True)

    # B-1 클러스터에 머지하여 clusters_simple.csv / clusters_capm.csv 생성
    base = clusters_b1.merge(
        samples[["code", "year_month", "ret_market_next", "beta_60d",
                 "ret_residual_simple", "ret_residual_capm"]],
        on=["code", "year_month"], how="left",
    )

    def _make_cluster_file(df: pd.DataFrame, label_col: str) -> pd.DataFrame:
        out = df.dropna(subset=[label_col]).copy()
        out["ret_next"] = out[label_col]
        out["sign_next"] = np.where(out["ret_next"] > 0, "U",
                                    np.where(out["ret_next"] < 0, "D", "F"))
        cols = ["code", "name", "year_month", "n_days", "ret_next", "sign_next", "cluster_id"]
        return out[cols]

    sim_path = CACHE / "emb_norm_series" / "clusters_simple.csv"
    capm_path = CACHE / "emb_norm_series" / "clusters_capm.csv"
    _make_cluster_file(base, "ret_residual_simple").to_csv(sim_path, index=False, encoding="utf-8-sig")
    _make_cluster_file(base, "ret_residual_capm").to_csv(capm_path, index=False, encoding="utf-8-sig")
    print(f"[save] {sim_path}", flush=True)
    print(f"[save] {capm_path}", flush=True)

    print("DONE", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
