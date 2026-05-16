"""(개선 4) sensitivity 시나리오들 결과 → 한 장 비교표.

입력: output/sensitivity/cluster_summary_{scenario}.csv + meta_{scenario}.txt
출력: output/sensitivity/sensitivity_summary.csv
"""
from __future__ import annotations

import sys
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
OUT_S = HERE / "output" / "sensitivity"

ORDER = [
    "baseline",
    "chart_small", "chart_large", "chart_wide",
    "label_5d", "label_20d", "label_3class",
]


def parse_meta(path: Path) -> dict:
    out = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def main() -> int:
    rows = []
    for s in ORDER:
        meta = parse_meta(OUT_S / f"meta_{s}.txt")
        if not meta:
            print(f"[skip] {s} (meta missing)", flush=True)
            continue
        rows.append({
            "scenario": s,
            "n_total": int(meta.get("n_total", 0)),
            "baseline_up_rate": float(meta.get("baseline_up_rate", float("nan"))),
            "baseline_mean_ret": float(meta.get("baseline_mean_ret", float("nan"))),
            "max_cluster_up_rate": float(meta.get("max_up_rate", float("nan"))),
            "min_cluster_up_rate": float(meta.get("min_up_rate", float("nan"))),
            "spread_pp": round(
                (float(meta["max_up_rate"]) - float(meta["min_up_rate"])) * 100, 2
            ),
            "max_above_baseline_pp": round(
                (float(meta["max_up_rate"]) - float(meta["baseline_up_rate"])) * 100, 2
            ),
            "min_below_baseline_pp": round(
                (float(meta["baseline_up_rate"]) - float(meta["min_up_rate"])) * 100, 2
            ),
        })
    df = pd.DataFrame(rows)
    out_path = OUT_S / "sensitivity_summary.csv"
    df.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"[save] {out_path}", flush=True)
    print(df.to_string(index=False), flush=True)
    print("DONE", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
