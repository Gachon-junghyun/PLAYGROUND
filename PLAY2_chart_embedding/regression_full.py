"""풀 차트 임베딩으로 다음달 수익률 회귀."""
from __future__ import annotations
import argparse, time, sys
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_squared_error, r2_score

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
OUT = HERE / "output" / "full" / "regression"
SEED = 42
SPLIT_PCT = 0.80


def quintile_spread(y_true, y_pred):
    n = len(y_pred)
    if n < 10:
        return float("nan")
    order = np.argsort(y_pred)
    q = n // 5
    return float(np.mean(y_true[order[-q:]]) - np.mean(y_true[order[:q]]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default=None)
    ap.add_argument("--models", default="all")
    ap.add_argument("--append", action="store_true")
    args = ap.parse_args()

    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)

    emb = np.load(CACHE / "full" / "embedding_pca.npy")
    samples = pd.read_parquet(CACHE / "samples.parquet").iloc[:len(emb)].reset_index(drop=True)
    res = pd.read_csv(CACHE / "market" / "labels_residual.csv", dtype={"code": str, "year_month": str})
    df = samples[["code", "year_month", "ret_next"]].copy()
    df = df.merge(res[["code", "year_month", "ret_residual_simple", "ret_residual_capm"]], on=["code", "year_month"], how="left")
    df["row"] = np.arange(len(df))
    df = df.sort_values("year_month").reset_index(drop=True)
    print("merged N=" + str(len(df)) + " elapsed=" + str(round(time.time()-t0, 1)))

    months = sorted(df["year_month"].unique())
    n_train_m = int(len(months) * SPLIT_PCT)
    train_months = set(months[:n_train_m])
    test_months = set(months[n_train_m:])
    train_mask = df["year_month"].isin(train_months).values
    test_mask = df["year_month"].isin(test_months).values
    print("split train=" + str(int(train_mask.sum())) + " test=" + str(int(test_mask.sum())))

    label_list = [args.label] if args.label else ["ret_next", "ret_residual_simple", "ret_residual_capm"]
    all_models = [
        ("Linear", LinearRegression()),
        ("Ridge", Ridge(alpha=1.0)),
        ("RF", RandomForestRegressor(n_estimators=100, max_depth=8, n_jobs=-1, random_state=SEED)),
    ]
    if args.models != "all":
        want = set(s.strip() for s in args.models.split(","))
        model_list = [m for m in all_models if m[0] in want]
    else:
        model_list = all_models

    rows = []
    for label_col in label_list:
        y = df[label_col].values
        valid = ~np.isnan(y)
        idx_full = df["row"].values
        tr = train_mask & valid
        te = test_mask & valid
        if tr.sum() < 100 or te.sum() < 100:
            continue
        X_tr = emb[idx_full[tr]]
        X_te = emb[idx_full[te]]
        y_tr = y[tr]
        y_te = y[te]
        for model_name, model in model_list:
            t1 = time.time()
            model.fit(X_tr, y_tr)
            yp = model.predict(X_te)
            r2 = r2_score(y_te, yp)
            mse = mean_squared_error(y_te, yp)
            sign_acc = float(np.mean(np.sign(yp) == np.sign(y_te)))
            qs = quintile_spread(y_te, yp)
            rows.append({"label": label_col, "model": model_name, "n_train": int(tr.sum()), "n_test": int(te.sum()), "r2": r2, "mse": mse, "sign_acc": sign_acc, "quintile_spread": qs})
            print(label_col + " " + model_name + " R2=" + str(round(r2, 4)) + " sign=" + str(round(sign_acc, 3)) + " qs=" + str(round(qs, 4)) + " t=" + str(round(time.time()-t1, 1)))

    out_df = pd.DataFrame(rows)
    out_path = OUT / "results.csv"
    if args.append and out_path.exists():
        prev = pd.read_csv(out_path)
        out_df = pd.concat([prev, out_df], ignore_index=True)
    out_df.to_csv(out_path, index=False)
    print("saved " + str(out_path) + " rows=" + str(len(out_df)))


if __name__ == "__main__":
    main()
