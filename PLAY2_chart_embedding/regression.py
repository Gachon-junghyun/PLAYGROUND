"""(시장 통제 3) B-1 임베딩 → 다음달 수익률 직접 회귀.

특징(X) = cache/emb_norm_series/embeddings.npy (PCA 8차원).
라벨 3종:
  ret_next                — 원시
  ret_residual_simple     — 시장 단순 차감
  ret_residual_capm       — CAPM 잔차

모델 3종: LinearRegression, Ridge(alpha=1.0), RandomForestRegressor(n_estimators=100, max_depth=8).

검증: time-series split. 시점 정렬 후 앞 80% 학습 / 뒤 20% 검증. 1회 분할.

지표: R², MSE, sign_accuracy (예측 부호 일치율), top_minus_bottom_quintile.

출력: output/regression/results.csv
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_squared_error, r2_score

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
OUT = HERE / "output" / "regression"

SEED = 42
SPLIT_PCT = 0.80


def quintile_spread(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    n = len(y_pred)
    if n < 10:
        return float("nan")
    order = np.argsort(y_pred)
    q = n // 5
    bottom = y_true[order[:q]]
    top = y_true[order[-q:]]
    return float(np.mean(top) - np.mean(bottom))


def evaluate(name_label: str, y_train: np.ndarray, y_test: np.ndarray,
             X_train: np.ndarray, X_test: np.ndarray) -> list[dict]:
    """3개 모델로 학습/평가."""
    # NaN drop (label 기준)
    tr_mask = ~np.isnan(y_train)
    te_mask = ~np.isnan(y_test)
    Xtr, ytr = X_train[tr_mask], y_train[tr_mask]
    Xte, yte = X_test[te_mask], y_test[te_mask]

    models = {
        "linear": LinearRegression(),
        "ridge": Ridge(alpha=1.0, random_state=SEED),
        "rf": RandomForestRegressor(
            n_estimators=100, max_depth=8, n_jobs=-1, random_state=SEED,
        ),
    }
    rows = []
    for mname, m in models.items():
        t0 = time.time()
        m.fit(Xtr, ytr)
        yhat = m.predict(Xte)
        elapsed = time.time() - t0
        r2 = r2_score(yte, yhat)
        mse = mean_squared_error(yte, yhat)
        sign_acc = float(np.mean(np.sign(yhat) == np.sign(yte)))
        spread = quintile_spread(yte, yhat)
        rows.append({
            "label_type": name_label,
            "model": mname,
            "n_train": int(len(ytr)),
            "n_test": int(len(yte)),
            "R2": round(r2, 5),
            "MSE": round(mse, 6),
            "sign_accuracy": round(sign_acc, 4),
            "top_minus_bottom_quintile": round(spread, 5),
            "fit_secs": round(elapsed, 2),
        })
        print(f"  [{name_label}/{mname}] R²={r2:.4f} MSE={mse:.5f} "
              f"sign_acc={sign_acc:.3f} q_spread={spread:.4f} "
              f"({elapsed:.1f}s)", flush=True)
    return rows


def main() -> int:
    # 입력 정렬
    clusters = pd.read_csv(CACHE / "emb_norm_series" / "clusters.csv",
                           dtype={"code": str, "year_month": str})
    emb = np.load(CACHE / "emb_norm_series" / "embeddings.npy").astype(np.float32)
    if len(emb) != len(clusters):
        print(f"FAILED: shape mismatch emb={len(emb)} clusters={len(clusters)}", flush=True)
        return 1

    # residual 라벨 머지 (시점 단위 라벨 — code/year_month 매칭)
    resid = pd.read_csv(CACHE / "market" / "labels_residual.csv",
                        dtype={"code": str, "year_month": str})
    df = clusters.merge(
        resid[["code", "year_month", "ret_residual_simple", "ret_residual_capm"]],
        on=["code", "year_month"], how="left",
    )
    print(f"[start] N={len(df)} emb_dim={emb.shape[1]}", flush=True)

    # time-series split: year_month 정렬 기준
    months = sorted(df["year_month"].unique())
    cut_idx = int(len(months) * SPLIT_PCT)
    train_months = set(months[:cut_idx])
    test_months = set(months[cut_idx:])
    print(f"[split] train_months={len(train_months)} test_months={len(test_months)} "
          f"cutoff={months[cut_idx]}", flush=True)

    train_mask = df["year_month"].isin(train_months).values
    test_mask = df["year_month"].isin(test_months).values

    X_train = emb[train_mask]
    X_test = emb[test_mask]
    print(f"[split] X_train={X_train.shape} X_test={X_test.shape}", flush=True)

    label_cols = {
        "ret_next": "ret_next",
        "ret_residual_simple": "ret_residual_simple",
        "ret_residual_capm": "ret_residual_capm",
    }
    all_rows = []
    for label_name, col in label_cols.items():
        print(f"[label] {label_name}", flush=True)
        y_full = df[col].values.astype(np.float64)
        y_train = y_full[train_mask]
        y_test = y_full[test_mask]
        rows = evaluate(label_name, y_train, y_test, X_train, X_test)
        all_rows.extend(rows)

    out = pd.DataFrame(all_rows)
    OUT.mkdir(parents=True, exist_ok=True)
    out_path = OUT / "results.csv"
    out.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"[save] {out_path}", flush=True)

    # 요약
    print("\n[summary] 라벨별 best model (R² 기준)", flush=True)
    for lbl, sub in out.groupby("label_type"):
        idx = sub["R2"].idxmax()
        best = sub.loc[idx]
        print(f"  {lbl}: best={best['model']} R²={best['R2']:.4f} "
              f"sign_acc={best['sign_accuracy']:.3f} "
              f"q_spread={best['top_minus_bottom_quintile']:.4f}",
              flush=True)
    print("DONE", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
