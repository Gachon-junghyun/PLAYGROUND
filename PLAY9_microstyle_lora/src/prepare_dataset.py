"""
PLAY8가 만든 final_dataset.chat.jsonl을 train/val로 쪼개고,
토큰 길이 통계를 찍어서 max_seq_length 설정 근거를 만든다.

입력:
  data/final_dataset.chat.jsonl   (1,411건 가정)

출력:
  data/train.jsonl
  data/val.jsonl
  reports/dataset_stats.md

표준 라이브러리만 사용. 토큰 카운트는 char 기준의 거친 근사 (대략 char/2 ≈ token).
정확한 토큰 카운트가 필요하면 train 스크립트가 tokenizer 로드된 뒤 한 번 더 찍는다.
"""
from __future__ import annotations
import argparse
import io
import json
import random
import statistics
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
REPORTS = ROOT / "reports"


def load_chat(path: Path) -> list[dict]:
    items = []
    with io.open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            items.append(json.loads(line))
    return items


def char_len(s: str) -> int:
    return len(s)


def estimate_tokens(s: str) -> int:
    # Gemma sentencepiece 한국어: 대략 char ≈ token (한 글자가 종종 1~2 토큰).
    # 보수적으로 char * 1.3 추정.
    return int(len(s) * 1.3)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=str(DATA / "final_dataset.chat.jsonl"))
    ap.add_argument("--train-out", default=str(DATA / "train.jsonl"))
    ap.add_argument("--val-out", default=str(DATA / "val.jsonl"))
    ap.add_argument("--val-ratio", type=float, default=0.06)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    in_path = Path(args.input)
    if not in_path.exists():
        print(f"FAILED: input not found: {in_path}", flush=True)
        return 2

    items = load_chat(in_path)
    print(f"[load] total={len(items)}", flush=True)

    # 셔플 + split
    rng = random.Random(args.seed)
    rng.shuffle(items)
    n_val = max(1, int(len(items) * args.val_ratio))
    val = items[:n_val]
    train = items[n_val:]
    print(f"[split] train={len(train)} val={len(val)}", flush=True)

    REPORTS.mkdir(exist_ok=True)
    DATA.mkdir(exist_ok=True)

    def dump(path: Path, rows: list[dict]) -> None:
        with io.open(path, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    dump(Path(args.train_out), train)
    dump(Path(args.val_out), val)
    print(f"[write] {args.train_out}", flush=True)
    print(f"[write] {args.val_out}", flush=True)

    # 길이 통계
    sys_lens, user_lens, asst_lens, total_lens = [], [], [], []
    think_lens, reply_lens = [], []
    for it in items:
        msgs = it["messages"]
        s = next((m["content"] for m in msgs if m["role"] == "system"), "")
        u = next((m["content"] for m in msgs if m["role"] == "user"), "")
        a = next((m["content"] for m in msgs if m["role"] == "assistant"), "")
        sys_lens.append(char_len(s))
        user_lens.append(char_len(u))
        asst_lens.append(char_len(a))
        total_lens.append(char_len(s) + char_len(u) + char_len(a))

        if "<think>" in a and "</think>" in a:
            th = a.split("<think>", 1)[1].split("</think>", 1)[0]
            rp = a.split("</think>", 1)[1].lstrip("\n")
            think_lens.append(char_len(th))
            reply_lens.append(char_len(rp))

    def stats(name: str, xs: list[int]) -> str:
        if not xs:
            return f"- **{name}**: (none)"
        xs_sorted = sorted(xs)
        return (
            f"- **{name}**: n={len(xs)}, "
            f"min={xs_sorted[0]}, "
            f"median={statistics.median(xs)}, "
            f"p90={xs_sorted[int(len(xs_sorted) * 0.9)]}, "
            f"p99={xs_sorted[int(len(xs_sorted) * 0.99)]}, "
            f"max={xs_sorted[-1]}"
        )

    p99_total = sorted(total_lens)[int(len(total_lens) * 0.99)]
    est_p99 = estimate_tokens("x" * p99_total)
    recommended_max_seq = max(1024, ((est_p99 + 127) // 128) * 128)  # 128 단위로 올림

    report = [
        "# PLAY9 데이터셋 통계",
        "",
        f"전체 {len(items)}건 → train {len(train)} / val {len(val)} (val_ratio={args.val_ratio}).",
        "",
        "## 문자 길이 (char count)",
        stats("system", sys_lens),
        stats("user (입력 톡)", user_lens),
        stats("assistant (think + reply)", asst_lens),
        stats("think 내용만", think_lens),
        stats("reply 한 줄만", reply_lens),
        stats("system+user+assistant total", total_lens),
        "",
        "## 토큰 길이 추정",
        f"- p99 total char ≈ {p99_total} → token 추정 ≈ {est_p99}",
        f"- **권장 max_seq_length: {recommended_max_seq}**",
        "",
        "## 주의",
        "- 토큰 카운트는 char × 1.3의 거친 추정. 학습 시작 직후 실제 tokenizer로 한 번 더 측정해라.",
        "- p99에 맞추면 1% truncate. p99.9로 맞추거나 패딩 부담이 크면 줄여도 됨.",
    ]
    report_path = REPORTS / "dataset_stats.md"
    with io.open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report) + "\n")
    print(f"[report] {report_path}", flush=True)
    print(f"[recommend] max_seq_length = {recommended_max_seq}", flush=True)
    print("DONE", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
