"""
학습된 LoRA adapter로 단일 입력에 추론 (Unsloth 기반).

사용:
  python -u src/infer.py --adapter ckpt/final --input-file input.txt
"""
from __future__ import annotations
import argparse
import io
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent

SYSTEM_PROMPT = (
    "너는 친구의 톡을 받고 머릿속으로 어떻게 답할지 한 번 굴린 뒤 답하는 한국어 화자다. "
    "먼저 <think>...</think> 안에 자연스러운 자기 사고를 적고, 그 뒤에 실제 답 한 줄만 보낸다. "
    "진지 신호(죽음·이별·우울·해고·강한 자기비하)가 보이면 비유·받아치기·펀치라인은 사용하지 않는다."
)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter", required=True, help="LoRA adapter 디렉토리")
    ap.add_argument("--base-model", default=None,
                    help="베이스 모델. 미지정 시 adapter/train_meta.json에서 읽음.")
    ap.add_argument("--input", default=None)
    ap.add_argument("--input-file", default=None)
    ap.add_argument("--max-new-tokens", type=int, default=600)
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--top-p", type=float, default=0.9)
    ap.add_argument("--max-seq-length", type=int, default=1536)
    return ap.parse_args()


def read_input(args) -> str:
    if args.input_file:
        return Path(args.input_file).read_text(encoding="utf-8").strip()
    if args.input:
        return args.input
    print("FAILED: --input or --input-file required", flush=True)
    sys.exit(2)


def main() -> int:
    args = parse_args()
    user_text = read_input(args)

    # Unsloth는 다른 라이브러리들보다 먼저 import해야 함
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
        print("FAILED: base_model not given and not in train_meta.json", flush=True)
        return 2

    print(f"[load] base={base} adapter={adapter_dir}", flush=True)

    # adapter 로딩: FastModel.from_pretrained에 adapter dir 직접 줘도 unsloth가 base를 train_meta에서 추출.
    # 안전하게 base 먼저 로드 후 adapter 붙임.
    model, tokenizer = FastModel.from_pretrained(
        model_name=str(adapter_dir),       # adapter 디렉토리 (안에 adapter_config.json 있음)
        max_seq_length=args.max_seq_length,
        load_in_4bit=True,
        full_finetuning=False,
        dtype=None,
    )
    tokenizer = get_chat_template(tokenizer, chat_template="gemma-4")
    FastModel.for_inference(model)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_text},
    ]
    prompt = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text=prompt, return_tensors="pt").to(model.device)

    print(f"[input] {user_text}", flush=True)
    with torch.no_grad():
        out = model.generate(
            **inputs,
            max_new_tokens=args.max_new_tokens,
            do_sample=True,
            temperature=args.temperature,
            top_p=args.top_p,
            pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
        )
    gen = tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)

    thoughts, reply = "", gen.strip()
    if "<think>" in gen and "</think>" in gen:
        thoughts = gen.split("<think>", 1)[1].split("</think>", 1)[0].strip()
        reply = gen.split("</think>", 1)[1].strip()

    print("\n=== 사고 ===", flush=True)
    print(thoughts or "(no think block)", flush=True)
    print("\n=== 답변 ===", flush=True)
    print(reply, flush=True)
    print("\n=== JSON ===", flush=True)
    print(json.dumps({"input": user_text, "thoughts": thoughts, "reply": reply, "raw": gen},
                     ensure_ascii=False), flush=True)
    print("\nDONE", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
