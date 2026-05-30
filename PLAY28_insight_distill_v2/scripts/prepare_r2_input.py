"""R2 Agent 입력 준비 (일반화) — 영역별 라벨 묶음만 조인+필터해서 슬림 jsonl로.

사용: python prepare_r2_input.py {macro|industry|corporate|meta}
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
S1 = ROOT / "data" / "s1_clean.jsonl"
LABELS = ROOT / "data" / "r1_topics.jsonl"

AREAS = {
    "macro": {
        "fed_policy", "inflation_data", "employment_data", "oil_geopolitics",
        "china_macro", "emerging_markets", "us_equity_market", "korea_economy",
    },
    "industry": {
        "ai_tech", "semiconductor_cycle", "big_tech_earnings",
        "game_industry", "consumer_electronics", "entertainment_content",
        "energy_commodities",
    },
    "corporate": {
        "corporate_earnings", "single_stock_move",
        "startup_business", "brand_strategy",
    },
    "meta": {
        "market_sentiment", "investment_strategy", "risk_factors",
        "geopolitics_general", "analyst_view",
        # personal_anecdote는 단독 라벨이면 제외 (사용자 결정)
    },
}


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in AREAS:
        print(f"Usage: python {sys.argv[0]} {{{'/'.join(AREAS)}}}")
        sys.exit(1)

    area = sys.argv[1]
    target_labels = AREAS[area]
    out_combined = ROOT / "data" / f"r2{area[0]}_{area}_input.jsonl"
    out_by_label = ROOT / "data" / f"r2{area[0]}_{area}_by_label"

    # 라벨 인덱스
    label_idx: dict[str, list[str]] = {}
    for line in LABELS.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        label_idx[r["id"]] = r["labels"]

    # 영역 라벨 매칭 명제만
    kept: list[dict] = []
    for line in S1.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        rec_id = f"{rec['video_id']}:{rec['chunk_idx']}:{rec['sentence_idx_in_chunk']}"
        labels = label_idx.get(rec_id, [])
        area_hit = [l for l in labels if l in target_labels]
        if not area_hit:
            continue
        if labels == ["personal_anecdote"]:
            continue
        kept.append({
            "id": rec_id,
            "speaker": rec["speaker"],
            "labels": labels,
            "area_labels": area_hit,
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

    out_combined.parent.mkdir(parents=True, exist_ok=True)
    with out_combined.open("w", encoding="utf-8") as f:
        for r in kept:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"AREA: {area}")
    print(f"WROTE {len(kept)} records -> {out_combined.name}")
    print(f"FILE SIZE: {out_combined.stat().st_size:,} chars (~{out_combined.stat().st_size//4} tokens)")

    from collections import Counter
    c = Counter()
    for r in kept:
        for l in r["area_labels"]:
            c[l] += 1
    print(f"\n{area} 라벨별 명제 수:")
    for l in sorted(target_labels, key=lambda x: -c.get(x, 0)):
        print(f"  {l}: {c.get(l, 0)}")

    out_by_label.mkdir(parents=True, exist_ok=True)
    print("\n라벨별 분할 파일:")
    for label in target_labels:
        rows = [r for r in kept if label in r["area_labels"]]
        if not rows:
            continue
        fp = out_by_label / f"{label}.jsonl"
        with fp.open("w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        sz = fp.stat().st_size
        print(f"  {fp.name}: {len(rows)}건, {sz:,} chars (~{sz//4} tokens)")


if __name__ == "__main__":
    main()
