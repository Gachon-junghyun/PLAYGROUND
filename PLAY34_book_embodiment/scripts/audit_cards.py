"""카드 품질 감사 — 카드가 '뻔한 말'이거나 발동 불가 상태인지 검출.

PLAY13 r4_audit_templates.py 패턴 차용(자체 포함). 외부 의존 없음.

검사 규칙:
  R1  idea 카드인데 trigger_when 비었음        → 발동 불가(deployment 핵심 위반).
  R2  novel 카드인데 review != None            → 범주 오류(소설을 SRS에 태움).
  R3  reframe 가 너무 짧음(<15자) 또는 비었음   → 잔여물이 아님.
  R4  reframe 에 보일러플레이트/동기부여 상투구  → '사고 기본값을 바꾸는 한 줄'이 아님.
  R5  reframe 가 title을 그대로 베낌            → 합성 안 됨.

R4 금지구: 책 카드가 흔히 빠지는 공허한 표현들.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

PLAY_DIR = Path(__file__).resolve().parent.parent
CARDS_FILE = PLAY_DIR / "data" / "cards.jsonl"

BOILERPLATE = [
    re.compile(r"열심히\s*(하면|하자|살자)"),
    re.compile(r"노력은\s*배신하지\s*않는다"),
    re.compile(r"결국\s*다\s*잘\s*될\s*것"),
    re.compile(r"중요하다는\s*것을\s*깨달았다$"),
    re.compile(r"교훈을\s*얻었다$"),
    re.compile(r"긍정적으로\s*생각하"),
    re.compile(r"무엇이든\s*할\s*수\s*있다"),
]


def load_cards() -> list[dict]:
    out = []
    for i, line in enumerate(CARDS_FILE.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError as e:
            out.append({"_parse_error": str(e), "_line": i})
    return out


def audit(card: dict) -> list[str]:
    v = []
    if "_parse_error" in card:
        return [f"PARSE_ERROR line {card['_line']}: {card['_parse_error']}"]

    ctype = card.get("book", {}).get("type")
    trigger = (card.get("trigger_when") or "").strip()
    reframe = (card.get("reframe") or "").strip()
    title = (card.get("book", {}).get("title") or "").strip()

    if ctype == "idea" and not trigger:
        v.append("R1 idea인데 trigger_when 비었음 → 발동 불가")
    if ctype == "novel" and card.get("review") is not None:
        v.append("R2 novel인데 review!=None → SRS 범주 오류")
    if len(reframe) < 15:
        v.append("R3 reframe 너무 짧음/비었음")
    for pat in BOILERPLATE:
        if pat.search(reframe):
            v.append(f"R4 보일러플레이트 상투구: '{pat.pattern}'")
            break
    if title and reframe and title in reframe and len(reframe) < len(title) + 10:
        v.append("R5 reframe가 title 복붙 수준")
    return v


def main() -> None:
    cards = load_cards()
    violations = {c.get("card_id", f"?{i}"): audit(c) for i, c in enumerate(cards)}
    bad = {k: v for k, v in violations.items() if v}

    print(f"== 카드 감사: {len(cards)}장 ==")
    for c in cards:
        if "_parse_error" in c:
            continue
        cid = c["card_id"]
        ctype = c["book"]["type"]
        status = "OK" if not violations[cid] else "FAIL"
        print(f"  [{status}] {cid} ({ctype})")
        for msg in violations[cid]:
            print(f"        - {msg}")

    print(f"\n위반 카드: {len(bad)} / {len(cards)}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
