"""iCloud 캘린더에서 향후 일정을 가져온다."""

META = {
    "name": "list_events",
    "description": "iCloud 캘린더의 향후 일정 목록을 본다. 사용자가 '내 일정', '다음 약속', '오늘 뭐 있어' 물으면 사용.",
    "params": {"hours": "앞으로 몇 시간 범위를 볼지 (숫자 문자열, 기본 48)"},
}


def run(hours: str = "48") -> str:
    import bot  # 같은 폴더 bot.py 의 CalDAV 로직 재사용 (call 시점 lazy import)
    try:
        n = int(str(hours).strip())
    except (ValueError, TypeError):
        n = 48
    events = bot.fetch_upcoming_events(lookahead_hours=n)
    if not events:
        return f"향후 {n}시간 내 일정 없음"
    return "\n".join(f"- {e['start'].isoformat()}  {e['title']}"
                     + (f"  (메모: {e['notes'][:60]})" if e["notes"] else "")
                     for e in events)
