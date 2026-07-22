"""NVIDIA NIM 하네스 — 단일 프롬프트를 강한 모델 하나로 호출(모델 폴백 내장).

arena.py 가 이미 만들어둔 키 로딩 + OpenAI 호환 클라이언트를 재사용한다.
arena.py 는 여러 모델을 *나란히 비교*하는 용도라면, 이 파일은 파이프라인이
'답 하나'를 필요로 할 때 쓴다 — 첫 모델이 죽거나(404/과부하) 빈 답이면
다음 모델로 자동 폴백해서 리포트 생성이 통째로 멈추지 않게 한다.

    from nv_client import chat
    model, text = chat("삼성전자 요약", system="너는 애널리스트다")
"""
from __future__ import annotations

import time

# 같은 PLAY 안의 arena.py 재사용 (키 로딩·클라이언트 생성 로직 중복 방지).
from arena import load_api_key, make_client

# 폴백 체인. 앞에서부터 시도, 성공하면 멈춘다.
# 순서 기준 = 스트리밍 실측(2026-07-09): 첫 토큰까지(TTFT) 짧고 조각이 잘게 나오는
# non-reasoning 모델을 앞에. **reasoning 모델(deepseek/nemotron-super/gpt-oss)은
# 답 전에 속으로 오래 생각해서 TTFT 가 13~44초씩 걸리고 스트리밍이 '안 되는 것처럼'
# 보인다** — 그래서 뒤로 뺐다. ministral-14b 는 TTFT 0.4s·토큰단위·항상 응답으로 최상.
# ID 는 수시로 바뀐다 — stale 이면 `python arena.py --list` 로 확인 후 교체.
# 2026-07-22: qwen3.5-122b-a10b 퇴역 확인. 대체 후보 qwen3.5-397b-a17b 는 실측
# 30s+ 타임아웃이라 기각하고, 1.0s 로 응답한 qwen3-next-80b-a3b-instruct 로 교체.
DEFAULT_CHAIN = [
    "mistralai/ministral-14b-instruct-2512",     # TTFT 0.4s, 토큰단위, 안정 → 기본
    "nvidia/nvidia-nemotron-nano-9b-v2",          # TTFT 0.4s, 빠름(조각 거침)
    "stepfun-ai/step-3.7-flash",                  # TTFT 0.2s, 가장 빠른 시작
    "qwen/qwen3-next-80b-a3b-instruct",           # 실측 1.0s, 안정
    "deepseek-ai/deepseek-v4-pro",                # 품질 좋지만 느림/버스트(TTFT 13s)
]

# 합성(리포트 작성) 전용 체인 — '가장 좋은 모델' 우선. 스크리닝(여러 번 호출)과 달리
# 합성은 1회뿐이라 최고 품질 모델을 쓴다. 2026-07-09 실측: mistral-large-3(675B)가
# TTFT 0.4s·토큰단위 스트림·최상급 품질로 1위(qwen-397b·nemotron-ultra 는 timeout/404).
# deepseek 는 품질 좋으나 TTFT 39s → 폴백. 최후엔 빠른 ministral 로라도 답을 낸다.
SYNTH_CHAIN = [
    "mistralai/mistral-large-3-675b-instruct-2512",  # 675B 플래그십, 빠르고 매끄러움
    "deepseek-ai/deepseek-v4-pro",                    # 강한 추론(느림) 폴백
    "mistralai/ministral-14b-instruct-2512",          # 최후 보루(항상 응답)
]

_CLIENT = None


def _client(timeout: float):
    global _CLIENT
    if _CLIENT is None:
        key = load_api_key()
        if not key:
            raise RuntimeError(
                "NVIDIA API 키 없음. nvapi_key.local.txt 를 만들거나 "
                "환경변수 NVIDIA_API_KEY 를 세팅하세요 (README 참고)."
            )
        _CLIENT = make_client(key, timeout)
    return _CLIENT


def chat(
    user: str,
    system: str | None = None,
    models: list[str] | None = None,
    max_tokens: int = 1500,
    temperature: float = 0.3,
    timeout: float = 120.0,
    verbose: bool = True,
    stream: bool = False,
    on_delta=None,
) -> tuple[str, str]:
    """(model_id, text) 반환. 체인의 모든 모델이 실패하면 RuntimeError.

    추론 모델은 답을 reasoning_content 에 넣기도 해서 content 가 비면 그걸 대신 쓴다.
    stream=True 면 토큰이 도착하는 대로 on_delta(piece, kind) 를 호출한다
    (kind = "content" | "reason"). GUI 에서 '써지는 과정'을 실시간으로 보여주는 용도.
    """
    client = _client(timeout)
    chain = models or DEFAULT_CHAIN
    msgs = ([{"role": "system", "content": system}] if system else []) + [
        {"role": "user", "content": user}
    ]
    last_err = None
    for model in chain:
        t0 = time.perf_counter()
        try:
            if stream:
                text = _stream_call(client, model, msgs, max_tokens, temperature, on_delta)
            else:
                resp = client.chat.completions.create(
                    model=model, messages=msgs, temperature=temperature,
                    top_p=0.9, max_tokens=max_tokens, stream=False,
                )
                msg = resp.choices[0].message
                text = (msg.content or "").strip() or \
                    (getattr(msg, "reasoning_content", None) or "").strip()
            if text:
                if verbose:
                    dt = time.perf_counter() - t0
                    print(f"  [nv_client] {model} OK ({dt:.1f}s)", flush=True)
                return model, text
            last_err = "빈 응답"
        except Exception as e:  # 404/rate-limit/네트워크 전부 흡수하고 다음 모델로
            last_err = f"{type(e).__name__}: {e}"
        if verbose:
            print(f"  [nv_client] {model} 실패 → 폴백  ({last_err})", flush=True)
    raise RuntimeError(f"모든 모델 실패. 마지막 오류: {last_err}")


def _stream_call(client, model, msgs, max_tokens, temperature, on_delta) -> str:
    """스트리밍 호출. content 를 최종답으로 모으되 reasoning_content 도 on_delta 로 흘린다."""
    resp = client.chat.completions.create(
        model=model, messages=msgs, temperature=temperature,
        top_p=0.9, max_tokens=max_tokens, stream=True,
    )
    content_parts, reason_parts = [], []
    for chunk in resp:
        if not chunk.choices:
            continue
        d = chunk.choices[0].delta
        r = getattr(d, "reasoning_content", None)
        c = getattr(d, "content", None)
        if r:
            reason_parts.append(r)
            if on_delta:
                on_delta(r, "reason")
        if c:
            content_parts.append(c)
            if on_delta:
                on_delta(c, "content")
    return "".join(content_parts).strip() or "".join(reason_parts).strip()
