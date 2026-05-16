"""Run all 50 eval cases against one or more models.

Output: results/run_{model_safe_name}_{ts}.jsonl, one line per case.
Each line: {case_id, model, input, expected_*, judgment, reply, errors, secs}.

Designed to be long-running. Prints progress lines + DONE/FAILED sentinel
per _REFERENCE/long_running.md.

Usage:
    python -u src/bench.py --models gemma3:4b exaone3.5:2.4b
    python -u src/bench.py --models gemma3:4b --limit 5      # quick smoke
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import traceback
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CASES = ROOT / "eval" / "cases.jsonl"
RESULTS = ROOT / "results"

sys.path.insert(0, str(ROOT / "src"))
from run_ollama import run_one  # noqa: E402


def safe_name(model: str) -> str:
    return model.replace(":", "_").replace("/", "_")


def load_cases(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def bench_model(model: str, cases: list[dict], out_path: Path) -> dict:
    n = len(cases)
    ok = fail = 0
    print(f"[bench] {model} → {out_path.name} ({n} cases)", flush=True)
    with out_path.open("w", encoding="utf-8") as f:
        for i, case in enumerate(cases, 1):
            try:
                result = run_one(model, case["input"])
                # Preserve any extra meta the case file carries (e.g. source for YouTube cases).
                row = {
                    "case_id": case.get("id"),
                    "category": case.get("category"),
                    "expected_humor_level": case.get("expected_humor_level"),
                    "expected_risk": case.get("expected_risk"),
                    **result,
                }
                if "source" in case:
                    row["source"] = case["source"]
                ok += 1
            except urllib.error.URLError as e:
                print(f"[bench] FAILED: ollama down: {e}", flush=True)
                return {"ok": ok, "fail": fail, "halted": True, "reason": str(e)}
            except Exception as e:
                row = {
                    "case_id": case["id"],
                    "category": case["category"],
                    "model": model,
                    "input": case["input"],
                    "error": f"{type(e).__name__}: {e}",
                    "traceback": traceback.format_exc(),
                }
                fail += 1
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            f.flush()
            print(
                f"[bench] {model} [{i}/{n}] {case['id']} ok={ok} fail={fail}",
                flush=True,
            )
    return {"ok": ok, "fail": fail, "halted": False}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", required=True)
    ap.add_argument("--limit", type=int, default=None, help="smoke test: first N cases")
    ap.add_argument(
        "--cases",
        default=str(DEFAULT_CASES),
        help="path to a cases jsonl (default: eval/cases.jsonl). Each line must have id/category/input fields.",
    )
    ap.add_argument(
        "--tag",
        default=None,
        help="optional tag inserted into output filename, e.g. 'youtube' → run_<model>_youtube_<ts>.jsonl",
    )
    args = ap.parse_args()

    RESULTS.mkdir(exist_ok=True)
    cases_path = Path(args.cases)
    if not cases_path.is_absolute():
        cases_path = ROOT / cases_path
    cases = load_cases(cases_path)
    if args.limit:
        cases = cases[: args.limit]
    print(f"[bench] loaded {len(cases)} cases from {cases_path}", flush=True)

    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    tag_part = f"_{args.tag}" if args.tag else ""
    summary = {}
    for model in args.models:
        out_path = RESULTS / f"run_{safe_name(model)}{tag_part}_{ts}.jsonl"
        try:
            summary[model] = bench_model(model, cases, out_path)
        except Exception as e:
            print(f"FAILED: {model}: {e}", flush=True)
            traceback.print_exc()
            summary[model] = {"ok": 0, "fail": len(cases), "error": str(e)}

    print(f"[bench] summary: {json.dumps(summary, ensure_ascii=False)}", flush=True)
    halted = any(s.get("halted") for s in summary.values())
    print("FAILED: bench halted (ollama down)" if halted else "DONE", flush=True)
    return 1 if halted else 0


if __name__ == "__main__":
    sys.exit(main())
