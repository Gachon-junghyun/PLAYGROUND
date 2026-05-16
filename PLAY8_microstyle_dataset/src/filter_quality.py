"""Step 3: raw triples → filtered triples.

자동 품질 필터. 사람 검수 전에 명백히 망가진 트리플만 거른다:
  - thoughts/reply 비어 있음
  - reply 길이 너무 짧음(<3) 또는 너무 김(>120)
  - reply에 이모지 (Speaker prompt 규칙 위반)
  - reply 한국어 비율 < 60%
  - thoughts에 prompt template 누설 ("→ 짧게" 외 메타 키워드 다수)
  - reply == input (회피)

Output: data/triples.filtered.jsonl + data/triples.rejected.jsonl
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "triples.raw.jsonl"
OK = ROOT / "data" / "triples.filtered.jsonl"
BAD = ROOT / "data" / "triples.rejected.jsonl"

EMOJI_RE = re.compile(
    r"[\U0001F300-\U0001FAFF\U0001F600-\U0001F64F\U0001F900-\U0001F9FF"
    r"☀-➿\U0001F680-\U0001F6FF]"
)
KOREAN_RE = re.compile(r"[가-힣]")
ANY_RE = re.compile(r"\S")


def korean_ratio(s: str) -> float:
    total = len(ANY_RE.findall(s))
    if total == 0:
        return 0.0
    return len(KOREAN_RE.findall(s)) / total


def classify(r: dict) -> tuple[bool, str]:
    if "error" in r:
        return False, "generation_error"
    thoughts = (r.get("thoughts") or "").strip()
    reply = (r.get("reply") or "").strip()
    if not thoughts:
        return False, "empty_thoughts"
    if not reply:
        return False, "empty_reply"
    if len(reply) < 3:
        return False, "reply_too_short"
    if len(reply) > 120:
        return False, "reply_too_long"
    if EMOJI_RE.search(reply):
        return False, "reply_has_emoji"
    if korean_ratio(reply) < 0.4:
        return False, "reply_low_korean"
    if reply == r.get("input", ""):
        return False, "reply_equals_input"
    if len(thoughts) < 40:
        return False, "thoughts_too_short"
    # thoughts에 명백한 프롬프트 누설 검사 (sample header 토큰들)
    if "친구의 톡을 받고" in thoughts or "한국어 내면 독백" in thoughts:
        return False, "thoughts_prompt_leak"
    return True, "ok"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=str(RAW))
    args = ap.parse_args()

    in_path = Path(args.input)
    if not in_path.exists():
        print(f"FAILED: {in_path} missing", flush=True)
        return 2

    OK.parent.mkdir(exist_ok=True)
    stats = Counter()
    with in_path.open("r", encoding="utf-8") as f, \
         OK.open("w", encoding="utf-8") as g, \
         BAD.open("w", encoding="utf-8") as b:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            ok, reason = classify(r)
            stats[reason] += 1
            r["filter_reason"] = reason
            if ok:
                g.write(json.dumps(r, ensure_ascii=False) + "\n")
            else:
                b.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"[filter] total={sum(stats.values())}", flush=True)
    for reason, n in stats.most_common():
        print(f"  {reason}: {n}", flush=True)
    print(f"[filter] kept → {OK}", flush=True)
    print(f"[filter] rejected → {BAD}", flush=True)
    print("DONE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
