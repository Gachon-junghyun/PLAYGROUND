"""Single-case runner: Thinker (inner monologue) -> Speaker (reply) via Ollama.

The Thinker outputs a free-form Korean inner monologue — how the model
*decides* to answer, what tone to take, where to drop the punch line.
The Speaker then writes the actual reply, guided by that monologue.

Both fields are preserved in the output so the user can see WHY the model
answered the way it did.

Usage:
    python -u src/run_ollama.py --model gemma4:e4b --input "나 오늘 발표 망한 듯"
    python -u src/run_ollama.py --model gemma4:e4b --input-file in.txt
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROMPTS = ROOT / "prompts"
OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"
TIMEOUT_S = 180


def load_prompt(name: str) -> str:
    return (PROMPTS / f"{name}.md").read_text(encoding="utf-8")


def call_ollama(model: str, prompt: str, temperature: float = 0.7, max_tokens: int = 1200) -> str:
    """Call Ollama /api/chat. `think: false` disables reasoning mode so the
    model's actual content goes to message.content, not thinking tokens."""
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "think": False,
        "options": {"temperature": temperature, "num_predict": max_tokens},
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_CHAT_URL,
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return body.get("message", {}).get("content", "") or body.get("response", "")


def clean_block(text: str) -> str:
    """Strip leading/trailing markdown fences and whitespace."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```\w*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def run_thinker(model: str, user_input: str) -> str:
    """Returns inner monologue (Korean free-form text)."""
    tmpl = load_prompt("thinker")
    prompt = tmpl.replace("{user_input}", user_input)
    raw = call_ollama(model, prompt, temperature=0.7, max_tokens=600)
    return clean_block(raw)


def run_speaker(model: str, user_input: str, thoughts: str) -> str:
    """Returns reply (one-line Korean utterance)."""
    tmpl = load_prompt("speaker")
    prompt = tmpl.replace("{user_input}", user_input).replace(
        "{inner_monologue}", thoughts
    )
    raw = call_ollama(model, prompt, temperature=0.8, max_tokens=300)
    return clean_block(raw)


def run_one(model: str, user_input: str) -> dict:
    t0 = time.time()
    thoughts = run_thinker(model, user_input)
    t1 = time.time()
    reply = run_speaker(model, user_input, thoughts)
    t2 = time.time()
    return {
        "model": model,
        "input": user_input,
        "thoughts": thoughts,
        "reply": reply,
        "thinker_secs": round(t1 - t0, 2),
        "speaker_secs": round(t2 - t1, 2),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--input", help="inline string (Windows: chcp 65001 권장)")
    g.add_argument("--input-file", help="path to a UTF-8 text file with the user input")
    args = ap.parse_args()

    if args.input_file:
        user_input = Path(args.input_file).read_text(encoding="utf-8").strip()
    else:
        user_input = args.input

    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass

    try:
        out = run_one(args.model, user_input)
    except urllib.error.URLError as e:
        print(f"FAILED: ollama not reachable at {OLLAMA_CHAT_URL}: {e}", flush=True)
        return 2

    # Human-readable narrative output, then machine-readable JSON.
    print("=" * 72)
    print(f"INPUT  : {out['input']}")
    print("-" * 72)
    print("THINKER 사고:")
    print(out["thoughts"])
    print("-" * 72)
    print(f"SPEAKER 답변: {out['reply']}")
    print("=" * 72)
    print(f"(thinker {out['thinker_secs']}s + speaker {out['speaker_secs']}s)")
    print()
    print("--- JSON ---")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
