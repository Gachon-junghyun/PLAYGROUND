# PLAY9_microstyle_lora

## 목적
PLAY8가 만든 1,411 트리플(`<think>...</think>\n답변` 포맷)로 **QLoRA 4-bit SFT 학습**을 돌려, 답변 전에 한국어 자연어 사고를 굴리는 microstyle adapter를 만든다. 학습 후 PLAY7의 평가셋 50건 + 자막 30건으로 베이스라인 대비 회귀/개선 측정.

## 디자인 핵심

```
PLAY8/final_dataset.chat.jsonl  (1,411건, system+user+assistant)
   ↓ prepare_dataset.py          (셔플 + train 1327 / val 84 split)
data/train.jsonl, data/val.jsonl
   ↓ train_qlora.py              (Unsloth FastModel + 4bit + LoRA r=16)
ckpt/final/                       (LoRA adapter + tokenizer + train_meta.json)
   ↓ eval_against_baseline.py    (PLAY7 eval cases에 추론)
reports/run_play9_<ts>.jsonl     (PLAY7 judge.py로 채점 가능한 포맷)
```

- **프레임워크: Unsloth.** raw transformers + peft + trl + bnb 직조합은 2026-05 시점 Gemma 4와 호환성 깨짐 (transformers 5.x ↔ bitsandbytes 0.49 Params4bit). Unsloth가 검증된 의존성 조합 + 2~5x 빠른 학습 + 50~80% 메모리 절약 제공.
- **loss masking**: `train_on_responses_only(instruction_part, response_part)`로 user 토큰은 loss 제외, assistant `<think>...</think>\n답변` 부분만 학습.
- **베이스 모델**: 기본 `unsloth/gemma-4-E4B-it` (Unsloth 사전 양자화, 다운로드 빠름). `google/gemma-4-E4B-it`로도 가능 (느림).
- **시스템 프롬프트**: PLAY8 dataset과 추론 시 동일해야 함. `infer.py` / `eval_against_baseline.py`에 하드코딩.

## 실행법

### 0. 사전 준비 (디스패치 환경 밖에서, 사용자가 직접)

```powershell
# 가상환경 (선택이지만 권장)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 1. PyTorch + torchvision (같은 CUDA index에서 같이!)
#    RTX 3080 + CUDA 12.x. nvidia-smi로 CUDA 버전 확인 후 cu121/cu124/cu128 중 선택.
pip uninstall -y torch torchvision torchaudio   # 기존 깨진 거 있으면 정리
pip install --no-cache-dir "torch==2.8.0" "torchvision==0.23.0" `
  --index-url https://download.pytorch.org/whl/cu128
# ⚠️ torch + torchvision은 반드시 같은 index에서 같이.
# torch 2.11 등 최신은 torchvision wheel 깨진 적 있어서 2.8 안정선 권장.

# 2. Unsloth (transformers/peft/trl/bnb 호환 버전 자동 관리)
pip install unsloth
# 또는 PowerShell 원샷 (Unsloth 권장): irm https://unsloth.ai/install.ps1 | iex

# 3. 우리 추가 의존성
pip install -r requirements.txt

# 4. Hugging Face 토큰 (Gemma 라이센스 동의 후)
#    https://huggingface.co/unsloth/gemma-4-E4B-it 가서 Accept
huggingface-cli login
# 또는: $env:HF_TOKEN = "hf_..."
```

### 환경 검증 (smoke 전에 한 번)

```powershell
python -c "from unsloth import FastModel; print('unsloth OK')"
python -c "import torch; print('cuda', torch.cuda.is_available())"
```

둘 다 OK 뜨면 다음 단계.

### 1. 데이터 split + 통계 (수 초, OK)

```powershell
cd C:\Users\fivep\OneDrive\Desktop\PLAYGROUND\PLAY9_microstyle_lora
$env:PYTHONUTF8 = "1"   # ← 이 PowerShell 세션 동안 한 번
python -u src/prepare_dataset.py
# → data/train.jsonl (1327), data/val.jsonl (84), reports/dataset_stats.md
```

### 2. Smoke 실행 — 20 step 환경 검증 (~10분)

본 학습 전에 **무조건 한 번** 돌려라. 환경(CUDA, bitsandbytes, 토큰) 깨졌는지 빠르게 확인.

```powershell
$env:PYTHONUTF8 = "1"
python -u src/train_qlora.py --smoke > smoke.log 2>&1
# 끝나면 ckpt/smoke_final/이 생기고 마지막 줄에 DONE
```

확인 포인트:
- `[load] base=...` `[load] vram alloc: ~3GB` 가 떠야 정상.
- `FAILED: ...`로 끝나면 의존성 / VRAM / HF 토큰 문제. README "가정 & 제약" 참고.

### 3. 본 학습 (수 시간, 디스패치 절대 부적합)

별도 PowerShell 창에서 background로 띄우는 걸 권장.

```powershell
# 본 학습 (3 epoch, ~3~5시간 예상 RTX 3080 기준)
python -u src/train_qlora.py > train.log 2>&1
```

진행 확인 (다른 창에서):
```powershell
Get-Content train.log -Wait
# 또는
Get-Content train.log -Tail 20
```

산출물:
- `ckpt/checkpoint-*/` — 중간 체크포인트 (save_steps=200 마다, 최대 3개 유지)
- `ckpt/final/` — 최종 adapter + tokenizer + train_meta.json
- `train.log` — 학습 로그 (sentinel: 마지막에 `DONE` 또는 `FAILED`)

중간에 죽으면:
```powershell
python -u src/train_qlora.py --resume > train.log 2>&1
```

### 4. 단일 추론 (smoke check)

```powershell
"나 오늘 발표 망한 듯" | Out-File -Encoding utf8 input.txt
python -u src/infer.py --adapter ckpt/final --input-file input.txt
```

`=== 사고 ===` / `=== 답변 ===` 두 블록이 콘솔에 찍힘. think 블록이 비었으면 학습이 덜 됐거나 chat template 미스매치.

### 5. PLAY7 평가셋 회귀 (50건 + 30건)

```powershell
# 합성 50건
python -u src/eval_against_baseline.py --adapter ckpt/final `
  --cases eval/cases.jsonl --tag play9_synth

# 자막 30건
python -u src/eval_against_baseline.py --adapter ckpt/final `
  --cases eval/cases_youtube.jsonl --tag play9_youtube
```

→ `reports/run_play9_synth_<ts>.jsonl`, `reports/run_play9_youtube_<ts>.jsonl`.

이 jsonl은 PLAY7의 `bench.py` 출력과 같은 스키마(`case_id`, `input`, `thoughts`, `reply`, `category`). PLAY7의 `judge.py`로 그대로 채점 가능:

```powershell
cd ..\PLAY7_microstyle_prompt
python -u src/judge.py `
  --input "..\PLAY9_microstyle_lora\reports\run_play9_*.jsonl" `
  --backend ollama --judge-model gemma3:12b
```

## 입력 / 출력

- **입력:**
  - `data/final_dataset.chat.jsonl` (PLAY8 부트스트랩 시 복사한 사본, 1,411건)
  - `eval/cases.jsonl` (PLAY7 합성 50건)
  - `eval/cases_youtube.jsonl` (PLAY7 자막 30건)
- **출력:**
  - `data/train.jsonl`, `data/val.jsonl`
  - `ckpt/final/` (LoRA adapter)
  - `reports/dataset_stats.md`, `reports/run_play9_*.jsonl`

## 가정 & 제약

### PLAY 독립성
- `data/final_dataset.chat.jsonl` / `data/final_dataset.dual.jsonl`은 PLAY8에서 복사한 사본. PLAY8가 데이터를 갱신해도 PLAY9는 영향받지 않으며, 명시적으로 다시 복사해야 반영.
- `eval/`도 마찬가지로 PLAY7 사본. PLAY7 코드(`judge.py`, `score.py`)는 채점할 때만 호출하는 외부 도구로 취급.

### 베이스 모델 선택
- 기본 `google/gemma-4-E4B-it` — ollama `gemma4:e4b`와 같은 라인 (Gemma 4, 8B params, effective 4B edge variant). 사용자 의도와 일치.
- **주의**: 이 repo id는 Gemma 3 / 3n 네이밍 패턴 추론값. HF에서 정확한 id 확인 필요. 다르면 `--base-model google/실제-id`로 override.
- fallback: `google/gemma-3n-E4B-it` (Gemma 3n, 이전 세대) → `google/gemma-3-4b-it` (텍스트 전용 4B) → `google/gemma-2-2b-it` (가장 안전).

### 학습 하이퍼파라미터의 근거
- **max_seq_length=1280**: `prepare_dataset.py`의 char-기반 추정 (p99 char 921 × 1.3 ≈ 1197 토큰). 실측은 train 시작 시 첫 8샘플로 한 번 더 찍힘.
- **batch=1 × grad_accum=8 = effective batch 8**: 10GB VRAM + 4B 모델 + seq 1280 + gradient checkpointing 기준 안전선.
- **lr=2e-4, cosine, warmup=3%**: QLoRA 표준 (QLoRA 논문 / Unsloth 권장값).
- **epochs=3**: 1,327 train × 3 epoch / effective batch 8 ≈ 498 step. step 당 4~10초 가정 → 약 1~2시간. RTX 3080 실측은 변동 가능.
- **LoRA r=16, alpha=32**: 톤 모방 수준의 SFT에 충분. 모델이 너무 안 따라오면 r=32로.
- **assistant_only_loss=True**: system/user 토큰엔 loss 안 흘림. 답변 + `<think>` 부분만 학습 → 입력 톡 자체를 외우는 부작용 차단.

### Self-distillation 한계 (반복 경고)
- 데이터는 **gemma4:e4b가 자기 자신을 모사한 결과**. 학습된 모델은 base의 사고·말투를 더 정렬되게 흉내내지만, base를 양적으로 능가하기 어렵다.
- PLAY7 평가셋에서 점수 ↑가 보이면 정렬 효과로 해석. ↓이면 데이터 노이즈 / 진지 차단 실패 / 과한 카드 사용 의심.

### 실행 시간 (디스패치 적합도)
- `prepare_dataset.py`: 1초. **디스패치 OK.**
- `train_qlora.py --smoke`: ~10분. **디스패치 부적합.** 사용자가 로컬.
- `train_qlora.py` 본 학습: 1~5시간. **디스패치 절대 부적합.**
- `infer.py` 1건: 5~15초. 디스패치 OK이긴 하나 첫 로딩이 30~60초.
- `eval_against_baseline.py` 50건: 5~15분. **디스패치 부적합.**

### 외부 액션·비용
- HuggingFace 모델 다운로드: ~5~10GB 1회. 디스크 + 네트워크 비용.
- ANTHROPIC API: PLAY9 자체는 호출 안 함. judge에 Claude 쓰면 PLAY7 README 참고.
- 학습은 로컬 GPU. 클라우드 비용 0.

### 시크릿
- `HF_TOKEN` / `HUGGINGFACE_HUB_TOKEN` 환경변수로만. 코드에 박지 않음.
- 라이센스: Gemma는 Hugging Face에서 한 번 Accept 클릭 필요.

### 알려진 Windows 함정
- bitsandbytes는 v0.42+부터 Windows wheel 공식 지원. 그 이전 버전이 깔리면 `ImportError` → `pip install --upgrade bitsandbytes`.
- `pip install -r requirements.txt`만 하면 torch가 CPU-only로 깔릴 수 있음. **반드시 CUDA 12.x torch를 먼저 별도 설치.**
- 한글 콘솔 mojibake: `infer.py`는 `--input-file`로 우회. argparse `--input` 직접 쓰면 PowerShell cp949로 깨질 수 있음.
- `gradient_checkpointing_kwargs={"use_reentrant": False}`: peft + grad checkpointing 호환 위해 필수.
- **`PYTHONUTF8=1` 필수**: Python 3.11 Windows 한국어 로케일에서 TRL/transformers 내부 파일을 cp949로 읽다 `UnicodeDecodeError` 발생. 학습/추론 명령 전에:
  ```powershell
  $env:PYTHONUTF8 = "1"
  python -u src/train_qlora.py --smoke > smoke.log 2>&1
  ```
  또는 `-X utf8` 플래그: `python -X utf8 -u src/train_qlora.py ...`

### Gemma 4 E4B 특이사항
- **멀티모달 backbone**: vision tower ~150M + audio encoder ~300M 포함. `AutoModelForCausalLM`으로 로드하면 텍스트 전용 LM 부분만 가져옴. 우리 학습은 텍스트만이라 OK.
- **Per-Layer Embeddings (PLE)**: 파라미터 효율화 기법. LoRA target에 `embed_tokens` 안 넣고 attn/mlp만 잡으면 영향 없음 (현재 설정 그대로 OK).
- **Native think tokens (`<|think|>`, `<|channel>`)**: gemma4가 내장한 reasoning 토큰. **우리 데이터셋은 plain text `<think>...</think>`라 충돌 방지 위해 chat template에 `enable_thinking=False` 명시.** 코드에 try/except로 추가됨.
- **Total params ~8B (effective 4B)**: MatFormer. 4bit QLoRA 시 GPU mem ~5~6GB 예상. RTX 3080 10GB 빠듯하지 않음. OOM이면 max_seq_length 1024로 줄이거나 fallback (`google/gemma-3-4b-it`).

### 미검증 부분 (작성 시점 기준)
- **이 스크립트는 코드만 작성됐고 실제 학습 검증은 사용자가 한다.** smoke 모드(`--smoke`)로 환경 검증 후 본 학습 시작 권장.
- TRL `SFTConfig`의 `assistant_only_loss` 옵션 동작은 chat template이 정확한 generation_prompt 마커를 출력해야 작동. Gemma 3 / 3n 토크나이저에서 안 되면 `DataCollatorForCompletionOnlyLM`으로 fallback 필요.
- `attn_implementation="eager"`: flash-attn 미설치 환경 가정. 설치돼 있으면 `"flash_attention_2"`로 바꿔 속도 ↑.

## 변경 이력
- 2026-05-12 — 최초 생성. PLAY8 dual dataset 1,411건 부트스트랩, prepare_dataset.py로 train 1327 / val 84 split + char 통계(p99 921). QLoRA 학습 스크립트(train_qlora.py), 단일 추론(infer.py), PLAY7 평가셋 회귀(eval_against_baseline.py), requirements.txt 작성. 학습은 디스패치 부적합이라 사용자 로컬 실행 가정.
- 2026-05-12 — **베이스 모델 정정**: `google/gemma-3-4b-it` → `google/gemma-4-E4B-it`. transformers `>=4.55` 으로 상향. chat template에 `enable_thinking=False` 명시. PYTHONUTF8=1 필요 표기.
- 2026-05-12 — **프레임워크 전환: raw stack → Unsloth.** Gemma 4 + QLoRA + Windows 조합에서 raw transformers/peft/trl/bnb 호환성 6번 연속 깨짐 (cp949, gemma3→4, bnb Params4bit, torchvision ABI, transformers 4.57.3 tokenizer too old, transformers 5.5+ vs bnb 0.49 충돌). Unsloth는 검증된 의존성 번들 + 2~5x 빠름 + 50~80% 메모리 절약. `unsloth.FastModel.from_pretrained` + `get_peft_model` + `train_on_responses_only`로 재작성. 베이스 default → `unsloth/gemma-4-E4B-it`. requirements.txt 대폭 단순화 (unsloth 하나로 transformers/peft/trl/bnb 다 따라옴).
