"""R2a Agent 입력 준비 — 매크로 영역 8 라벨만 조인+필터해서 단일 jsonl로.

목적: Agent가 한 번 또는 두 번의 Read로 처리할 수 있게 사전 분할.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
S1 = ROOT / "data" / "s1_clean.jsonl"
LABELS = ROOT / "data" / "r1_topics.jsonl"
OUT = ROOT / "data" / "r2a_macro_input.jsonl"
OUT_BY_LABEL = ROOT / "data" / "r2a_macro_by_label"

MACRO_LABELS = {
    "fed_policy", "inflation_data", "employment_data", "oil_geopolitics",
    "china_macro", "emerging_markets", "us_equity_market", "korea_economy",
}


def main() -> None:
    # 라벨 인덱스 빌드
    label_idx: dict[str, list[str]] = {}
    for line in LABELS.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        label_idx[r["id"]] = r["labels"]

    # 매크로 라벨이 1개 이상 붙은 명제만 추출
    kept: list[dict] = []
    for line in S1.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        rec_id = f"{rec['video_id']}:{rec['chunk_idx']}:{rec['sentence_idx_in_chunk']}"
        labels = label_idx.get(rec_id, [])
        macro_hit = [l for l in labels if l in MACRO_LABELS]
        if not macro_hit:
            continue
        if labels == ["personal_anecdote"]:  # 안전장치 — 매크로 라벨도 없으니 어차피 안 걸림
            continue
        # 슬림 출력: 카드 합성에 필요한 필드만
        kept.append({
            "id": rec_id,
            "speaker": rec["speaker"],
            "labels": labels,
            "macro_labels": macro_hit,
            "proposition": rec["proposition"],
            "raw_quote": rec["raw_quote"],
            "types": rec.get("types", []),
            "direction": rec.get("direction", ""),
            "time_horizon": rec.get("time_horizon", ""),
            "confidence_level": rec.get("confidence_level", ""),
            "evidence_type": rec.get("evidence_type", ""),
            "evidence_mentioned": rec.get("evidence_mentioned", []),
            "conditions": rec.get("conditions", []),
        })

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        for r in kept:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # 통계
    size_chars = OUT.stat().st_size
    print(f"WROTE {len(kept)} records -> {OUT}")
    print(f"FILE SIZE: {size_chars:,} chars ({size_chars/4:.0f} tokens 추정)")

    # 라벨별 분포 (멀티라벨이라 중복 카운트)
    from collections import Counter
    c = Counter()
    for r in kept:
        for l in r["macro_labels"]:
            c[l] += 1
    print("\n매크로 라벨별 명제 수:")
    for l in sorted(MACRO_LABELS, key=lambda x: -c.get(x, 0)):
        print(f"  {l}: {c.get(l, 0)}")

    # 라벨별 분할 파일 — 큰 라벨용
    OUT_BY_LABEL.mkdir(parents=True, exist_ok=True)
    for label in MACRO_LABELS:
        rows = [r for r in kept if label in r["macro_labels"]]
        if not rows:
            continue
        fp = OUT_BY_LABEL / f"{label}.jsonl"
        with fp.open("w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"  분할 파일: {fp.name} ({len(rows)}건, {fp.stat().st_size:,} chars)")


if __name__ == "__main__":
    main()
