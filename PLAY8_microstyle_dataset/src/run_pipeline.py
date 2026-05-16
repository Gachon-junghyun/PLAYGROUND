"""Full pipeline runner: generate → filter → build.

Resume-safe. Idempotent. Designed for `python -u src/run_pipeline.py > pipe.log 2>&1`
as a long background job. Emits DONE/FAILED sentinels on each step and at end.

Usage:
    python -u src/run_pipeline.py --model gemma4:e4b
    python -u src/run_pipeline.py --model gemma4:e4b --resume  # default behavior
    python -u src/run_pipeline.py --model gemma4:e4b --skip-generate  # only filter+build
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(label: str, cmd: list[str]) -> int:
    print(f"\n========== {label} ==========", flush=True)
    print(f"$ {' '.join(cmd)}", flush=True)
    t0 = time.time()
    # Reconfigure parent stdout to utf-8 so child's Korean output doesn't crash
    # on Windows cp949 console.
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace", cwd=str(ROOT),
    )
    assert proc.stdout is not None
    for line in proc.stdout:
        try:
            print(line.rstrip(), flush=True)
        except UnicodeEncodeError:
            # Last-resort: byte-safe write
            sys.stdout.buffer.write(line.rstrip().encode("utf-8", errors="replace") + b"\n")
            sys.stdout.buffer.flush()
    rc = proc.wait()
    print(f"[{label}] exit={rc} elapsed={time.time()-t0:.1f}s", flush=True)
    return rc


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="gemma4:e4b")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--no-resume", action="store_true",
                    help="overwrite triples.raw.jsonl from scratch")
    ap.add_argument("--skip-generate", action="store_true",
                    help="only run filter + build on existing triples.raw.jsonl")
    args = ap.parse_args()

    py = sys.executable

    if not args.skip_generate:
        gen_cmd = [py, "-u", "src/generate_triples.py", "--model", args.model]
        if not args.no_resume:
            gen_cmd.append("--resume")
        if args.limit:
            gen_cmd += ["--limit", str(args.limit)]
        rc = run("generate", gen_cmd)
        if rc != 0:
            print(f"FAILED: generate step exit {rc}", flush=True)
            return rc

    rc = run("filter", [py, "-u", "src/filter_quality.py"])
    if rc != 0:
        print(f"FAILED: filter step exit {rc}", flush=True)
        return rc

    rc = run("build", [py, "-u", "src/build_dataset.py"])
    if rc != 0:
        print(f"FAILED: build step exit {rc}", flush=True)
        return rc

    print("DONE: pipeline complete", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
