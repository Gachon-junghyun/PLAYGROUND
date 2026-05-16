"""Step 2: input_candidates → v3 inner-monologue 파이프 → (input, thoughts, reply) 트리플.

PLAY7와 동일한 thinker/speaker 프롬프트 사용 (PLAY8 안에 자체 복사본).
ollama chat API, think:false. 길게 도는 background 작업 — sentinel 출력.

Output: data/triples.raw.jsonl (한 줄당 하나의 트리플 + 메타)
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
INPUT_FILE = ROOT / "data" / "input_candidates.jsonl"
OUT_FILE = ROOT / "data" / "triples.raw.jsonl"
OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"


def load_prompt(name: str) -> str:
    return (PROMPTS / f"{name}.md").read_text(encoding="utf-8")


def clean_block(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```\w*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def call_ollama(model: str, prompt: str, temperature: float, max_tokens: int) -> str:
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
    with urllib.request.urlopen(req, timeout=180) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return body.get("message", {}).get("content", "") or body.get("response", "")


def format_reference(ref_lines: list[str]) -> str:
    """Format reference_after lines as a quoted block for the Thinker prompt."""
    cleaned = [s.strip() for s in (ref_lines or []) if s and s.strip()]
    if not cleaned:
        return "(없음)"
    return "\n".join(f"- {s}" for s in cleaned[:3])


def run_thinker(
    model: str, user_input: str, reference_after: list[str], tmpl: str
) -> str:
    prompt = tmpl.replace("{user_input}", user_input).replace(
        "{reference_after}", format_reference(reference_after)
    )
    return clean_block(call_ollama(model, prompt, 0.7, 600))


def run_speaker(model: str, user_input: str, thoughts: str, tmpl: str) -> str:
    prompt = tmpl.replace("{user_input}", user_input).replace(
        "{inner_monologue}", thoughts
    )
    return clean_block(call_ollama(model, prompt, 0.8, 300))


def already_done_ids(out_path: Path) -> set[str]:
    """Resume support — re-running doesn't redo chunks already in OUT."""
    if not out_path.exists():
        return set()
    done = set()
    with out_path.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                done.add(json.loads(line)["chunk_id"])
            except Exception:
                pass
    return done


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="gemma4:e4b")
    ap.add_argument("--limit", type=int, default=None, help="smoke test: first N chunks")
    ap.add_argument("--resume", action="store_true", help="skip chunks already in output")
    args = ap.parse_args()

    if not INPUT_FILE.exists():
        print(f"FAILED: {INPUT_FILE} missing — run chunk_transcripts.py first", flush=True)
        return 2

    OUT_FILE.parent.mkdir(exist_ok=True)
    thinker_tmpl = load_prompt("thinker")
    speaker_tmpl = load_prompt("speaker")

    chunks = [json.loads(l) for l in INPUT_FILE.open("r", encoding="utf-8") if l.strip()]
    if args.limit:
        chunks = chunks[: args.limit]

    done = already_done_ids(OUT_FILE) if args.resume else set()
    todo = [c for c in chunks if c["chunk_id"] not in done]
    mode = "a" if args.resume else "w"
    print(f"[gen] model={args.model} todo={len(todo)} (skip={len(chunks)-len(todo)})", flush=True)

    ok = fail = 0
    with OUT_FILE.open(mode, encoding="utf-8") as f:
        for i, c in enumerate(todo, 1):
            t0 = time.time()
            try:
                ref_after = c.get("reference_after", [])
                thoughts = run_thinker(args.model, c["input_text"], ref_after, thinker_tmpl)
                reply = run_speaker(args.model, c["input_text"], thoughts, speaker_tmpl)
                ok += 1
                row = {
                    "chunk_id": c["chunk_id"],
                    "model": args.model,
                    "input": c["input_text"],
                    "reference_after": ref_after,
                    "thoughts": thoughts,
                    "reply": reply,
                    "source_path": c["source_path"],
                    "elapsed": round(time.time() - t0, 2),
                }
            except urllib.error.URLError as e:
                print(f"[gen] FAILED ollama down: {e}", flush=True)
                print("FAILED: ollama_down", flush=True)
                return 2
            except Exception as e:
                fail += 1
                row = {
                    "chunk_id": c["chunk_id"],
                    "model": args.model,
                    "input": c["input_text"],
                    "error": f"{type(e).__name__}: {e}",
                }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            f.flush()
            print(f"[gen] [{i}/{len(todo)}] {c['chunk_id']} ok={ok} fail={fail} elapsed={row.get('elapsed', '?')}s", flush=True)

    print(f"[gen] summary ok={ok} fail={fail}", flush=True)
    print("DONE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
