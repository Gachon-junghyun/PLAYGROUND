# PLAY52_cf_workers_ai_imagegen

## 목적
Cloudflare Workers AI REST API(`ai/run/{model}`)를 직접 호출해 텍스트→이미지 생성, 그리고 기존 이미지를 프롬프트로 수정(img2img)하는 최소 실험. Worker 배포 없이 로컬에서 계정 토큰만으로 추론을 찍어본다.

## 실행법
```powershell
# 의존성 설치: 없음 (urllib 등 표준 라이브러리만 사용, Python 3.8+)

# 방법 A: 이 디렉토리 안에 "env" 파일을 만들어 KEY=VALUE로 저장 (git에는 절대 안 올라감, .gitignore 등록됨)
# PLAY52_cf_workers_ai_imagegen/env
#   CF_ACCOUNT_ID=...
#   CF_API_TOKEN=...

# 방법 B: 셸 환경변수로 직접 설정 (env 파일보다 우선순위 높음 — 이미 셸에 설정된 키는 env 파일 값으로 덮어쓰지 않음)
$env:CF_ACCOUNT_ID = "..."
$env:CF_API_TOKEN = "..."

# 텍스트 → 이미지 생성 (SDXL)
python PLAY52_cf_workers_ai_imagegen/main.py "a cat riding a skateboard, watercolor style" -o out.png

# 기존 이미지 → 프롬프트로 수정 (SD1.5 img2img, -i로 입력 이미지 지정)
python PLAY52_cf_workers_ai_imagegen/main.py "the same cat but at night, neon lights" -i out.png -o out_modified.png -s 0.7
```

## 입력 / 출력
- **입력:** 위치 인자 `prompt`(텍스트), `-i/--input-image`(있으면 img2img 모드, 없으면 텍스트→이미지), `-s/--strength`(img2img 전용, 0~1, 낮을수록 원본 보존, 기본 0.8), `-o/--output`(저장 경로, 기본 `output.png`), `-m/--model`(Workers AI 모델 ID 오버라이드, 기본값은 모드별로 다름)
- **출력:** 지정한 경로에 PNG 파일 저장, 콘솔에 저장 경로+바이트 수 출력

## 가정 & 제약
- **모델 응답 포맷이 모델마다 다름을 흡수했다.** `stable-diffusion-xl-base-1.0`, `stable-diffusion-v1-5-img2img` 계열은 `image/png` 원본 바이트를 그대로 응답하고, `@cf/black-forest-labs/flux-1-schnell` 같은 일부 모델은 JSON `{result: {image: base64}}`로 준다. `main.py`는 `Content-Type`으로 분기해서 둘 다 처리하지만, 다른 모델을 쓸 경우 응답 포맷이 또 다를 수 있어 검증 안 했다.
- **img2img 입력 이미지는 바이트 배열 그대로 JSON에 박아 보낸다.** Cloudflare img2img 모델 스펙이 base64가 아니라 `image: [int, int, ...]` 형태를 기대해서 그렇게 맞췄다. 큰 이미지(수 MB)를 넣으면 JSON 페이로드가 커져서 느려지거나 Cloudflare 쪽 요청 크기 제한에 걸릴 수 있음 — 테스트는 ~690KB PNG 기준으로만 확인했다.
- **img2img 출력은 스타일이 크게 튈 수 있다.** SDXL(txt2img)과 SD1.5(img2img)는 다른 모델이라 구도/자세는 유지되지만 화풍이 바뀌는 경우가 흔하다 — 실제 검증에서도 픽셀아트 입력이 일러스트풍으로 나왔다. "미세 수정"을 기대하면 `-s`를 0.3~0.5로 낮춰서 시도.
- **토큰/계정ID는 코드에 없다.** `CF_ACCOUNT_ID`, `CF_API_TOKEN`을 이 디렉토리의 로컬 `env` 파일(KEY=VALUE) 또는 셸 환경변수로만 받는다. `PLAY52_cf_workers_ai_imagegen/env`는 루트 `.gitignore`에 명시적으로 등록돼 있어 커밋되지 않는다 — 파일명이 `.env`가 아니라 확장자 없는 `env`라 기존 `.env*` 패턴만으로는 안 걸렸던 걸 뒤늦게 잡아서 별도 룰을 추가했다.
- **과금:** Workers AI는 무료 티어(일일 뉴런 한도)가 있지만 그 이상은 과금된다. 이 스크립트는 호출 1회당 API 1회 호출만 하므로 반복 실행 시 한도 소진에 유의. 자동 재시도/루프 없음.
- **네트워크 의존.** 오프라인이거나 토큰이 Workers AI 권한이 없으면 `HTTPError`로 바로 중단된다. 별도 재시도 로직 없음 — 디스패치 환경 45초 제한 안에서 1회 호출이 실패하면 그대로 실패로 끝낸다.
- **샘플 프롬프트는 위 실행법 예시로 대체.** 로컬 파일을 읽는 PLAY가 아니라 별도 더미 입력 파일은 두지 않았다.
- Worker 배포(`wrangler deploy`)는 다루지 않는다 — REST API 직접 호출만. Worker 엔드포인트로 감싸는 버전이 필요하면 별도로 요청.

## 변경 이력
- 2026-07-22 — 최초 생성. Cloudflare Workers AI 이미지 생성 REST API를 표준 라이브러리만으로 호출하는 스크립트.
- 2026-07-22 — 로컬 `env` 파일 자동 로딩 추가 + `.gitignore`에 해당 파일 등록(기존 `.env*` 패턴이 확장자 없는 `env` 파일을 못 잡던 구멍 발견 후 수정). 실제 토큰으로 SDXL 이미지 생성 1회 검증 완료 — 정상 동작 확인.
- 2026-07-22 — img2img 모드 추가(`-i/--input-image`, `-s/--strength`). 기존 생성 이미지를 입력으로 넣어 SD1.5 img2img 모델로 수정하는 것까지 실제 토큰으로 검증 완료.
