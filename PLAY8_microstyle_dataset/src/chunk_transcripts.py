"""Step 1: transcripts → 연속 2~3줄 chunk → input 후보.

PLAY6/PLAY7가 단일 utterance를 input으로 썼다면, PLAY8은 사용자 요청대로
"몇 줄 묶어서 대화처럼" 변환한다 — 친구가 톡으로 연달아 보낸 묶음 느낌.

자막은 방송 host 멘트가 섞여 있다. 친근한 톤만 통과시키도록 자동 필터를 둔다:
- 정중 어미("~합니다", "~드립니다", "~바랍니다") 등장 시 제외
- 영상 마케팅 키워드("구독", "좋아요", "오늘 영상") 등장 시 제외
- 너무 짧거나(<10자) 너무 긴(>80자) 묶음 제외
- 한국어 음절 비율 ≥ 70%

Output: data/input_candidates.jsonl
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRANSCRIPTS_DIR = ROOT / "raw_transcripts"
OUT = ROOT / "data" / "input_candidates.jsonl"

KOREAN_RE = re.compile(r"[가-힣]")
ANY_CHAR_RE = re.compile(r"\S")

HOST_ENDINGS = (
    "합니다", "합니다.", "겠습니다", "드립니다", "바랍니다",
    "주십시오", "주세요", "드릴게요", "보세요",
)
MARKETING_KEYS = (
    "구독", "좋아요", "알림 설정", "댓글", "오늘 영상",
    "본 영상", "유튜브", "채널", "시청해", "시청자",
    "여러분", "안녕하세요", "안녕히",
)
FRIENDLY_ENDINGS = (
    "잖아", "거든", "듯", "지?", "지!", "지~",
    "냐?", "냐ㅋ", "ㅋㅋ", "ㅎㅎ", "지 뭐", "야?",
    "야!", "라고", "는데", "는데?", "더라", "더라?",
)


def korean_ratio(s: str) -> float:
    total = len(ANY_CHAR_RE.findall(s))
    if total == 0:
        return 0.0
    return len(KOREAN_RE.findall(s)) / total


def looks_host(text: str) -> bool:
    if any(text.endswith(e) for e in HOST_ENDINGS):
        return True
    if any(k in text for k in MARKETING_KEYS):
        return True
    return False


def looks_friendly(text: str) -> bool:
    return any(text.endswith(e) or e in text for e in FRIENDLY_ENDINGS)


def load_lines(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="utf-8", errors="ignore")
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


def windowed_chunks(lines: list[str], min_size: int, max_size: int):
    """Yield (start_idx, end_idx, joined_text, sublist) for each window."""
    for size in range(min_size, max_size + 1):
        for i in range(len(lines) - size + 1):
            sub = lines[i : i + size]
            joined = " ".join(sub)  # 한 묶음을 자연스럽게 이어붙임
            yield i, i + size, joined, sub


def is_acceptable(joined: str, sub: list[str]) -> tuple[bool, str]:
    if not (10 <= len(joined) <= 80):
        return False, "length"
    if korean_ratio(joined) < 0.6:
        return False, "korean_ratio"
    # 묶음 안 어떤 줄이라도 host 분위기 → 제외
    if any(looks_host(s) for s in sub):
        return False, "host_tone"
    # 친근 어미가 최소 한 줄엔 있어야 friend-tone 통과
    if not any(looks_friendly(s) for s in sub):
        return False, "no_friendly_marker"
    return True, "ok"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-size", type=int, default=2, help="chunk lines minimum")
    ap.add_argument("--max-size", type=int, default=3, help="chunk lines maximum")
    ap.add_argument("--per-source-cap", type=int, default=80)
    ap.add_argument("--total-cap", type=int, default=2000)
    args = ap.parse_args()

    if not TRANSCRIPTS_DIR.exists():
        print(f"FAILED: transcripts not found at {TRANSCRIPTS_DIR}", flush=True)
        return 2

    OUT.parent.mkdir(exist_ok=True)
    picked: list[dict] = []
    seen: set[str] = set()
    per_source: dict[str, int] = defaultdict(int)
    reject_reasons: dict[str, int] = defaultdict(int)

    paths = sorted(p for p in TRANSCRIPTS_DIR.rglob("*.txt") if "backup" not in p.parts)
    print(f"[chunk] scanning {len(paths)} transcripts", flush=True)

    for path in paths:
        if len(picked) >= args.total_cap:
            break
        rel = path.relative_to(ROOT).as_posix()
        lines = load_lines(path)
        for start, end, joined, sub in windowed_chunks(lines, args.min_size, args.max_size):
            if per_source[rel] >= args.per_source_cap:
                break
            if joined in seen:
                continue
            ok, reason = is_acceptable(joined, sub)
            if not ok:
                reject_reasons[reason] += 1
                continue
            # context_after: 그 다음 3줄 (있으면). v4의 "참고 톤".
            ref_after = lines[end : end + 3]
            picked.append(
                {
                    "chunk_id": f"chk_{len(picked) + 1:05d}",
                    "source_path": rel,
                    "start_line": start + 1,
                    "end_line": end,
                    "lines": sub,
                    "input_text": joined,
                    "reference_after": ref_after,
                }
            )
            seen.add(joined)
            per_source[rel] += 1
            if len(picked) >= args.total_cap:
                break

    with OUT.open("w", encoding="utf-8") as f:
        for c in picked:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    print(f"[chunk] wrote {len(picked)} input_candidates → {OUT}", flush=True)
    print(f"[chunk] sources covered: {len(per_source)}", flush=True)
    print(f"[chunk] reject reasons: {dict(reject_reasons)}", flush=True)
    print("DONE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
