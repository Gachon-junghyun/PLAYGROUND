"""Sparring CLI — deployment 루프의 하네스.

⭐ 이 PLAY의 핵심: 복습을 '퀴즈'가 아니라 "이런 상황이 왔다, 받아쳐봐"(TAP)로 띄운다.
   카드를 *상황*으로 부활시키고, 사용자가 응답하면 회의론자(=Claude/subagent,
   prompts/sparring.md)가 한 합 후벼판다. 그 결과를 quality로 채점해 다음 복습일을 재계산.

이 스크립트가 하는 일(=plumbing):
  - due      : 오늘 만기인 idea 카드 목록.
  - present  : 카드를 '상황'으로 출력. **reframe은 숨긴다**(deployment: 사용자가 직접 생성).
  - grade    : SM-2로 다음 복습일 재계산 + review_log.jsonl에 발현 결과 기록 + 카드 갱신.

적대 검증 '한 합' 자체는 코드가 아니라 모델(메인 Claude/subagent)이 prompts/sparring.md로
수행한다. 외부 LLM API 호출 없음.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

# Windows 콘솔(cp949)에서 한국어·em-dash 출력 시 크래시 방지.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
import srs  # noqa: E402

PLAY_DIR = Path(__file__).resolve().parent.parent
CARDS_FILE = PLAY_DIR / "data" / "cards.jsonl"
LOG_FILE = PLAY_DIR / "log" / "review_log.jsonl"


def load_cards() -> list[dict]:
    cards = []
    for line in CARDS_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            cards.append(json.loads(line))
    return cards


def save_cards(cards: list[dict]) -> None:
    CARDS_FILE.write_text(
        "\n".join(json.dumps(c, ensure_ascii=False) for c in cards) + "\n",
        encoding="utf-8",
    )


def get_card(cards: list[dict], card_id: str) -> dict:
    for c in cards:
        if c["card_id"] == card_id:
            return c
    sys.exit(f"[err] card_id '{card_id}' 없음")


def cmd_due(args) -> None:
    cards = load_cards()
    due = [c for c in cards if srs.is_due(c, args.today)]
    today = args.today or date.today().isoformat()
    print(f"== 오늘({today}) 만기 카드: {len(due)}장 ==\n")
    if not due:
        print("(없음) novel 카드는 SRS 대상이 아니라 여기 안 뜬다.")
        return
    for c in due:
        r = c["review"]
        print(f"  {c['card_id']}  [{c['book']['type']}] {c['book']['title']}")
        print(f"        trigger: {c['trigger_when'][:70]}")
        print(f"        reps={r['reps']} ease={r['ease']} due={r['due']}\n")
    print("다음: python review.py present <card_id>")


def cmd_present(args) -> None:
    """카드를 '상황'으로 띄운다. reframe은 숨긴다 — 사용자가 직접 생성해야 deployment."""
    cards = load_cards()
    c = get_card(cards, args.card_id)
    if c["book"]["type"] == "novel":
        print(f"[skip] {c['card_id']}는 novel 카드 — sparring/SRS 대상이 아니다.")
        print("소설 카드는 felt-shift를 그냥 다시 '느끼는' 용도. 뷰어로 읽어라.")
        return

    print("=" * 64)
    print(f"  SPARRING — {c['card_id']}  ({c['book']['title']} / {c['book']['author']})")
    print("=" * 64)
    print("\n[상황이 왔다]")
    print(f"  {c['trigger_when']}\n")
    print("이 순간 네 사고 기본값을 바꿀 한 수는? (reframe을 *네 말로* 꺼내라.)")
    if c.get("verification_questions"):
        print("\n[자가 점검 — 답해보고 막히면 발현 실패다]")
        for i, q in enumerate(c["verification_questions"], 1):
            print(f"  {i}. {q}")
    print("\n→ 네 응답을 적은 뒤, prompts/sparring.md를 Claude에게 줘서 적대 한 합을 받아라.")
    print("→ 끝나면: python review.py grade", c["card_id"], "<0-5> --note \"...\"")
    print("\n(정답 reframe은 일부러 숨겼다. 막히면 grade 0~2로 정직하게 기록.)")


def cmd_grade(args) -> None:
    cards = load_cards()
    c = get_card(cards, args.card_id)
    if c["book"]["type"] == "novel" or c.get("review") is None:
        sys.exit(f"[err] {c['card_id']}는 novel — SRS 채점 대상이 아니다(범주 오류).")

    old = c["review"]
    new = srs.update_review(old, args.quality, args.today)
    c["review"] = new
    save_cards(cards)

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": (args.today or date.today().isoformat()),
        "card_id": c["card_id"],
        "quality": args.quality,
        "deployed": args.quality >= 3,  # 3+ = 실전에서 발현 성공으로 본다
        "note": args.note or "",
        "interval_before": old["interval_days"],
        "interval_after": new["interval_days"],
        "due_next": new["due"],
    }
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    verdict = "발현 성공" if args.quality >= 3 else "발현 실패(내일 다시)"
    print(f"[기록] {c['card_id']} q={args.quality} → {verdict}")
    print(f"       다음 복습: {new['due']} (간격 {new['interval_days']}일, ease {new['ease']}, reps {new['reps']})")
    print(f"       로그 → {LOG_FILE}")


def main() -> None:
    ap = argparse.ArgumentParser(description="PLAY34 sparring/deployment CLI")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_due = sub.add_parser("due", help="오늘 만기 idea 카드")
    p_due.add_argument("--today", help="YYYY-MM-DD (테스트용 고정 날짜)")
    p_due.set_defaults(func=cmd_due)

    p_pre = sub.add_parser("present", help="카드를 '상황'으로 띄움(reframe 숨김)")
    p_pre.add_argument("card_id")
    p_pre.set_defaults(func=cmd_present)

    p_gr = sub.add_parser("grade", help="발현 결과 채점 + 다음 복습일 재계산")
    p_gr.add_argument("card_id")
    p_gr.add_argument("quality", type=int, help="0~5 (3+ = 발현 성공)")
    p_gr.add_argument("--note", help="이번 합에서 깨진 관절/배운 점")
    p_gr.add_argument("--today", help="YYYY-MM-DD (테스트용 고정 날짜)")
    p_gr.set_defaults(func=cmd_grade)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
