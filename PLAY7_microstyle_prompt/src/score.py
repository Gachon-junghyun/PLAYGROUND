"""Aggregate judged_*.jsonl files into a comparison report.

Output: results/report_{ts}.md

Per model:
  - overall mean (25점 만점)
  - axis means
  - per-category means (특히 H1 serious_grief에서 안 까부는지 핵심)
  - 워스트 5 케이스 (모델별)

Usage:
    python -u src/score.py
    python -u src/score.py --pattern "judged_run_*.jsonl"
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"

AXES = ("situation_fit", "humor_fit", "naturalness", "continuation", "safety")


def load_judged(pattern: str) -> dict[str, list[dict]]:
    """Returns {model: [judged_row, ...]}."""
    by_model: dict[str, list[dict]] = defaultdict(list)
    for path in sorted(glob.glob(str(RESULTS / pattern))):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                row = json.loads(line)
                model = row.get("model") or "unknown"
                by_model[model].append(row)
    return by_model


def axis_mean(rows: list[dict], axis: str) -> float:
    vals = [
        r["scores"].get(axis)
        for r in rows
        if isinstance(r.get("scores"), dict) and isinstance(r["scores"].get(axis), (int, float))
    ]
    return round(mean(vals), 2) if vals else 0.0


def total_mean(rows: list[dict]) -> float:
    vals = [
        r["scores"].get("total")
        for r in rows
        if isinstance(r.get("scores"), dict) and isinstance(r["scores"].get("total"), (int, float))
    ]
    return round(mean(vals), 2) if vals else 0.0


def category_means(rows: list[dict]) -> dict[str, float]:
    by_cat: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        cat = r.get("category", "?")
        if isinstance(r.get("scores"), dict) and isinstance(
            r["scores"].get("total"), (int, float)
        ):
            by_cat[cat].append(r["scores"]["total"])
    return {k: round(mean(v), 2) for k, v in sorted(by_cat.items())}


def worst_n(rows: list[dict], n: int = 5) -> list[dict]:
    scored = [
        r
        for r in rows
        if isinstance(r.get("scores"), dict)
        and isinstance(r["scores"].get("total"), (int, float))
    ]
    return sorted(scored, key=lambda r: r["scores"]["total"])[:n]


def write_report(by_model: dict[str, list[dict]]) -> Path:
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    out = RESULTS / f"report_{ts}.md"
    lines: list[str] = []
    lines.append(f"# Phase 1 Bench Report — {ts}")
    lines.append("")
    lines.append(f"Models compared: {len(by_model)}")
    lines.append("")

    lines.append("## Overall (25점 만점)")
    lines.append("")
    lines.append("| Model | Total | situation | humor | natural | continuation | safety | n |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for model, rows in by_model.items():
        lines.append(
            f"| `{model}` | **{total_mean(rows)}** | "
            f"{axis_mean(rows, 'situation_fit')} | "
            f"{axis_mean(rows, 'humor_fit')} | "
            f"{axis_mean(rows, 'naturalness')} | "
            f"{axis_mean(rows, 'continuation')} | "
            f"{axis_mean(rows, 'safety')} | "
            f"{len(rows)} |"
        )
    lines.append("")

    lines.append("## Per-Category (Total 평균)")
    lines.append("")
    all_cats: set[str] = set()
    for rows in by_model.values():
        all_cats.update(category_means(rows).keys())
    cats = sorted(all_cats)
    header = "| Model | " + " | ".join(cats) + " |"
    sep = "|---|" + "---|" * len(cats)
    lines.append(header)
    lines.append(sep)
    for model, rows in by_model.items():
        cm = category_means(rows)
        row = f"| `{model}` | " + " | ".join(str(cm.get(c, "-")) for c in cats) + " |"
        lines.append(row)
    lines.append("")
    lines.append("**핵심 컬럼:** `serious_grief`, `self_deprecation`, `relationship_conflict` 가 낮으면 안전성 약함.")
    lines.append("")

    lines.append("## 모델별 워스트 5")
    lines.append("")
    for model, rows in by_model.items():
        lines.append(f"### `{model}`")
        for r in worst_n(rows):
            scores = r["scores"]
            lines.append(
                f"- **{r.get('case_id')}** ({r.get('category')}) total={scores.get('total')}"
            )
            lines.append(f"  - input: {r.get('input')!r}")
            lines.append(f"  - reply: {r.get('reply')!r}")
            lines.append(f"  - axes: {{ s={scores.get('situation_fit')}, h={scores.get('humor_fit')}, n={scores.get('naturalness')}, c={scores.get('continuation')}, sf={scores.get('safety')} }}")
        lines.append("")

    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pattern", default="judged_run_*.jsonl")
    args = ap.parse_args()
    by_model = load_judged(args.pattern)
    if not by_model:
        print(f"FAILED: no files match {args.pattern}", flush=True)
        return 2
    out = write_report(by_model)
    print(f"[score] wrote {out}", flush=True)
    print("DONE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
