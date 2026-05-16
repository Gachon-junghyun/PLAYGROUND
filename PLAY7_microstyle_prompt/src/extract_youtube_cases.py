"""Extract evaluation cases from PLAY7's own youtube_whisper/transcripts/*.txt.

PLAY7 is self-contained — does NOT depend on PLAY6. The transcript files
were placed inside PLAY7/youtube_whisper/ by the user so this PLAY can
build its own cases independently.

Output: eval/cases_youtube.jsonl  (one case per line, PLAY7 case format)

Each case is one short Korean utterance that looks like a real
micro-reaction, plus 2-3 lines of preceding context for the human reader.
Expected labels are None (no ground truth on real transcripts).
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent
TRANSCRIPTS_DIR = ROOT / "youtube_whisper" / "transcripts"
OUT = ROOT / "eval" / "cases_youtube.jsonl"

KOREAN_RE = re.compile(r"[가-힣ㄱ-ㅎㅏ-ㅣ]")
REPEAT_RE = re.compile(r"(.)\1{4,}")  # 5+ identical chars in a row


def looks_like_micro_reaction(line: str) -> bool:
    """Heuristic: a short Korean utterance that could be a friend's tone-setting reply."""
    s = line.strip()
    if not (5 <= len(s) <= 30):
        return False
    if not KOREAN_RE.search(s):
        return False
    if REPEAT_RE.search(s):
        return False
    # has at least one Korean syllable cluster
    if len(KOREAN_RE.findall(s)) < 3:
        return False
    return True


def iter_transcripts(transcripts_dir: Path):
    """Yield (source_relpath, [non-empty lines]) for each *.txt under transcripts_dir.

    Skips backup/ folder — that's the user's archive, not the working set.
    """
    for path in sorted(transcripts_dir.rglob("*.txt")):
        if "backup" in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = path.read_text(encoding="utf-8", errors="ignore")
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        if lines:
            yield path.relative_to(ROOT).as_posix(), lines


def pick_cases(target_n: int, per_source_cap: int) -> list[dict]:
    picked: list[dict] = []
    seen_utts: set[str] = set()
    per_source: dict[str, int] = defaultdict(int)

    for relpath, lines in iter_transcripts(TRANSCRIPTS_DIR):
        for i, line in enumerate(lines):
            if len(picked) >= target_n:
                return picked
            if per_source[relpath] >= per_source_cap:
                break
            if not looks_like_micro_reaction(line):
                continue
            if line in seen_utts:
                continue
            ctx_before = lines[max(0, i - 3) : i]
            ctx_after = lines[i + 1 : i + 4]
            if len(ctx_before) < 2:
                continue
            picked.append(
                {
                    "id": f"YT-{len(picked) + 1:02d}",
                    "category": "youtube_real",
                    "input": line,
                    "expected_humor_level": None,
                    "expected_risk": None,
                    "expected_function": None,
                    "note": "PLAY7 자체 transcripts에서 추출한 실제 화자 발화",
                    "source": {
                        "source_path": relpath,
                        "line_number": i + 1,
                        "context_before": ctx_before,
                        "context_after": ctx_after,
                    },
                }
            )
            seen_utts.add(line)
            per_source[relpath] += 1
    return picked


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=30, help="target number of cases")
    ap.add_argument("--per-source", type=int, default=5, help="cap per transcript file")
    args = ap.parse_args()

    if not TRANSCRIPTS_DIR.exists():
        print(f"FAILED: transcripts dir not found at {TRANSCRIPTS_DIR}", flush=True)
        return 2

    cases = pick_cases(args.n, args.per_source)
    OUT.parent.mkdir(exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        for case in cases:
            f.write(json.dumps(case, ensure_ascii=False) + "\n")

    src_dist = defaultdict(int)
    for c in cases:
        src_dist[c["source"]["source_path"]] += 1

    print(f"[extract] wrote {len(cases)} cases → {OUT}", flush=True)
    print(f"[extract] from {len(src_dist)} transcript files:", flush=True)
    for src, n in src_dist.items():
        print(f"  - {src}: {n}", flush=True)
    print("DONE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
