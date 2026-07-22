"""기억해둔 것 중 특정 주제를 찾아본다. (전체 기억은 이미 자동 주입되므로,
기억이 아주 많아져서 특정 키워드만 콕 집어 보고 싶을 때 보조로 쓴다.)"""

META = {
    "name": "recall",
    "description": "저장된 기억 중 특정 키워드가 든 것만 찾는다. (전체 기억은 자동으로 이미 참고 중)",
    "params": {"query": "찾을 키워드"},
}


def run(query: str) -> str:
    import bot
    conn = bot.db_connect()
    try:
        rows = bot.mem_all(conn, limit=500)
    finally:
        conn.close()
    q = (query or "").lower().strip()
    hits = [f"#{i}: {c}" for i, c in rows if q in c.lower()]
    return "\n".join(hits) if hits else f"'{query}' 관련 기억 없음"
