from __future__ import annotations

import argparse
import json
from pathlib import Path


BASE = Path(__file__).resolve().parent
DEFAULT_PATH = BASE / "data" / "ollama_microstyle_entries.jsonl"


def main() -> None:
    parser = argparse.ArgumentParser(description="Print generated Ollama microstyle entries.")
    parser.add_argument("--path", type=Path, default=DEFAULT_PATH)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--type", default=None)
    args = parser.parse_args()

    if not args.path.exists():
        raise SystemExit("No Ollama entries yet. Run: python ollama_annotate.py --limit 5")

    shown = 0
    with args.path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            if args.type and row.get("entry_type") != args.type:
                continue
            print(f"[{row.get('entry_type')}] {row.get('utterance')}")
            print(f"  context: {row.get('context')}")
            print(f"  function: {', '.join(row.get('social_function') or [])}")
            print(f"  devices: {', '.join(row.get('style_devices') or [])}")
            templates = row.get("rewrite_templates") or []
            if templates:
                print(f"  templates: {' / '.join(templates[:3])}")
            print()
            shown += 1
            if shown >= args.limit:
                break


if __name__ == "__main__":
    main()
