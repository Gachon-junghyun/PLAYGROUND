#!/usr/bin/env python3
"""Cloudflare Workers AI 이미지 생성 REST API 호출 실험. 표준 라이브러리만 사용."""
import argparse
import base64
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_TXT2IMG_MODEL = "@cf/stabilityai/stable-diffusion-xl-base-1.0"
DEFAULT_IMG2IMG_MODEL = "@cf/runwayml/stable-diffusion-v1-5-img2img"
ENV_FILE = Path(__file__).resolve().parent / "env"


def load_env_file(path):
    """KEY=VALUE 형식의 로컬 env 파일을 읽어 os.environ에 없는 키만 채운다. 파일이 없으면 조용히 스킵."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _run_model(model, payload, account_id, api_token):
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}"
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Authorization", f"Bearer {api_token}")
    req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            content_type = resp.headers.get("Content-Type", "")
            data = resp.read()
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise SystemExit(f"Cloudflare API error {e.code}: {detail}")

    # SD 계열은 image/png 원본 바이트를 바로 준다.
    if "application/json" not in content_type:
        return data

    # flux 등 일부 모델은 JSON에 base64 이미지를 담아 준다.
    result = json.loads(data)
    if not result.get("success", True):
        raise SystemExit(f"API returned failure: {result}")
    image_b64 = result.get("result", {}).get("image")
    if not image_b64:
        raise SystemExit(f"No image in response: {result}")
    return base64.b64decode(image_b64)


def generate_image(prompt, model, account_id, api_token):
    return _run_model(model, {"prompt": prompt}, account_id, api_token)


def modify_image(prompt, input_image_path, model, account_id, api_token, strength):
    image_bytes = Path(input_image_path).read_bytes()
    payload = {"prompt": prompt, "image": list(image_bytes), "strength": strength}
    return _run_model(model, payload, account_id, api_token)


def main():
    parser = argparse.ArgumentParser(description="Cloudflare Workers AI image generation/modification experiment")
    parser.add_argument("prompt", help="이미지 생성/수정 프롬프트")
    parser.add_argument("-i", "--input-image", help="이 이미지를 입력으로 img2img 수정 (없으면 텍스트→이미지 생성)")
    parser.add_argument("-s", "--strength", type=float, default=0.8,
                         help="img2img 전용: 원본을 얼마나 남길지 0~1 (낮을수록 원본 보존, 기본값: 0.8)")
    parser.add_argument("-o", "--output", default="output.png", help="출력 PNG 경로 (기본값: output.png)")
    parser.add_argument("-m", "--model", default=None,
                         help=f"Workers AI 모델 ID (기본값: txt2img={DEFAULT_TXT2IMG_MODEL}, img2img={DEFAULT_IMG2IMG_MODEL})")
    args = parser.parse_args()

    load_env_file(ENV_FILE)
    account_id = os.environ.get("CF_ACCOUNT_ID")
    api_token = os.environ.get("CF_API_TOKEN")
    if not account_id or not api_token:
        raise SystemExit("환경변수 CF_ACCOUNT_ID, CF_API_TOKEN을 먼저 설정하세요.")

    if args.input_image:
        model = args.model or DEFAULT_IMG2IMG_MODEL
        image_bytes = modify_image(args.prompt, args.input_image, model, account_id, api_token, args.strength)
    else:
        model = args.model or DEFAULT_TXT2IMG_MODEL
        image_bytes = generate_image(args.prompt, model, account_id, api_token)

    with open(args.output, "wb") as f:
        f.write(image_bytes)
    print(f"saved: {args.output} ({len(image_bytes)} bytes)")


if __name__ == "__main__":
    main()
