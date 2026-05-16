"""
PLAY9 — Unsloth 기반 QLoRA 4-bit 학습 (Gemma 4 E4B + 1,411 트리플).

베이스: unsloth/gemma-4-E4B-it (unsloth 사전 양자화). google/gemma-4-E4B-it도 가능.

전제 (디스패치 부적합 → 사용자가 별도 PowerShell에서):
  0. PyTorch + torchvision (CUDA 12.x) 설치 끝.
  1. pip install unsloth  ← Unsloth가 transformers/peft/trl/bnb 호환 버전 자동 관리.
  2. Hugging Face 토큰 (Gemma 라이센스 동의 후).

권장:
  $env:PYTHONUTF8 = "1"
  python -u src/train_qlora.py > train.log 2>&1
"""
from __future__ import annotations
import argparse
import io
import json
import os
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def load_jsonl(path: Path) -> list[dict]:
    items = []
    with io.open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            items.append(json.loads(line))
    return items


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-model", default="unsloth/gemma-4-E2B-it",
                    help="기본 E2B (10GB GPU 안전). E4B는 16GB+ 필요. "
                         "VRAM 16GB+ 환경이면 --base-model unsloth/gemma-4-E4B-it.")
    ap.add_argument("--train-file", default=str(DATA / "train.jsonl"))
    ap.add_argument("--val-file", default=str(DATA / "val.jsonl"))
    ap.add_argument("--output-dir", default=str(ROOT / "ckpt"))
    ap.add_argument("--max-seq-length", type=int, default=1536)
    ap.add_argument("--epochs", type=float, default=3.0)
    ap.add_argument("--batch-size", type=int, default=1)
    ap.add_argument("--grad-accum", type=int, default=8)
    ap.add_argument("--learning-rate", type=float, default=2e-4)
    ap.add_argument("--warmup-ratio", type=float, default=0.03)
    ap.add_argument("--lora-r", type=int, default=16)
    ap.add_argument("--lora-alpha", type=int, default=16)
    ap.add_argument("--lora-dropout", type=float, default=0.0)
    ap.add_argument("--seed", type=int, default=3407)
    ap.add_argument("--smoke", action="store_true",
                    help="20 step만 돌려서 환경 검증.")
    ap.add_argument("--resume", action="store_true")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    log(f"args: base={args.base_model} smoke={args.smoke} epochs={args.epochs}")

    # === 1. 환경 ===
    try:
        # Unsloth must be imported BEFORE transformers/peft/trl.
        from unsloth import FastModel
        from unsloth.chat_templates import get_chat_template, train_on_responses_only

        import torch
        import transformers, peft, trl, accelerate, bitsandbytes, unsloth
        from transformers import BitsAndBytesConfig
        from datasets import Dataset
        from trl import SFTTrainer, SFTConfig

        log(f"versions: torch={torch.__version__} unsloth={unsloth.__version__} "
            f"transformers={transformers.__version__} trl={trl.__version__} "
            f"peft={peft.__version__} accelerate={accelerate.__version__} "
            f"bitsandbytes={bitsandbytes.__version__}")
        if not torch.cuda.is_available():
            print("FAILED: CUDA not available", flush=True)
            return 2
        log(f"gpu: {torch.cuda.get_device_name(0)} "
            f"({torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB)")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"FAILED: import error: {e}", flush=True)
        return 2

    # === 2. 데이터 ===
    train_rows = load_jsonl(Path(args.train_file))
    val_rows = load_jsonl(Path(args.val_file))
    if args.smoke:
        train_rows = train_rows[:32]
        val_rows = val_rows[:8]
    log(f"data: train={len(train_rows)} val={len(val_rows)}")

    # === 3. 모델 + 토크나이저 (Unsloth가 한 번에) ===
    # 10GB GPU 안전선: E2B (Effective 2B) 4bit ≈ 1.5GB + 활성값/optim ≈ 3-4GB peak.
    log(f"loading: {args.base_model} (4bit)")
    model, tokenizer = FastModel.from_pretrained(
        model_name=args.base_model,
        max_seq_length=args.max_seq_length,
        load_in_4bit=True,
        full_finetuning=False,
        dtype=None,
    )
    log(f"model loaded. vram alloc: {torch.cuda.memory_allocated() / 1e9:.2f} GB")

    # === 4. LoRA 어댑터 (text-only, no vision/audio) ===
    model = FastModel.get_peft_model(
        model,
        finetune_vision_layers=False,
        finetune_language_layers=True,
        finetune_attention_modules=True,
        finetune_mlp_modules=True,
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        bias="none",
        random_state=args.seed,
    )
    log("LoRA adapter added.")

    # === 5. Chat template (Gemma 4) ===
    tokenizer = get_chat_template(tokenizer, chat_template="gemma-4")

    # === 6. 데이터셋 포맷: messages → text (chat template 적용) ===
    def to_text(rows: list[dict]) -> Dataset:
        out_rows = []
        for r in rows:
            text = tokenizer.apply_chat_template(
                r["messages"], tokenize=False, add_generation_prompt=False,
            ).removeprefix("<bos>")
            out_rows.append({"text": text})
        return Dataset.from_list(out_rows)

    train_ds = to_text(train_rows)
    val_ds = to_text(val_rows)
    log(f"chat-templated. sample[:200]: {train_ds[0]['text'][:200]!r}")

    # 토큰 길이 측정 (Gemma 4 multimodal processor 호환: text= 명시)
    try:
        sample_lens = [len(tokenizer(text=train_ds[i]["text"])["input_ids"])
                       for i in range(min(8, len(train_ds)))]
        log(f"sample token lens: max={max(sample_lens)} avg={sum(sample_lens) // len(sample_lens)}")
    except Exception as e:
        log(f"(token length probe skipped: {e})")

    # === 7. Trainer ===
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    max_steps = 20 if args.smoke else -1
    save_steps = 10 if args.smoke else 200
    eval_steps = 10 if args.smoke else 100
    logging_steps = 1 if args.smoke else 10

    sft_config = SFTConfig(
        output_dir=str(out_dir),
        num_train_epochs=args.epochs,
        max_steps=max_steps,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.learning_rate,
        warmup_ratio=args.warmup_ratio,
        lr_scheduler_type="cosine",
        optim="adamw_8bit",
        weight_decay=0.001,
        bf16=True,
        max_seq_length=args.max_seq_length,
        dataset_text_field="text",
        packing=False,
        logging_steps=logging_steps,
        save_steps=save_steps,
        eval_steps=eval_steps,
        eval_strategy="steps",
        save_strategy="steps",
        save_total_limit=3,
        load_best_model_at_end=False,
        report_to="none",
        seed=args.seed,
        dataloader_num_workers=0,
        remove_unused_columns=False,
    )

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        args=sft_config,
    )

    # assistant 응답에만 loss (사용자 입력 마스킹)
    trainer = train_on_responses_only(
        trainer,
        instruction_part="<|turn>user\n",
        response_part="<|turn>model\n",
    )
    log("trainer ready (responses-only loss).")

    # === 8. 학습 ===
    log("training start")
    try:
        result = trainer.train(resume_from_checkpoint=args.resume or None)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"FAILED: train error: {e}", flush=True)
        return 1
    log(f"training done. metrics: {result.metrics}")

    # === 9. adapter 저장 ===
    final_dir = out_dir / ("smoke_final" if args.smoke else "final")
    model.save_pretrained(str(final_dir))
    tokenizer.save_pretrained(str(final_dir))
    log(f"adapter saved → {final_dir}")

    meta = {
        "base_model": args.base_model,
        "epochs": args.epochs,
        "train_size": len(train_rows),
        "val_size": len(val_rows),
        "max_seq_length": args.max_seq_length,
        "lora_r": args.lora_r,
        "lora_alpha": args.lora_alpha,
        "metrics": result.metrics,
        "smoke": args.smoke,
        "framework": "unsloth",
    }
    with io.open(final_dir / "train_meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print("DONE", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
