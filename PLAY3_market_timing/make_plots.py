"""(4) 시각화 + 사용자가 직접 보는 한 장짜리 패널 csv.

입력: cache/timing_panel.parquet, cache/panel_meta.csv
출력:
  - output/cluster_vs_kospi.png  (top1, bot1 비율 + KOSPI 종가)
  - output/timing_panel_with_kospi.csv  (사람이 한눈에 보고 판단할 수 있는 csv)
"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / "cache"
OUT = ROOT / "output"
OUT.mkdir(parents=True, exist_ok=True)


def main():
    panel = pd.read_parquet(CACHE / "timing_panel.parquet").sort_values("year_month").reset_index(drop=True)
    meta = pd.read_csv(CACHE / "panel_meta.csv", header=None, index_col=0).iloc[:, 0]
    top1_id = int(meta["top1_cluster_id"])
    bot1_id = int(meta["bot1_cluster_id"])

    panel["t"] = pd.to_datetime(panel["year_month"] + "-01")

    fig, ax1 = plt.subplots(figsize=(12, 5))
    ax1.plot(panel["t"], panel["top1_pct"] * 100, color="tab:blue",
             label=f"top1 cluster_{top1_id}_pct (%)", linewidth=1.5)
    ax1.plot(panel["t"], panel["bot1_pct"] * 100, color="tab:red",
             label=f"bot1 cluster_{bot1_id}_pct (%)", linewidth=1.5)
    ax1.set_ylabel("cluster share (% of universe)")
    ax1.set_xlabel("month")
    ax1.legend(loc="upper left")
    ax1.grid(True, alpha=0.3)

    ax2 = ax1.twinx()
    ax2.plot(panel["t"], panel["close_last"], color="black",
             label="KOSPI close (rhs)", linewidth=1.2, linestyle="--")
    ax2.set_ylabel("KOSPI close")
    ax2.legend(loc="upper right")

    plt.title(
        f"Top1 / Bot1 cluster share vs KOSPI  (top1=cluster_{top1_id}, bot1=cluster_{bot1_id})"
    )
    plt.tight_layout()
    plt.savefig(OUT / "cluster_vs_kospi.png", dpi=130)
    plt.close()
    print(f"[plots] saved: {OUT / 'cluster_vs_kospi.png'}")

    # 사람이 직접 보고 판단할 수 있는 한 장 csv
    keep = ["year_month", "n_stocks", "top1_pct", "bot1_pct",
            "close_last", "kospi_ret", "kospi_ret_next"]
    panel[keep].to_csv(OUT / "timing_panel_with_kospi.csv", index=False)
    print(f"[plots] saved: {OUT / 'timing_panel_with_kospi.csv'}")


if __name__ == "__main__":
    main()
