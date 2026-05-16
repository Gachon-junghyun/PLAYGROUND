"""Step 4: filtered triples → final SFT-ready dataset + 통계 리포트.

HuggingFace SFT 형식 두 가지 변형으로 출력:
  - chat: messages 배열 (system / user / assistant)
  - dual: input → assistant가 thoughts + reply 한 시퀀스로 출력하는 학습 포맷
    (Phase 4 LoRA가 "답변 전 사고하는 습관"을 익히게 하는 핵심)

Output:
  - data/final_dataset.chat.jsonl
  - data/final_dataset.dual.jsonl
  - reports/summary.md
"""
from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "triples.filtered.jsonl"
OUT_CHAT = ROOT / "data" / "final_dataset.chat.jsonl"
OUT_DUAL = ROOT / "data" / "final_dataset.dual.jsonl"
REPORT = ROOT / "reports" / "summary.md"

SYSTEM_PROMPT = (
    "너는 친구의 톡을 받고 머릿속으로 어떻게 답할지 한 번 굴린 뒤 답하는 한국어 화자다. "
    "먼저 <think>...</think> 안에 자연스러운 자기 사고를 적고, 그 뒤에 실제 답 한 줄만 보낸다. "
    "진지 신호(죽음·이별·우울·해고·강한 자기비하)가 보이면 비유·받아치기·펀치라인은 사용하지 않는다."
)


def to_chat(r: dict) -> dict:
    """OpenAI-style messages. assistant 메시지는 thoughts+reply를 <think> 태그로 묶은 것."""
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": r["input"]},
            {
                "role": "assistant",
                "content": f"<think>\n{r['thoughts'].strip()}\n</think>\n{r['reply'].strip()}",
            },
        ],
        "meta": {
            "chunk_id": r.get("chunk_id"),
            "source_path": r.get("source_path"),
            "model": r.get("model"),
        },
    }


def to_dual(r: dict) -> dict:
    """완전 평탄화 — prompt → completion 한 시퀀스 (TRL SFTTrainer 호환)."""
    completion = f"<think>\n{r['thoughts'].strip()}\n</think>\n{r['reply'].strip()}"
    return {
        "prompt": r["input"],
        "completion": completion,
        "meta": {
            "chunk_id": r.get("chunk_id"),
            "source_path": r.get("source_path"),
            "model": r.get("model"),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=str(SRC))
    args = ap.parse_args()
    in_path = Path(args.input)
    if not in_path.exists():
        print(f"FAILED: {in_path} missing — run filter_quality.py first", flush=True)
        return 2

    OUT_CHAT.parent.mkdir(exist_ok=True)
    REPORT.parent.mkdir(exist_ok=True)

    rows = [json.loads(l) for l in in_path.open("r", encoding="utf-8") if l.strip()]
    if not rows:
        print("FAILED: no rows in input", flush=True)
        return 2

    with OUT_CHAT.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(to_chat(r), ensure_ascii=False) + "\n")
    with OUT_DUAL.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(to_dual(r), ensure_ascii=False) + "\n")

    # 통계
    thought_lens = [len(r["thoughts"]) for r in rows]
    reply_lens = [len(r["reply"]) for r in rows]
    by_source = Counter(r.get("source_path", "?") for r in rows)
    by_model = Counter(r.get("model", "?") for r in rows)

    lines = [
        "# PLAY8 Final Dataset Summary",
        "",
        f"- **Triples**: {len(rows)}",
        f"- **Source videos**: {len(by_source)}",
        f"- **Generator models**: {dict(by_model)}",
        "",
        "## Length distribution",
        "",
        f"| Field | min | median | mean | max |",
        f"|---|---|---|---|---|",
        f"| thoughts (chars) | {min(thought_lens)} | {statistics.median(thought_lens):.0f} | {statistics.mean(thought_lens):.0f} | {max(thought_lens)} |",
        f"| reply (chars)    | {min(reply_lens)} | {statistics.median(reply_lens):.0f} | {statistics.mean(reply_lens):.0f} | {max(reply_lens)} |",
        "",
        "## Per-source counts",
        "",
    ]
    for src, n in by_source.most_common():
        lines.append(f"- `{src}`: {n}")
    lines += [
        "",
        "## Sample (first 3 triples)",
        "",
    ]
    for r in rows[:3]:
        lines.append(f"### chunk_id `{r.get('chunk_id')}`")
        lines.append(f"- **input**: {r['input']}")
        lines.append(f"- **thoughts**: {r['thoughts']}")
        lines.append(f"- **reply**: {r['reply']}")
        lines.append("")
    lines += [
        "## Output files",
        "",
        f"- `{OUT_CHAT.relative_to(ROOT).as_posix()}` — OpenAI chat 포맷 (system/user/assistant)",
        f"- `{OUT_DUAL.relative_to(ROOT).as_posix()}` — TRL SFTTrainer 호환 prompt/completion 포맷",
        "",
        "두 포맷 모두 assistant/completion 안에 `<think>...</think>` 태그로 사고를 포함한다.",
        "LoRA 학습 시 모델이 \"답변 전 한 번 사고하는 습관\" 자체를 익히게 된다.",
    ]
    REPORT.write_text("\n".join(lines), encoding="utf-8")

    print(f"[build] {len(rows)} triples → {OUT_CHAT.name} + {OUT_DUAL.name}", flush=True)
    print(f"[build] report → {REPORT.relative_to(ROOT).as_posix()}", flush=True)
    print("DONE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
