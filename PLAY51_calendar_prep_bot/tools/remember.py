"""사용자가 '기억해줘/참고해둬' 하거나, 나중에 도움될 지속적 사실을 알게 됐을 때 저장.
저장된 기억은 이후 모든 대화·일정 준비의 system 프롬프트에 자동으로 주입된다."""

META = {
    "name": "remember",
    "description": "지속적으로 기억할 사실을 저장. 사용자가 '기억해/참고해둬' 하거나, 일정·사람·선호처럼 나중에 또 쓸 맥락을 알게 되면 호출. 일정에 단어 몇 개뿐이어도 이 기억으로 채워서 진행할 수 있게 된다.",
    "params": {"content": "기억할 내용 (누가/무엇을/왜/선호 등 구체적으로, 한 문장)"},
}


def run(content: str) -> str:
    import bot
    conn = bot.db_connect()
    try:
        bot.mem_add(conn, content)
    finally:
        conn.close()
    return f"기억했어요: {content}"
