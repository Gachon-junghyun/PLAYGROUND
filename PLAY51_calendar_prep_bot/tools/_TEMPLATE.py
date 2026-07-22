"""도구 템플릿 — 이 파일을 `tools/<도구이름>.py` 로 복사하고 META/run 을 채워라.

규칙 (자세한 건 tools/__init__.py 참고):
- 파일명 == META["name"] == 영문 snake_case.
- run 의 인자는 전부 문자열로 들어온다. 반환도 문자열.
- 무거운 라이브러리는 run 안에서 lazy import.
- 저장 후 봇에서 /reload 하면 즉시 붙는다.
"""

META = {
    "name": "example",                         # 파일명과 동일하게
    "description": "이 도구가 뭘 하는지 한 줄. LLM 이 '언제 이걸 써야 하는지' 판단할 수 있게 써라.",
    "params": {
        "text": "이 인자가 무엇인지 설명 (LLM 이 뭘 넣어야 할지 알 수 있게)",
    },
}


def run(text: str) -> str:
    return f"받은 값: {text}"
