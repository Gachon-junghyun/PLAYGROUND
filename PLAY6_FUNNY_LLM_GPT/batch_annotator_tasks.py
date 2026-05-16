from __future__ import annotations

import argparse
import json
from pathlib import Path


BASE = Path(__file__).resolve().parent
DATA_DIR = BASE / "data"
PROMPT_PATH = BASE / "annotator_prompt.md"


def load_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Split annotator tasks into small JSON batch files.")
    parser.add_argument("--input", type=Path, default=DATA_DIR / "annotator_tasks.jsonl")
    parser.add_argument("--out-dir", type=Path, default=DATA_DIR / "annotator_batches")
    parser.add_argument("--batch-size", type=int, default=25)
    args = parser.parse_args()

    if not args.input.exists():
        raise SystemExit("Annotator tasks not found. Run: python build_microstyle_db.py")

    prompt = PROMPT_PATH.read_text(encoding="utf-8") if PROMPT_PATH.exists() else ""
    tasks = load_jsonl(args.input)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    for old in args.out_dir.glob("batch_*.json"):
        old.unlink()

    count = 0
    for index in range(0, len(tasks), args.batch_size):
        batch = tasks[index:index + args.batch_size]
        payload = {
            "batch_id": f"batch_{count + 1:04d}",
            "system_prompt": prompt,
            "tasks": batch,
        }
        path = args.out_dir / f"batch_{count + 1:04d}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        count += 1

    print(f"[OK] batches: {count} -> {args.out_dir}")


if __name__ == "__main__":
    main()
