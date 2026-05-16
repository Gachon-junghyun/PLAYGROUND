"""(3) 단순화 A — 시간순 70/30 split + 학습기간 KMeans 재적합 + 회귀.

절차:
  1. samples (13,971) + embeddings_pca_64_full → 시간순 70/30 split
  2. 학습기간 임베딩으로 KMeans K=20 재적합 (out-of-sample 클러스터 보장)
  3. 검증기간 임베딩을 transform → 시점별 cluster_dist 재산출
  4. 학습기간의 (cluster_dist → KOSPI 다음달 수익률) 회귀 fit (Linear / Ridge / RF)
  5. 검증기간 R², MSE, 부호 일치율 평가
  6. baseline = KOSPI lag-1, lag-3 momentum만으로 같은 회귀

입력: PLAY2 cache (samples, embeddings, kospi)
출력: output/walk_forward_results.csv
"""
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score, mean_squared_error

ROOT = Path(__file__).resolve().parent
PLAY_ROOT = ROOT.parent
PLAY2 = PLAY_ROOT / "PLAY2_chart_embedding"
CACHE = ROOT / "cache"
OUT = ROOT / "output"
OUT.mkdir(parents=True, exist_ok=True)

K = 20
SPLIT_FRACTION = 0.70
SEED = 42


def kospi_monthly():
    kospi = pd.read_parquet(PLAY2 / "cache" / "market" / "kospi.parquet")
    kospi["date"] = pd.to_datetime(kospi["date"])
    kospi["year_month"] = kospi["date"].dt.strftime("%Y-%m")
    monthly = kospi.groupby("year_month").agg(close_last=("close", "last")).reset_index()
    monthly = monthly.sort_values("year_month").reset_index(drop=True)
    monthly["kospi_ret"] = monthly["close_last"].pct_change()
    monthly["kospi_ret_next"] = monthly["kospi_ret"].shift(-1)
    monthly["kospi_ret_lag1"] = monthly["kospi_ret"].shift(1)
    monthly["kospi_ret_lag3"] = monthly["close_last"].pct_change(3).shift(1)
    return monthly


def make_dist(df_with_cluster: pd.DataFrame) -> pd.DataFrame:
    grp = df_with_cluster.groupby(["year_month", "cluster_id"]).size().unstack(fill_value=0)
    for k in range(K):
        if k not in grp.columns:
            grp[k] = 0
    grp = grp.reindex(sorted(grp.columns), axis=1)
    grp["n"] = grp.sum(axis=1)
    pct = grp[list(range(K))].div(grp["n"], axis=0)
    pct.columns = [f"cluster_{c}_pct" for c in pct.columns]
    return pct.reset_index()


def fit_eval(name, model, X_tr, y_tr, X_te, y_te, feat_label):
    model.fit(X_tr, y_tr)
    yhat_tr = model.predict(X_tr)
    yhat_te = model.predict(X_te)
    sign_acc = float(np.mean(np.sign(yhat_te) == np.sign(y_te)))
    return dict(
        model=name,
        features=feat_label,
        n_train=len(y_tr),
        n_test=len(y_te),
        train_R2=r2_score(y_tr, yhat_tr),
        test_R2=r2_score(y_te, yhat_te),
        train_MSE=mean_squared_error(y_tr, yhat_tr),
        test_MSE=mean_squared_error(y_te, yhat_te),
        test_sign_acc=sign_acc,
    )


def main():
    samples = pd.read_parquet(PLAY2 / "cache" / "samples.parquet")
    emb = np.load(PLAY2 / "cache" / "full" / "embeddings_pca_64_full.npy")
    assert len(samples) == len(emb)

    samples = samples.copy().reset_index(drop=True)
    samples["__idx"] = np.arange(len(samples))

    # 시간순 split: 월 단위로 자른다
    months = sorted(samples["year_month"].unique())
    n_months = len(months)
    cut = int(n_months * SPLIT_FRACTION)
    train_months = set(months[:cut])
    test_months = set(months[cut:])
    print(f"[wf] months={n_months}, train={len(train_months)} ({months[0]}..{months[cut-1]}), "
          f"test={len(test_months)} ({months[cut]}..{months[-1]})")

    train_mask = samples["year_month"].isin(train_months)
    test_mask = samples["year_month"].isin(test_months)
    emb_tr = emb[train_mask.values]
    emb_te = emb[test_mask.values]
    print(f"[wf] samples train={train_mask.sum()}, test={test_mask.sum()}")

    # KMeans 학습기간 fit
    km = KMeans(n_clusters=K, random_state=SEED, n_init=10)
    km.fit(emb_tr)
    cl_tr = km.labels_
    cl_te = km.predict(emb_te)

    df_tr = samples.loc[train_mask, ["year_month", "ret_next"]].copy()
    df_tr["cluster_id"] = cl_tr
    df_te = samples.loc[test_mask, ["year_month", "ret_next"]].copy()
    df_te["cluster_id"] = cl_te

    dist_tr = make_dist(df_tr)
    dist_te = make_dist(df_te)
    monthly = kospi_monthly()
    panel_tr = dist_tr.merge(monthly, on="year_month", how="left").dropna(subset=["kospi_ret_next"])
    panel_te = dist_te.merge(monthly, on="year_month", how="left").dropna(subset=["kospi_ret_next"])
    print(f"[wf] panel_tr={panel_tr.shape}, panel_te={panel_te.shape}")

    cluster_cols = [f"cluster_{c}_pct" for c in range(K)]
    momentum_cols = ["kospi_ret_lag1", "kospi_ret_lag3"]

    # 결측치 (lag-3는 첫 3개월 nan)
    panel_tr = panel_tr.dropna(subset=cluster_cols + momentum_cols)
    panel_te = panel_te.dropna(subset=cluster_cols + momentum_cols)
    print(f"[wf] after dropna panel_tr={panel_tr.shape}, panel_te={panel_te.shape}")

    y_tr = panel_tr["kospi_ret_next"].values
    y_te = panel_te["kospi_ret_next"].values

    feature_sets = {
        "momentum_only": momentum_cols,                     # baseline
        "cluster_only": cluster_cols,                       # 클러스터만
        "cluster+momentum": cluster_cols + momentum_cols,   # 결합
    }

    results = []
    for label, cols in feature_sets.items():
        X_tr = panel_tr[cols].values
        X_te = panel_te[cols].values
        results.append(fit_eval("Linear", LinearRegression(), X_tr, y_tr, X_te, y_te, label))
        results.append(fit_eval("Ridge", Ridge(alpha=1.0, random_state=SEED), X_tr, y_tr, X_te, y_te, label))
        results.append(fit_eval(
            "RF",
            RandomForestRegressor(n_estimators=100, max_depth=8, random_state=SEED, n_jobs=1),
            X_tr, y_tr, X_te, y_te, label,
        ))
    # naive baseline: 학습기간 평균값을 항상 예측
    mean_pred = float(np.mean(y_tr))
    yhat = np.full_like(y_te, mean_pred)
    results.append(dict(
        model="MeanBaseline", features="(constant)",
        n_train=len(y_tr), n_test=len(y_te),
        train_R2=0.0,
        test_R2=r2_score(y_te, yhat),
        train_MSE=float(np.mean((y_tr - mean_pred) ** 2)),
        test_MSE=mean_squared_error(y_te, yhat),
        test_sign_acc=float(np.mean(np.sign(yhat) == np.sign(y_te))),
    ))

    res_df = pd.DataFrame(results)
    res_df.to_csv(OUT / "walk_forward_results.csv", index=False)
    print("\n=== walk_forward_results ===")
    print(res_df.to_string(index=False))

    # 메타: split 경계
    pd.DataFrame({
        "train_first": [months[0]], "train_last": [months[cut-1]],
        "test_first": [months[cut]], "test_last": [months[-1]],
        "n_train_months": [len(train_months)], "n_test_months": [len(test_months)],
    }).to_csv(OUT / "walk_forward_split.csv", index=False)


if __name__ == "__main__":
    main()
