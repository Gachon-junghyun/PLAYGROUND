from __future__ import annotations

import argparse
import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


BASE = Path(__file__).resolve().parent
DATA_DIR = BASE / "data"
DEFAULT_TASKS = DATA_DIR / "annotator_tasks.jsonl"
DEFAULT_OUT = DATA_DIR / "ollama_microstyle_entries.jsonl"
DEFAULT_REJECTS = DATA_DIR / "ollama_rejects.jsonl"
PROMPT_PATH = BASE / "annotator_prompt.md"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def existing_task_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    done: set[str] = set()
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            task_id = row.get("task_id") or row.get("source", {}).get("task_id")
            if task_id:
                done.add(task_id)
    return done


def compact_task(task: dict[str, Any]) -> dict[str, Any]:
    source = task["source"]
    item = task["input"]
    return {
        "task_id": task["task_id"],
        "source": source,
        "context_before": item.get("context_before", []),
        "utterance": item.get("utterance", ""),
        "context_after": item.get("context_after", []),
        "heuristic_type": item.get("heuristic_type", ""),
        "heuristic_tags": item.get("heuristic_tags", {}),
    }


def build_prompt(system_prompt: str, task: dict[str, Any]) -> str:
    return (
        f"{system_prompt}\n\n"
        "아래 작업 하나만 처리해라. JSON 외의 설명은 쓰지 마라.\n\n"
        f"작업:\n{json.dumps(compact_task(task), ensure_ascii=False, indent=2)}\n"
    )


def call_ollama(model: str, prompt: str, host: str, temperature: float, timeout: int) -> str:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_ctx": 4096,
        },
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{host.rstrip('/')}/api/generate",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return str(body.get("response", ""))


def extract_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def normalize_entry(task: dict[str, Any], raw: dict[str, Any], model: str) -> dict[str, Any]:
    source = task["source"]
    task_id = task["task_id"]
    entry_type = raw.get("entry_type") or task["input"].get("heuristic_type") or "principle"
    return {
        "task_id": task_id,
        "model": model,
        "entry_type": entry_type,
        "utterance": str(raw.get("utterance") or task["input"].get("utterance") or "").strip(),
        "context": str(raw.get("context") or "").strip(),
        "social_function": raw.get("social_function") or [],
        "style_devices": raw.get("style_devices") or [],
        "usable_when": raw.get("usable_when") or [],
        "avoid_when": raw.get("avoid_when") or [],
        "rewrite_templates": raw.get("rewrite_templates") or [],
        "quality_notes": str(raw.get("quality_notes") or "").strip(),
        "source": {
            "task_id": task_id,
            "candidate_id": source.get("candidate_id"),
            "source_path": source.get("source_path"),
            "line_number": source.get("line_number"),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Annotate microstyle candidates with a local Ollama model.")
    parser.add_argument("--model", default="gemma4:e4b")
    parser.add_argument("--host", default="http://localhost:11434")
    parser.add_argument("--tasks", type=Path, default=DEFAULT_TASKS)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--rejects", type=Path, default=DEFAULT_REJECTS)
    parser.add_argument("--limit", type=int, default=20, help="How many new tasks to process.")
    parser.add_argument("--offset", type=int, default=0, help="Skip this many tasks before filtering done ids.")
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--sleep", type=float, default=0.0)
    parser.add_argument("--reset", action="store_true", help="Delete output/reject files before running.")
    args = parser.parse_args()

    if args.reset:
        for path in [args.out, args.rejects]:
            if path.exists():
                path.unlink()

    if not args.tasks.exists():
        raise SystemExit("Annotator tasks not found. Run: python build_microstyle_db.py")

    system_prompt = PROMPT_PATH.read_text(encoding="utf-8")
    tasks = load_jsonl(args.tasks)[args.offset:]
    done = existing_task_ids(args.out)
    selected = [task for task in tasks if task["task_id"] not in done][:args.limit]

    if not selected:
        print("[OK] no new tasks to process")
        return

    ok = 0
    failed = 0
    started = time.time()
    for index, task in enumerate(selected, 1):
        task_id = task["task_id"]
        print(f"[{index}/{len(selected)}] {task_id} {task['source']['source_path']}:{task['source']['line_number']}", flush=True)
        prompt = build_prompt(system_prompt, task)
        try:
            response = call_ollama(args.model, prompt, args.host, args.temperature, args.timeout)
            raw = extract_json(response)
            entry = normalize_entry(task, raw, args.model)
            append_jsonl(args.out, entry)
            ok += 1
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, Exception) as exc:
            append_jsonl(
                args.rejects,
                {
                    "task_id": task_id,
                    "model": args.model,
                    "error": repr(exc),
                    "task": compact_task(task),
                },
            )
            print(f"  [ERR] {repr(exc)}", flush=True)
            failed += 1
        if args.sleep:
            time.sleep(args.sleep)

    elapsed = time.time() - started
    print(f"[DONE] ok={ok} failed={failed} elapsed={elapsed:.1f}s")
    print(f"[OUT] {args.out}")
    if failed:
        print(f"[REJECTS] {args.rejects}")


if __name__ == "__main__":
    main()
