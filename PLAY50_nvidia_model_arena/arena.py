"""NVIDIA NIM Model Arena — 같은 프롬프트를 여러 무료 모델에 병렬로 던지고 답을 나란히 비교.

build.nvidia.com 이 OpenAI 호환 API 로 100+ 모델을 무료로 열어둔 걸 활용한다.
키는 코드에 박지 않는다. 환경변수 NVIDIA_API_KEY 만 세팅하면 바로 돈다.

    setx NVIDIA_API_KEY "nvapi-xxxx"   # PowerShell, 새 창부터 적용
    python arena.py "블랙홀을 5살한테 설명해줘"
"""

import argparse
import concurrent.futures
import os
import pathlib
import sys
import textwrap
import time

# Windows 콘솔(cp949)에서 유니코드 구분선/한글이 깨지거나 죽는 걸 막는다.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# 키는 코드에 안 박는다. 우선순위: 환경변수 → 옆에 있는 nvapi_key.local.txt (gitignore됨).
KEY_FILE = pathlib.Path(__file__).with_name("nvapi_key.local.txt")


def load_api_key():
    key = os.environ.get("NVIDIA_API_KEY")
    if key:
        return key.strip()
    if KEY_FILE.exists():
        return KEY_FILE.read_text(encoding="utf-8").strip()
    return None

# build.nvidia.com 은 OpenAI 호환 → base_url 만 갈아끼우면 openai SDK 그대로 사용.
BASE_URL = "https://integrate.api.nvidia.com/v1"

# 기본 비교 대상 — 서로 다른 랩의 현행 chat 모델 5종.
# 2026-07-22 에 --list(118개)로 재검증. qwen3.5-122b-a10b 는 그새 퇴역해서
# 대체 후보 qwen3.5-397b-a17b 를 먼저 넣었으나 30s+ 타임아웃(너무 무거움) —
# 실측 1.0s 로 응답하는 qwen3-next-80b-a3b-instruct 로 최종 교체.
# (나머지 4개는 07-01 확인 그대로 생존 확인됨.)
# 404/410 이면 스크립트가 죽지 않고 그 모델만 건너뛰고 나머지로 계속 간다.
# 지금 쓸 수 있는 전체 목록:  python arena.py --list  (키 필요)
DEFAULT_MODELS = [
    "meta/llama-3.3-70b-instruct",              # Meta
    "openai/gpt-oss-120b",                      # OpenAI (오픈웨이트)
    "qwen/qwen3-next-80b-a3b-instruct",         # Alibaba Qwen
    "deepseek-ai/deepseek-v4-pro",              # DeepSeek
    "nvidia/llama-3.3-nemotron-super-49b-v1.5", # NVIDIA Nemotron
]

DEFAULT_PROMPT = "한 문장으로: 좋은 개발자와 그냥 코딩하는 사람의 차이는?"


def ask_one(client, model, prompt, max_tokens, temperature):
    """모델 하나 호출. (model, ok, text, latency_s, tokens, error) 튜플 반환."""
    t0 = time.perf_counter()
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            top_p=0.9,
            max_tokens=max_tokens,
            stream=False,
        )
        dt = time.perf_counter() - t0
        msg = resp.choices[0].message
        text = (msg.content or "").strip()
        # 추론 모델(gpt-oss, nemotron-super 등)은 답을 reasoning_content 에 넣고
        # content 는 비워두기도 한다. content 가 비면 사고과정이라도 보여준다.
        reasoning = (getattr(msg, "reasoning_content", None) or "").strip()
        if not text and reasoning:
            text = "[사고과정만 반환됨 — --max-tokens 를 늘리면 최종답이 나옴]\n" + reasoning
        tokens = getattr(resp.usage, "total_tokens", None) if resp.usage else None
        return (model, True, text, dt, tokens, None)
    except Exception as e:  # 404/rate-limit/auth/네트워크 전부 여기서 흡수
        dt = time.perf_counter() - t0
        return (model, False, "", dt, None, f"{type(e).__name__}: {e}")


def make_client(api_key, timeout):
    try:
        from openai import OpenAI
    except ImportError:
        sys.exit("[!] openai SDK 가 없습니다.  pip install openai  후 다시 실행하세요.")
    # max_retries=0: 504/과부하 모델에서 SDK 가 몇 분씩 재시도하며 매달리는 걸 막는다.
    return OpenAI(base_url=BASE_URL, api_key=api_key, timeout=timeout, max_retries=0)


def print_result(r, wrap):
    model, ok, text, dt, tokens, err = r
    head = f"-- {model}"
    print("\n" + head + " " + "-" * max(0, 72 - len(head)))
    if not ok:
        print(f"   [실패 {dt:4.1f}s]  {err}")
        return
    tok_s = f"{tokens} tok" if tokens is not None else "tok?"
    print(f"   [{dt:4.1f}s · {tok_s}]")
    body = text if text else "(빈 응답)"
    for line in body.splitlines() or [body]:
        print(textwrap.fill(line, width=wrap, initial_indent="   ", subsequent_indent="   ")
              if line.strip() else "")


def main():
    ap = argparse.ArgumentParser(
        description="같은 프롬프트를 여러 NVIDIA 무료 모델에 병렬 호출해 비교.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("prompt", nargs="?", default=DEFAULT_PROMPT,
                    help="모델들에게 던질 프롬프트 (생략 시 기본 프롬프트)")
    ap.add_argument("--models", help="쉼표로 구분한 모델 ID 목록 (기본 세트 덮어쓰기)")
    ap.add_argument("--max-tokens", type=int, default=512,
                    help="모델당 최대 출력 토큰 (기본 512, 크레딧 아끼려면 낮게)")
    ap.add_argument("--temperature", type=float, default=0.4)
    ap.add_argument("--wrap", type=int, default=76, help="출력 줄바꿈 폭")
    ap.add_argument("--timeout", type=float, default=60.0,
                    help="모델당 응답 대기 상한(초). 초과 시 그 모델만 실패 처리 (기본 60)")
    ap.add_argument("--list", action="store_true",
                    help="지금 이 키로 호출 가능한 전체 모델 ID 를 출력하고 종료")
    args = ap.parse_args()

    api_key = load_api_key()
    if not api_key:
        sys.exit(
            "[!] API 키를 못 찾았습니다. 둘 중 하나로 넣으세요:\n"
            "    (A) 이 폴더에 nvapi_key.local.txt 파일 만들고 키 한 줄 붙여넣기 (git 무시됨, 권장)\n"
            "    (B) PowerShell:  setx NVIDIA_API_KEY \"nvapi-xxxx\"  (새 창부터 적용)\n"
            "    키 발급: https://build.nvidia.com → 아무 모델 → 'Get API Key'\n"
        )

    client = make_client(api_key, args.timeout)

    if args.list:
        models = sorted(m.id for m in client.models.list().data)
        print(f"호출 가능한 모델 {len(models)}개:")
        for m in models:
            print(f"  {m}")
        return

    models = ([m.strip() for m in args.models.split(",") if m.strip()]
              if args.models else DEFAULT_MODELS)

    print(f"프롬프트: {args.prompt}")
    print(f"모델 {len(models)}개 병렬 호출 중...  (무료 티어 ~40 RPM 공유 한도)")

    # 무료 티어가 ~40 RPM 이라 모델 몇 개는 동시에 쏴도 안전. 워커는 넉넉히.
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(8, len(models))) as ex:
        futs = [ex.submit(ask_one, client, m, args.prompt, args.max_tokens, args.temperature)
                for m in models]
        for f in concurrent.futures.as_completed(futs):
            results.append(f.result())

    # 원래 순서대로 정렬해서 출력 (as_completed 는 도착 순이라 뒤섞임)
    order = {m: i for i, m in enumerate(models)}
    results.sort(key=lambda r: order.get(r[0], 999))

    for r in results:
        print_result(r, args.wrap)

    ok = sum(1 for r in results if r[1])
    fastest = min((r for r in results if r[1]), key=lambda r: r[3], default=None)
    print("\n" + "=" * 74)
    print(f"성공 {ok}/{len(models)}"
          + (f"  ·  최속: {fastest[0]} ({fastest[3]:.1f}s)" if fastest else ""))
    if ok < len(models):
        print("실패 모델은 대개 ID 가 바뀐 경우 —  python arena.py --list  로 현행 ID 확인.")


if __name__ == "__main__":
    main()
