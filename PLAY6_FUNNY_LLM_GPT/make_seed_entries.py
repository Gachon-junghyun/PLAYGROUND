from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


BASE = Path(__file__).resolve().parent
DATA_DIR = BASE / "data"


def stable_id(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


def load_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def compact_context(candidate: dict) -> str:
    before = candidate.get("context_before") or []
    after = candidate.get("context_after") or []
    parts = []
    if before:
        parts.append(before[-1])
    parts.append(candidate["utterance"])
    if after:
        parts.append(after[0])
    return " / ".join(parts)


def usable_when(entry_type: str, funcs: list[str], devices: list[str]) -> list[str]:
    items: list[str] = []
    if entry_type == "micro_reaction":
        items.append("상대 말에 짧게 반응하면서 대화를 살리고 싶을 때")
    if entry_type == "humor_device":
        items.append("평범한 이야기에 말맛이나 웃음 포인트를 붙이고 싶을 때")
    if entry_type == "social_judgment":
        items.append("관계 거리나 부담감을 먼저 살펴야 하는 대화에서")
    if entry_type == "conversation_move":
        items.append("대화가 끊기지 않게 질문이나 전환을 넣고 싶을 때")
    if "위로" in funcs or "수습" in funcs:
        items.append("가벼운 민망함이나 실수를 부드럽게 넘길 때")
    if "질문" in devices:
        items.append("상대가 더 말할 여지를 열어두고 싶을 때")
    return items or ["가벼운 캐주얼 대화에서 말맛을 더하고 싶을 때"]


def avoid_when(risk: str, devices: list[str]) -> list[str]:
    items = ["상대가 진지하게 사과하거나 실제로 힘든 일을 말하는 상황"]
    if risk == "high":
        items.append("친밀도가 낮거나 사적인 정보가 걸린 상황")
    if "과장" in devices or "능청" in devices:
        items.append("상대가 놀림으로 받아들일 수 있는 상황")
    return items


def rewrite_templates(utterance: str, entry_type: str, devices: list[str]) -> list[str]:
    if entry_type == "micro_reaction":
        return [
            "아 이거 살짝 웃긴데?",
            "잠깐만, 흐름이 이상하게 재밌어졌는데?",
            "오케이. 일단 이건 메모할 만함."
        ]
    if "완곡화" in devices:
        return [
            "그 질문은 조금 넓게 물어보는 게 좋겠다.",
            "정확히 캐묻기보단 방향만 살짝 물어보는 느낌.",
            "이건 직진보다 완만한 커브가 맞음."
        ]
    if "묘사" in devices:
        return [
            "그냥 설명하지 말고 장면을 한 번 틀어줘야 함.",
            "이건 대사로 보여주면 바로 살아남.",
            "머릿속에 화면이 켜지게 말하는 쪽."
        ]
    if "반전" in devices:
        return [
            "앞에서는 평범하게 깔고 마지막에 살짝 꺾는다.",
            "정상 루트인 척하다가 끝에서 방향을 바꾼다.",
            "방점은 마지막에 숨겨두는 게 맛있음."
        ]
    return [
        "이건 말 자체보다 타이밍이 중요한 타입.",
        "상대 말의 핵심을 받은 다음 한 박자 짧게 던진다.",
        "길게 설명하지 말고 한 문장으로 정리한다."
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Create rough seed entries from heuristic candidates.")
    parser.add_argument("--input", type=Path, default=DATA_DIR / "microstyle_candidates.jsonl")
    parser.add_argument("--output", type=Path, default=DATA_DIR / "seed_microstyle_entries.jsonl")
    parser.add_argument("--limit", type=int, default=250)
    parser.add_argument("--min-score", type=int, default=8)
    args = parser.parse_args()

    if not args.input.exists():
        raise SystemExit("Candidate file not found. Run: python build_microstyle_db.py")

    candidates = load_jsonl(args.input)
    selected = [c for c in candidates if c["score"] >= args.min_score][:args.limit]
    entries = []
    for c in selected:
        tags = c.get("tags", {})
        devices = tags.get("style_devices", [])
        funcs = tags.get("reply_functions", [])
        risk = tags.get("risk", "low")
        entry_id = f"entry_{stable_id(c['candidate_id'] + c['utterance'])}"
        entries.append(
            {
                "entry_id": entry_id,
                "entry_type": c["candidate_type"],
                "utterance": c["utterance"],
                "context": compact_context(c),
                "social_function": funcs,
                "style_devices": devices,
                "usable_when": usable_when(c["candidate_type"], funcs, devices),
                "avoid_when": avoid_when(risk, devices),
                "rewrite_templates": rewrite_templates(c["utterance"], c["candidate_type"], devices),
                "quality_notes": "휴리스틱 초벌 entry. LLM annotator 또는 사람 검수 필요.",
                "source": {
                    "candidate_id": c["candidate_id"],
                    "source_path": c["source_path"],
                    "line_number": c["line_number"],
                    "score": c["score"],
                },
            }
        )

    write_jsonl(args.output, entries)
    print(f"[OK] seed entries: {len(entries)} -> {args.output}")


if __name__ == "__main__":
    main()
