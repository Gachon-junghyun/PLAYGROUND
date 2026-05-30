"""R4 신규 카드 자동 템플릿 검출 (PLAY28 v2 incremental).

검사 대상: data/r4_cards_new/*.jsonl (A7~A10 batch).
출력: data/r4_audit_new.md

7개 금지 패턴 + framework 사전 완전일치 — prompts/r4_reverse_distill.md §Step 6 동일.
"""
from __future__ import annotations
import json, re
from pathlib import Path

ROOT = Path(__file__).parent.parent
R4_CARDS_DIR = ROOT / "data" / "r4_cards_new"
REV_DIST_FILE = ROOT / "data" / "reverse_distillation_cards.json"
OUT_FILE = ROOT / "data" / "r4_audit_new.md"

PATTERNS = [
    ("P1_표면신호", re.compile(r"라는 표면 신호가 실제로는")),
    ("P2_조건부전이", re.compile(r"로 이어지는 조건부 전이 신호인지 확인한다")),
    ("P3_왜지금", re.compile(r"왜 지금 ['\"][^'\"]+['\"]가 나타났고, 어떤 조건에서")),
    ("P4_호재악재판정", re.compile(r"원초 신호를 곧바로 호재/악재로 판정하지 않고")),
    ("P5_1차2차분리", re.compile(r"1차 영향과 2차 수혜/피해 대상을 분리한다")),
    ("P6_기존사고점프", re.compile(r"카드의 기존 사고 점프는")),
]
CHECK_FIELDS = ["attention_hook", "implicit_question", "reasoning_move", "matched_thinking_pattern"]


def load_framework_definitions() -> set[str]:
    if not REV_DIST_FILE.exists():
        return set()
    data = json.loads(REV_DIST_FILE.read_text(encoding="utf-8"))
    return {c["matched_thinking_pattern"].strip()
            for c in data.get("cards", [])
            if c.get("matched_thinking_pattern")}


def audit_card(card: dict, framework_defs: set[str]) -> list[tuple[str, str, str]]:
    violations: list[tuple[str, str, str]] = []
    for field in CHECK_FIELDS:
        text = card.get(field, "")
        if not isinstance(text, str):
            continue
        for pid, pat in PATTERNS:
            m = pat.search(text)
            if m:
                violations.append((field, pid, m.group(0)))
        if field == "matched_thinking_pattern" and text.strip() in framework_defs:
            violations.append((field, "P7_framework복붙", text.strip()))
    return violations


def main() -> None:
    framework_defs = load_framework_definitions()
    print(f"framework 사전 정의: {len(framework_defs)}개")

    if not R4_CARDS_DIR.exists():
        print(f"[err] {R4_CARDS_DIR} 없음. Agent 호출 먼저.")
        return

    batches: list[tuple[str, list[dict]]] = []
    for fp in sorted(R4_CARDS_DIR.glob("*.jsonl")):
        cards = []
        for line in fp.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                cards.append(json.loads(line))
            except json.JSONDecodeError as e:
                cards.append({"_parse_error": str(e), "_raw": line[:100]})
        batches.append((fp.stem, cards))

    total_cards = sum(len(c) for _, c in batches)
    parse_errors = sum(1 for _, cards in batches for c in cards if "_parse_error" in c)

    all_violations: list[tuple[str, str, list[tuple[str, str, str]]]] = []
    for batch_name, cards in batches:
        for c in cards:
            if "_parse_error" in c:
                all_violations.append((batch_name, "PARSE_ERROR", [("_", "JSON", c.get("_raw", ""))]))
                continue
            vios = audit_card(c, framework_defs)
            if vios:
                all_violations.append((batch_name, c.get("card_id", "?"), vios))

    lines = [
        "# R4 신규 카드 자동 템플릿 검출 보고 (PLAY28 v2)",
        "",
        f"- 총 카드 수: **{total_cards}**",
        f"- JSON 파싱 에러: {parse_errors}",
        f"- framework 사전 정의 set 크기: {len(framework_defs)}",
        f"- 위반 카드 수: **{len(all_violations)}**",
        "",
        "## Batch별 카드 수",
        "",
        "| Batch | 카드 |",
        "|---|---:|",
    ]
    for batch_name, cards in batches:
        lines.append(f"| {batch_name} | {len(cards)} |")
    lines.append("")
    if not all_violations:
        lines.append("## 결과: 위반 0건 ✅")
    else:
        lines.append("## 위반 상세")
        lines.append("")
        for batch_name, card_id, vios in all_violations:
            lines.append(f"### {batch_name} / {card_id}")
            for field, pid, matched in vios:
                lines.append(f"- `{field}` → **{pid}** : `{matched[:80]}`")
            lines.append("")

    OUT_FILE.write_text("\n".join(lines), encoding="utf-8")
    print(f"audit 완료 → {OUT_FILE}")
    print(f"위반: {len(all_violations)}건, 카드 {total_cards}장 중")


if __name__ == "__main__":
    main()
