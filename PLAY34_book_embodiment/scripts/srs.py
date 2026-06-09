"""SM-2 복습 스케줄러 — stdlib만. 카드의 review 필드를 갱신한다.

핵심 분기 (CLAUDE.md / 디스패치 브리프): **idea 카드만 SRS에 태운다.**
novel 카드는 review == None 으로 저장돼 있고, 스케줄링에서 영구 제외한다.
소설을 간격반복에 태우는 건 범주 오류 — 소설의 가치는 '경험'이라 회상 간격으로
관리할 대상이 아니다.

quality(0~5) 의미:
  0~2 = 발현 실패(상황이 왔는데 reframe가 안 떠오름/막혀버림) → 간격 리셋, 내일 다시.
  3   = 겨우 발현, 적대 검증에서 관절 깨짐.
  4   = 발현했고 적대 한 합 버팀.
  5   = 즉각 발현 + 적대 검증 완파.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

DEFAULT_REVIEW = {"due": None, "ease": 2.5, "interval_days": 1, "reps": 0}


def _today(today: str | None) -> date:
    if today is None:
        return date.today()
    return datetime.strptime(today, "%Y-%m-%d").date()


def init_review(card_type: str, today: str | None = None) -> dict | None:
    """카드 생성 시 review 필드 초기화. novel은 None(=SRS 제외)."""
    if card_type == "novel":
        return None
    d = _today(today)
    return {"due": d.isoformat(), "ease": 2.5, "interval_days": 0, "reps": 0}


def is_due(card: dict, today: str | None = None) -> bool:
    """idea 카드이고 due <= today 면 만기. novel(review None)은 항상 False."""
    review = card.get("review")
    if not review or not review.get("due"):
        return False
    d = _today(today)
    return datetime.strptime(review["due"], "%Y-%m-%d").date() <= d


def update_review(review: dict, quality: int, today: str | None = None) -> dict:
    """SM-2 한 스텝. review dict를 받아 새 review dict를 반환(원본 비파괴)."""
    if review is None:
        raise ValueError("novel 카드(review=None)는 SRS 스케줄 대상이 아니다 — 범주 오류")
    if not (0 <= quality <= 5):
        raise ValueError("quality는 0~5 정수")

    ease = float(review.get("ease", 2.5))
    interval = int(review.get("interval_days", 0))
    reps = int(review.get("reps", 0))
    d = _today(today)

    if quality < 3:
        # 발현 실패 → 리셋. 내일 다시.
        reps = 0
        interval = 1
    else:
        if reps == 0:
            interval = 1
        elif reps == 1:
            interval = 6
        else:
            interval = max(1, round(interval * ease))
        reps += 1

    # ease 갱신(표준 SM-2 공식), 하한 1.3
    ease = ease + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    ease = max(1.3, round(ease, 3))

    return {
        "due": (d + timedelta(days=interval)).isoformat(),
        "ease": ease,
        "interval_days": interval,
        "reps": reps,
    }


if __name__ == "__main__":
    # 동작 확인용 짧은 시연
    r = init_review("idea", "2026-05-31")
    print("init idea:", r)
    print("init novel:", init_review("novel"))
    for q in (5, 4, 2, 4):
        r = update_review(r, q, "2026-05-31")
        print(f"  q={q} -> reps={r['reps']} interval={r['interval_days']} ease={r['ease']} due={r['due']}")
