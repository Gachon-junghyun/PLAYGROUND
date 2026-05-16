"""Score a bench output file with an LLM judge.

Two backends:
  - ollama: local model (default: gemma3:27b or any model you have).
  - claude: Anthropic API (env ANTHROPIC_API_KEY).

Input: results/run_*.jsonl
Output: results/judged_*.jsonl   one line per case with rubric scores.

Usage:
    python -u src/judge.py --input results/run_gemma3_4b_*.jsonl --backend ollama --judge-model gemma3:12b
    python -u src/judge.py --input results/run_gemma3_4b_*.jsonl --backend claude --judge-model claude-haiku-4-5-20251001
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROMPTS = ROOT / "prompts"
RESULTS = ROOT / "results"
OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"


def load_judge_prompt() -> str:
    return (PROMPTS / "judge.md").read_text(encoding="utf-8")


def fill(template: str, user_input: str, expected: dict, reply: str) -> str:
    return (
        template.replace("{user_input}", user_input)
        .replace("{expected}", json.dumps(expected, ensure_ascii=False))
        .replace("{model_reply}", reply)
    )


def extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        raise ValueError(f"no json in: {text[:200]!r}")
    return json.loads(m.group(0))


def call_ollama(model: str, prompt: str) -> str:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "think": False,
        "options": {"temperature": 0.1, "num_predict": 600},
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_CHAT_URL,
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return body.get("message", {}).get("content", "") or body.get("response", "")


def call_claude(model: str, prompt: str) -> str:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    payload = {
        "model": model,
        "max_tokens": 400,
        "messages": [{"role": "user", "content": prompt}],
    }
    req = urllib.request.Request(
        ANTHROPIC_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return "".join(block.get("text", "") for block in body.get("content", []))


def score_one(
    backend: str, judge_model: str, row: dict, template: str
) -> dict:
    if row.get("error") or not row.get("reply"):
        return {"_skipped": True, "reason": row.get("error", "no reply")}
    expected = {
        "humor_level": row["expected_humor_level"],
        "risk": row["expected_risk"],
    }
    prompt = fill(template, row["input"], expected, row["reply"])
    if backend == "ollama":
        raw = call_ollama(judge_model, prompt)
    elif backend == "claude":
        raw = call_claude(judge_model, prompt)
    else:
        raise ValueError(f"unknown backend: {backend}")
    try:
        scores = extract_json(raw)
        for axis in ("situation_fit", "humor_fit", "naturalness", "continuation", "safety"):
            if axis not in scores:
                scores[axis] = 0
        scores["total"] = sum(
            scores[a] for a in ("situation_fit", "humor_fit", "naturalness", "continuation", "safety")
        )
        return scores
    except Exception as e:
        return {"_parse_error": str(e), "_raw": raw[:300]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="path or glob to run_*.jsonl")
    ap.add_argument("--backend", choices=["ollama", "claude"], default="ollama")
    ap.add_argument("--judge-model", required=True)
    args = ap.parse_args()

    paths = sorted(glob.glob(args.input))
    if not paths:
        print(f"FAILED: no files match {args.input}", flush=True)
        return 2

    template = load_judge_prompt()

    for in_path in paths:
        in_p = Path(in_path)
        out_p = RESULTS / f"judged_{in_p.stem}.jsonl"
        print(f"[judge] {in_p.name} → {out_p.name}", flush=True)
        with in_p.open("r", encoding="utf-8") as f, out_p.open(
            "w", encoding="utf-8"
        ) as g:
            rows = [json.loads(line) for line in f if line.strip()]
            for i, row in enumerate(rows, 1):
                try:
                    scores = score_one(args.backend, args.judge_model, row, template)
                except urllib.error.URLError as e:
                    print(f"[judge] FAILED: backend down: {e}", flush=True)
                    return 2
                merged = {
                    "case_id": row.get("case_id"),
                    "category": row.get("category"),
                    "model": row.get("model"),
                    "input": row.get("input"),
                    "reply": row.get("reply"),
                    "scores": scores,
                }
                g.write(json.dumps(merged, ensure_ascii=False) + "\n")
                g.flush()
                total = scores.get("total", "?")
                print(f"[judge] [{i}/{len(rows)}] {row.get('case_id')} total={total}", flush=True)
    print("DONE", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
