# PLAY10_chat_playground

## 목적
PLAY9에서 학습한 LoRA 어댑터를 **실사용** 하기 위한 챗 UI. 두 모델을 사이드바이사이드로 띄워서 (튠 vs 베이스) 비교 + 사용자 ㅋㅋㅋ를 reward signal로 잡아 자가 데이터 수집까지 한 번에.

## 디자인 핵심

```
좌측 패널: PLAY9 어댑터 (Korean microstyle, <think>+답변)
우측 패널: 동일 base Gemma 4 E2B (어댑터 disable, raw 응답)
   ↓
사용자가 어느 패널이든 "ㅋ" 3개 이상(ㅋㅋㅋ) 포함 발화 입력
   ↓
그 패널의 **직전 3 메시지** 묶음 → data/collected_kkkk.jsonl 자동 append
```

VRAM 절약: base 모델 하나만 로드, `model.disable_adapter()` 컨텍스트로 베이스 응답 생성. RTX 3080 10GB에 ~8GB만 사용.

## 실행법

### 0. 사전 준비
PLAY9 환경 그대로. torch 2.10.0+cu128, torchvision 0.23.0, xformers 0.0.35, transformers 5.5.0, unsloth 2026.5.2, bitsandbytes 0.49.1. (PLAY9 README "0. 사전 준비" 참고)

추가로 gradio만:
```powershell
pip install -r requirements.txt
```

### 1. 실행
```powershell
cd C:\Users\fivep\OneDrive\Desktop\PLAYGROUND\PLAY10_chat_playground
$env:PYTHONUTF8 = "1"
$env:HF_HUB_DISABLE_SYMLINKS_WARNING = "1"
python -u src/chat.py
```

- 모델 로딩 ~30-60초.
- 끝나면 자동으로 브라우저 열리고 `http://localhost:7860`.
- 좌/우 각각 다른 대화 진행 가능. 입력은 패널별 텍스트박스에.

### 2. ㅋㅋㅋ 데이터 수집 흐름

```
turn 1) user: 나 오늘 발표 망한 듯
        bot: ㄱㅊㄱㅊ 발표는 시간이 약이지

turn 2) user: 진짜 시간이 약이긴 함
        bot: 시간이 약사라면 의사는 누구야?

turn 3) user: ㅋㅋㅋㅋㅋㅋ 너무 웃긴데?
              ↑ ㅋ 3개 이상 감지 → 캡처 발동
```

캡처되는 jsonl row:
```json
{
  "model": "tuned",                          // 또는 "base"
  "trigger": "ㅋㅋㅋㅋㅋㅋ 너무 웃긴데?",
  "captured_at": "2026-05-13T01:23:45",
  "messages": [
    {"role": "assistant", "content": "..."},  // 마지막 3 메시지
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ]
}
```

이 jsonl을 PLAY11에서 추가 학습 데이터로 사용 (계획).

## 입력 / 출력
- **입력:** 브라우저 챗 인터페이스. 좌측은 튠 모델용 textbox, 우측은 베이스용.
- **출력:**
  - 화면: 각 패널 chatbot에 사고(`🧠 *...*`) + 답변(`💬 **...**`) 표시
  - 파일: `data/collected_kkkk.jsonl` (ㅋㅋㅋ 트리거 데이터 누적)

## 가정 & 제약

### PLAY 독립성
- `adapter/`는 PLAY9 `ckpt/final/`의 사본 (128MB). PLAY9가 어댑터 재학습하면 사용자가 명시적으로 다시 복사해야 반영.
- base 모델은 `unsloth/gemma-4-E2B-it` (HF cache 공유). adapter `train_meta.json`에서 base id 자동 추출.

### 두 모델 동시 실행 — adapter toggle
- PEFT의 `model.disable_adapter()` 컨텍스트로 base 응답 생성. 같은 모델 인스턴스 메모리 공유 → VRAM 2배 안 듦.
- 한 요청 한 번에 하나씩만 generate (좌/우 동시 입력 불가, race 없음).

### ㅋㅋㅋ 감지 휴리스틱
- 정규식 `ㅋ{3,}` (한글 ㅋ 자모 3개 이상 연속). `ㅋㅋㅋ`, `ㅋㅋㅋㅋㅋㅋ` 등 잡음.
- "ㄱㅋㅋㅋ"같이 자모 깨진 경우는 안 잡힘. 보통 IME 정상이면 문제 없음.
- 사용자가 농담 아닌데 ㅋㅋㅋ 칠 수도 있음(반어법, 자조). 데이터 noise로 받아들이고 PLAY11에서 manual cleanup 가정.

### 직전 3 메시지의 의미
- ㅋㅋㅋ 발화 **직전까지** 누적된 history에서 **마지막 3 entry** 캡처.
- 보통 (user → assistant → user) 또는 (assistant → user → assistant) 패턴. role 균등 보장 안 함.
- ㅋㅋㅋ 발화 자체는 trigger 필드에 별도 저장.
- 3개 미만이면 있는 만큼만 (대화 초반에 ㅋㅋㅋ 치면 짧게).

### 안전선
- 같은 system prompt를 양쪽에 동일하게 주입 → fair 비교. base 모델도 <think> 형식 시도하지만 학습 안 됐으니 잘 안 따를 가능성 큼 (그게 비교 포인트).
- 데이터 수집은 로컬 파일에만. 외부 전송 없음.

### 실행 시간 / 디스패치 적합도
- `chat.py` 실행 자체는 1회성 launch (서버처럼 떠 있음).
- 모델 로딩 ~30-60초.
- 한 응답 ~30-50초 (max_new_tokens=500, T4-level GPU 기준).
- **디스패치 부적합** — UI는 사용자 직접 띄움.

### Gradio 보안
- `server_name="127.0.0.1"` 로컬 only. `share=False`로 외부 공개 안 함.
- 7860 포트가 이미 쓰이면 `demo.launch(server_port=7861)` 등으로 변경.

## 변경 이력
- 2026-05-12 — 최초 생성. PLAY9 어댑터(ckpt/final) 128MB 복사. Gradio Blocks 기반 좌우 챗 UI, `disable_adapter()` 컨텍스트로 base/tuned 동시 비교. ㅋ{3,} 정규식 감지 + 직전 3 메시지 jsonl append. system prompt는 PLAY8/9 학습 시 사용한 것과 동일하게 하드코딩. 모델은 같은 인스턴스 공유로 VRAM 2배 절약.
