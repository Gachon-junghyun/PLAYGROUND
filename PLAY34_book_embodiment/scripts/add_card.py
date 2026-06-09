"""캡처 플로우 — 카드 JSON(파일 또는 stdin) → data/cards.jsonl 에 append.

카드 *내용*(trigger_when/reframe/...)은 모델이 prompts/extract_cards.md로 발췌에서
합성한다. 이 스크립트는 그 결과를 받아 review 필드를 type에 맞게 초기화하고 저장하는
plumbing일 뿐이다.

idea/novel 분기:
  - idea  : review = {due: today, ease 2.5, ...}  (SRS 태움)
  - novel : review = None                          (SRS 제외)

card_id 미지정 시 다음 B### 자동 부여.

사용:
  python add_card.py path/to/new_card.json
  type new_card.json | python add_card.py -        # stdin
  python add_card.py path/to/new_card.json --today 2026-05-31
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
import srs  # noqa: E402

PLAY_DIR = Path(__file__).resolve().parent.parent
CARDS_FILE = PLAY_DIR / "data" / "cards.jsonl"


def load_cards() -> list[dict]:
    if not CARDS_FILE.exists():
        return []
    out = []
    for line in CARDS_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def next_id(cards: list[dict]) -> str:
    nums = []
    for c in cards:
        cid = c.get("card_id", "")
        if cid.startswith("B") and cid[1:].isdigit():
            nums.append(int(cid[1:]))
    return f"B{(max(nums) + 1) if nums else 1:03d}"


def main() -> None:
    ap = argparse.ArgumentParser(description="발췌→카드 결과를 cards.jsonl에 append")
    ap.add_argument("src", help="카드 JSON 파일 경로, 또는 '-' (stdin)")
    ap.add_argument("--today", help="YYYY-MM-DD (review due 초기화 날짜)")
    args = ap.parse_args()

    raw = sys.stdin.read() if args.src == "-" else Path(args.src).read_text(encoding="utf-8")
    card = json.loads(raw)

    ctype = card.get("book", {}).get("type")
    if ctype not in ("idea", "novel"):
        sys.exit("[err] book.type 은 'idea' 또는 'novel' 이어야 한다.")

    cards = load_cards()
    card.setdefault("card_id", next_id(cards))
    card.setdefault("cross_links", [])

    # idea인데 trigger 없으면 거부 — trigger 없는 카드는 발동 불가(브리프: '하지 마라').
    if ctype == "idea" and not card.get("trigger_when", "").strip():
        sys.exit(f"[err] idea 카드 {card['card_id']}에 trigger_when이 비었다. "
                 "발동 조건 없는 카드는 deployment가 불가능하다.")

    # review 필드를 type에 맞게 (재)초기화. 이미 있으면 존중.
    if "review" not in card:
        card["review"] = srs.init_review(ctype, args.today)
    elif ctype == "novel":
        card["review"] = None  # novel은 항상 SRS 제외

    with CARDS_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(card, ensure_ascii=False) + "\n")

    print(f"[OK] {card['card_id']} ({ctype}) 추가 → {CARDS_FILE}")
    if ctype == "idea":
        print(f"     review.due = {card['review']['due']} (오늘 만기). "
              "python review.py present " + card["card_id"])
    else:
        print("     novel — SRS 제외. 뷰어로 읽기만.")


if __name__ == "__main__":
    main()
