"""
학습된 LoRA adapter를 PLAY7 평가셋(cases.jsonl 50건 + cases_youtube.jsonl 30건)에 돌려서
PLAY7 judge.py가 그대로 채점 가능한 jsonl 출력 (Unsloth 기반).

사용:
  python -u src/eval_against_baseline.py --adapter ckpt/final
"""
from __future__ import annotations
import argparse
import io
import json
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
EVAL = ROOT / "eval"
REPORTS = ROOT / "reports"

SYSTEM_PROMPT = (
    "너는 친구의 톡을 받고 머릿속으로 어떻게 답할지 한 번 굴린 뒤 답하는 한국어 화자다. "
    "먼저 <think>...</think> 안에 자연스러운 자기 사고를 적고, 그 뒤에 실제 답 한 줄만 보낸다. "
    "진지 신호(죽음·이별·우울·해고·강한 자기비하)가 보이면 비유·받아치기·펀치라인은 사용하지 않는다."
)


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def load_jsonl(path: Path) -> list[dict]:
    out = []
    with io.open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter", required=True)
    ap.add_argument("--base-model", default=None)
    ap.add_argument("--cases", default=str(EVAL / "cases.jsonl"))
    ap.add_argument("--tag", default="play9")
    ap.add_argument("--max-new-tokens", type=int, default=600)
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--top-p", type=float, default=0.9)
    ap.add_argument("--max-seq-length", type=int, default=1536)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    cases = load_jsonl(Path(args.cases))
    if args.limit > 0:
        cases = cases[: args.limit]
    log(f"cases: n={len(cases)}")

    from unsloth import FastModel
    from unsloth.chat_templates import get_chat_template
    import torch

    adapter_dir = Path(args.adapter)
    meta_path = adapter_dir / "train_meta.json"
    base = args.base_model
    if not base and meta_path.exists():
        with io.open(meta_path, "r", encoding="utf-8") as f:
            base = json.load(f).get("base_model")
    if not base:
        print("FAILED: base_model not given and not in adapter meta", flush=True)
        return 2

    log(f"loading base={base} adapter={adapter_dir}")
    model, tokenizer = FastModel.from_pretrained(
        model_name=str(adapter_dir),
        max_seq_length=args.max_seq_length,
        load_in_4bit=True,
        full_finetuning=False,
        dtype=None,
    )
    tokenizer = get_chat_template(tokenizer, chat_template="gemma-4")
    FastModel.for_inference(model)

    REPORTS.mkdir(exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    out_path = REPORTS / f"run_{args.tag}_{ts}.jsonl"

    started = time.time()
    with io.open(out_path, "w", encoding="utf-8") as f:
        for idx, case in enumerate(cases, 1):
            user_text = case["input"]
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_text},
            ]
            prompt = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True)
            inputs = tokenizer(text=prompt, return_tensors="pt").to(model.device)

            t0 = time.time()
            with torch.no_grad():
                out = model.generate(
                    **inputs,
                    max_new_tokens=args.max_new_tokens,
                    do_sample=True,
                    temperature=args.temperature,
                    top_p=args.top_p,
                    pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
                )
            dt = time.time() - t0
            gen = tokenizer.decode(
                out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)

            thoughts, reply = "", gen.strip()
            if "<think>" in gen and "</think>" in gen:
                thoughts = gen.split("<think>", 1)[1].split("</think>", 1)[0].strip()
                reply = gen.split("</think>", 1)[1].strip()

            row = {
                "case_id": case.get("id"),
                "category": case.get("category"),
                "input": user_text,
                "thoughts": thoughts,
                "reply": reply,
                "raw": gen,
                "latency_s": round(dt, 2),
                "model": f"play9_lora:{adapter_dir.name}",
                "base_model": base,
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            f.flush()
            elapsed = time.time() - started
            eta = elapsed / idx * (len(cases) - idx)
            log(f"  [{idx}/{len(cases)}] {case.get('id')} ({dt:.1f}s, eta {eta/60:.1f}m)")

    log(f"output: {out_path}")
    print("DONE", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
