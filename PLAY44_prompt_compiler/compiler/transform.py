"""B2. 변환 계층 — 사용자 원명령 → 측면별 행동 키(JSON).

문체 계약: 행동 키는 trigger 와 같은 문체, 즉 "~할 때 / ~하는 작업" 으로 끝나는
상황 묘사 1문장. 측면당 2~3개. Haiku 1회 호출, 파싱 실패 시 1회 재시도, 그래도
실패하면 원명령을 단일 키로 폴백.

ANTHROPIC_API_KEY 가 없으면 LLM 없이 휴리스틱 폴백(원명령 → 단일 키)으로 동작 →
키 없이도 파이프라인 전체가 돈다.
"""
import json
import os
import re

ASPECTS = ["작업유형", "사고스타일", "출력형식", "도메인규칙"]

SYS = """너는 프롬프트 컴파일러의 변환 계층이다. 사용자 원명령을 받아, 어떤 부품(명제)을
불러와야 하는지 측면별 '행동 키'로 변환한다.

문체 계약(엄수): 모든 행동 키는 '상황 묘사 1문장'이며 반드시 "~할 때" 또는 "~하는 작업"
으로 끝난다. 행동 자체를 적지 말고, 그 행동이 필요한 *상황*을 적어라.
- 나쁨: "멀티플 산정 근거를 명시" (행동·명사구)
- 좋음: "기업 밸류에이션에서 멀티플을 적용할 때" (상황 서술)

측면은 정확히 이 넷: 작업유형 / 사고스타일 / 출력형식 / 도메인규칙. 각 측면당 2~3개.
해당 없는 측면은 빈 배열. 오직 아래 JSON 만 출력하라(설명 금지는 잊고, JSON 만):
{"작업유형": ["...할 때"], "사고스타일": ["...할 때"], "출력형식": ["...하는 작업"], "도메인규칙": ["...할 때"]}"""


def _fallback(command):
    """LLM 실패/무키 시: 원명령을 작업유형 단일 키로. 문체 계약에 맞춰 어미 보정."""
    s = command.strip().rstrip(".")
    if not (s.endswith("때") or s.endswith("작업")):
        s = f"{s}을(를) 수행하는 작업"
    return {"작업유형": [s], "사고스타일": [], "출력형식": [], "도메인규칙": []}


def _parse(txt):
    m = re.search(r"\{.*\}", txt, re.S)
    if not m:
        raise ValueError("no json")
    d = json.loads(m.group())
    return {a: [str(x) for x in d.get(a, []) if str(x).strip()] for a in ASPECTS}


def transform(command, model="claude-haiku-4-5-20251001"):
    """원명령 → {측면: [행동 키...]}. (결과, 경로) 튜플 반환. 경로는 진단용."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return _fallback(command), "fallback:no_key"
    try:
        import anthropic
    except ImportError:
        return _fallback(command), "fallback:no_sdk"

    client = anthropic.Anthropic()
    for attempt in ("first", "retry"):
        try:
            msg = client.messages.create(
                model=model, max_tokens=600, system=SYS,
                messages=[{"role": "user", "content": f"원명령: {command}"}])
            keys = _parse(msg.content[0].text)
            if any(keys[a] for a in ASPECTS):
                return keys, f"llm:{attempt}"
        except Exception:
            continue
    return _fallback(command), "fallback:parse_fail"


if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "삼성전자 3분기 실적 적대적으로 검토해줘"
    keys, path = transform(cmd)
    print(f"[{path}]")
    print(json.dumps(keys, ensure_ascii=False, indent=1))
