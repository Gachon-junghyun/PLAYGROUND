"""S1: 룰 기반 노이즈 컷. LLM 없음.

입력: HAN_LAB/.../propositions.jsonl (1,060건)
출력: data/s1_clean.jsonl + 콘솔 통계

룰 (README "가정 & 제약" 1번 참조):
1. is_promotional 또는 is_meta_remark → 컷
2. types에 promotion_chatter 있으면 → 컷
3. types에 fact_statement/causal_claim/prediction/conditional_prediction/interpretation 하나도 없으면 → 컷
4. proposition 길이 < 15자 → 컷 (정보 빈약)
5. raw_quote와 proposition의 토큰 jaccard ≥ 0.85 → 동어반복 컷
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SRC = Path(r"C:\Users\fivep\OneDrive\Desktop\HAN_LAB\experiments\insight_pipeline\data\propositions.jsonl")
OUT = Path(__file__).parent / "data" / "s1_clean.jsonl"

KEEP_TYPES = {"fact_statement", "causal_claim", "prediction", "conditional_prediction", "interpretation"}
MIN_PROP_LEN = 15
JACCARD_DUP_THRESHOLD = 0.85

# 한글/영문/숫자 토큰만 (조사·구두점 제거)
TOKEN_RE = re.compile(r"[가-힣A-Za-z0-9]+")


def tokens(text: str) -> set[str]:
    return set(TOKEN_RE.findall(text or ""))


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def classify(r: dict) -> str | None:
    """컷 사유 반환. None이면 통과."""
    if r.get("is_promotional"):
        return "promotional"
    if r.get("is_meta_remark"):
        return "meta_remark_flag"

    types = set(r.get("types", []))
    if "promotion_chatter" in types:
        return "type_promotion"
    if not (types & KEEP_TYPES):
        return "no_useful_type"

    prop = (r.get("proposition") or "").strip()
    if len(prop) < MIN_PROP_LEN:
        return "too_short"

    raw = r.get("raw_quote") or ""
    if jaccard(tokens(raw), tokens(prop)) >= JACCARD_DUP_THRESHOLD:
        return "paraphrase_duplicate"

    return None


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")

    if not SRC.exists():
        print(f"[FAIL] 입력 없음: {SRC}")
        sys.exit(1)

    rows = [json.loads(l) for l in SRC.read_text(encoding="utf-8").splitlines() if l.strip()]
    print(f"[S1] 입력 {len(rows)}건")

    kept: list[dict] = []
    cut_reasons: dict[str, int] = {}
    for r in rows:
        reason = classify(r)
        if reason is None:
            kept.append(r)
        else:
            cut_reasons[reason] = cut_reasons.get(reason, 0) + 1

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        for r in kept:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"[S1] 통과 {len(kept)}건 → {OUT.relative_to(Path.cwd()) if OUT.is_relative_to(Path.cwd()) else OUT}")
    print(f"[S1] 컷 {sum(cut_reasons.values())}건")
    for reason, n in sorted(cut_reasons.items(), key=lambda x: -x[1]):
        print(f"  - {reason}: {n}")

    # 화자별 통과율
    by_ch: dict[str, list[int]] = {}
    for r in rows:
        s = r.get("speaker", "?")
        by_ch.setdefault(s, [0, 0])
        by_ch[s][1] += 1
    for r in kept:
        by_ch[r.get("speaker", "?")][0] += 1
    print("\n[S1] 화자별 통과율:")
    for s, (k, t) in sorted(by_ch.items(), key=lambda x: -x[1][1]):
        print(f"  - {s}: {k}/{t} ({k/t*100:.0f}%)")


if __name__ == "__main__":
    main()
