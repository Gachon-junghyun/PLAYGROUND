# PLAY8_microstyle_dataset

## 목적
PLAY7가 50건 평가셋과 v3 inner-monologue 프롬프트만 검증했다면, **PLAY8은 학습용 데이터셋 공장.** 자막 → 친구 톤 묶음 → v3 사고/답변 파이프 → `(input, thoughts, reply)` 트리플 수천 건으로 변환한다. Phase 4 LoRA 학습이 곧장 먹을 수 있는 SFT 포맷으로 출력.

## 데이터 흐름

```
raw_transcripts/*.txt
    ↓ chunk_transcripts.py  (연속 2~3줄 → input, 친근 필터)
data/input_candidates.jsonl
    ↓ generate_triples.py    (v3 inner monologue, ollama chat, think:false)
data/triples.raw.jsonl
    ↓ filter_quality.py      (이모지/길이/한국어/누설 자동 필터)
data/triples.filtered.jsonl
    ↓ build_dataset.py        (HF chat / TRL dual 포맷 + 통계)
data/final_dataset.chat.jsonl
data/final_dataset.dual.jsonl
reports/summary.md
```

## 실행법

### 0. 사전 준비
- Ollama 가동 + `gemma4:e4b` (또는 다른 모델) 풀.
- `raw_transcripts/`에 `.txt` 자막 (PLAY 부트스트랩 시 PLAY7에서 복사함).

### 1. Chunking (수 초)
```powershell
python -u src/chunk_transcripts.py
# --min-size 2 --max-size 3 --per-source-cap 80 --total-cap 2000
```
→ `data/input_candidates.jsonl` (현재 자료 기준 ~1,450건)

### 2~4. Triple 생성 + 필터 + 빌드를 한 번에 (권장)

**디스패치 부적합.** 1,400건 × ~15초 = 약 6시간. 로컬 별도 PowerShell 창에서 띄운다.

```powershell
# 안전한 풀 실행 (resume 기본, generate → filter → build 자동 체이닝)
cd C:\Users\fivep\OneDrive\Desktop\PLAYGROUND\PLAY8_microstyle_dataset
python -u src/run_pipeline.py --model gemma4:e4b > pipe.log 2>&1
```

`pipe.log`에는 단계마다 진행 라인 + 각 단계 끝의 `DONE` / `FAILED` sentinel + 최종 `DONE: pipeline complete`.

### 진행 상황 확인 (다른 PowerShell 창에서)

```powershell
# 진행 카운트
(Get-Content data/triples.raw.jsonl).Length
# = 지금까지 처리된 트리플 수

# 마지막 로그
Get-Content pipe.log -Tail 5

# 실시간 follow
Get-Content pipe.log -Wait
```

### 중간에 죽으면 그냥 다시 실행

`generate_triples.py`는 출력 파일에 이미 있는 chunk_id를 건너뛴다. 어디서 죽었든 같은 명령으로 이어 실행:

```powershell
python -u src/run_pipeline.py --model gemma4:e4b > pipe.log 2>&1
```

### 단계별 직접 실행 (디버그용)
```powershell
# 일단 5건만 smoke
python -u src/generate_triples.py --model gemma4:e4b --limit 5

# 풀 실행
python -u src/generate_triples.py --model gemma4:e4b --resume

# 자동 필터 (이모지/길이/누설 제거)
python -u src/filter_quality.py

# 최종 SFT 포맷 + 리포트 빌드
python -u src/build_dataset.py
```

## 출력 포맷

### `final_dataset.chat.jsonl` (OpenAI chat 형식)
```json
{
  "messages": [
    {"role": "system", "content": "너는 친구의 톡을 받고 머릿속으로..."},
    {"role": "user", "content": "<친구가 보낸 톡>"},
    {"role": "assistant", "content": "<think>\n<자기 사고>\n</think>\n<실제 답변>"}
  ],
  "meta": {"chunk_id": "...", "source_path": "...", "model": "..."}
}
```

### `final_dataset.dual.jsonl` (TRL SFTTrainer 호환)
```json
{
  "prompt": "<친구가 보낸 톡>",
  "completion": "<think>\n<사고>\n</think>\n<답변>",
  "meta": {...}
}
```

두 포맷 모두 assistant/completion 안에 `<think>...</think>` 태그로 사고를 포함. **LoRA 학습 시 모델이 "답변 전 한 번 사고하는 습관" 자체를 익히게 됨.** HER-Dataset의 dual-layer thinking 컨셉과 정렬.

## 입력 / 출력
- **입력:** `raw_transcripts/*.txt` (PLAY 부트스트랩 시 PLAY7에서 복사)
- **출력:** 각 단계의 `data/*.jsonl`, `reports/summary.md`

## 가정 & 제약

### PLAY 독립성
- `raw_transcripts/`, `prompts/thinker.md`, `prompts/speaker.md`는 PLAY8 부트스트랩 시 PLAY7에서 복사한 사본. PLAY7 코드를 import하지 않으며, PLAY7가 변경돼도 PLAY8는 영향 없다.
- PLAY7가 프롬프트를 개선하면 사용자가 명시적으로 PLAY8 prompts/ 디렉토리에 다시 복사해야 반영.

### Chunk 필터 휴리스틱의 한계
- 친근 어미(`잖아`, `거든`, `듯`, `지?` 등) 기반의 간단한 필터. 실제 host 멘트가 친근 어미를 가지면 통과한다.
- 정중 어미(`합니다`, `드립니다` 등)나 마케팅 키워드(`구독`, `영상`) 한 줄이라도 묶음에 있으면 제외.
- 현재 19개 영상 기준 약 1,450건 통과 / 5,000+건 reject.

### 학습 데이터로서의 한계 (검수 필수)
- 트리플은 **모델 자체가 생성한 가상 대화.** 실제 화자가 그렇게 답한다는 보장 없다. self-knowledge distillation에 가깝다.
- Phase 4 LoRA가 이 데이터로만 학습되면 **현재 gemma4:e4b의 사고·말투를 흉내내는 모델**이 된다. base model을 능가하기 어렵다.
- 진짜로 사람 같은 말맛을 익히려면: (1) 사람이 검수해서 명백히 망가진 트리플 제거, (2) 사용자 본인 톡 데이터 / 다른 화자 데이터 추가 혼합.

### 학습량 시그널
- v3 inner monologue 학습에는 최소 **2,000 트리플** 권장 (한 샘플당 thoughts 400자 + reply 25자 ≈ 400~500 토큰이라 시퀀스가 길다).
- 현재 1,450 후보로 풀 생성하면 자동 필터 후 약 1,000~1,200 트리플 확보 예상 → **최소 라인 살짝 부족.** 자막 추가하거나 합성 증강 필요.

### 실행 시간 (디스패치 적합도)
- `chunk_transcripts.py`: 1~2초. **OK.**
- `filter_quality.py`: 1초. **OK.**
- `build_dataset.py`: 1초. **OK.**
- `generate_triples.py`: 한 트리플 ~15초. 1,000건 ≈ **4~5시간.** **디스패치 부적합** — 사용자가 로컬에서 background로.

### Resume
- `generate_triples.py --resume`로 이어 실행 가능. 출력 파일에 이미 있는 chunk_id는 건너뜀.
- 중간에 ollama가 죽으면 `FAILED: ollama_down` sentinel + exit 2. 다시 띄우고 `--resume`.

## 변경 이력
- 2026-05-11 — 최초 생성. transcripts/prompts를 PLAY7에서 복사, 4단계 파이프(chunk → generate → filter → build) 작성. 1,452개 input 후보까지 추출 OK, smoke 5건으로 사이클 검증.
- 2026-05-11 — **v4 디자인 전환: 자막 다음 줄(`reference_after`)을 Thinker에게 "참고 톤"으로 주입.**
  - 동기: 자막은 대화가 아니라 1인 host 독백이라 Y(reply) 정답 없음 → self-distillation 한계. 그래도 자막의 *다음 N줄*에 사람이 어떻게 받았는지의 흔적이 있음 → 그 톤·길이·온도를 모델에게 보여주면 답변이 그 맥락에 더 정렬됨.
  - 변경: `chunk_transcripts.py`가 `reference_after` 필드 추가, `thinker.md`가 참고 톤 활용 규칙 명시, `generate_triples.py`가 prompt에 주입.
  - 검증: smoke 5건에서 모델이 사고에 명시적으로 "참고 톤 보니까... 무시하자/맞추자"라고 처리. 비교 → `results/v3_vs_v4.md`.
  - 240건 풀 진행 중 v5로 전환 → 240건은 `data/archive/triples.v4.jsonl`로 보존.
- 2026-05-11 — **v5 디자인 전환: 개그 카드 4장(콜백/라임/놀리기/비유) 명시.**
  - 동기: v4는 "재미 어디서 낼지"가 추상적. 사용자가 개그의 핵심 메커닉(콜백·라임·놀리기·비유)을 명시적으로 가르쳐야 한다고 지적.
  - 변경: `thinker.md` 사고 단계 5번을 "개그 카드 4장 중 하나 이상 발상"으로 재작성. 각 카드에 정의·예시·안전선 추가 (놀리기는 "ㅋㅋ"/친근 어미로 마무리, 진지 신호 있으면 카드 전부 금지).
  - 검증: smoke 5건에서 모델이 사고에 카드명("콜백", "비유", "놀리기" 등) 명시적으로 적고 답변에 그 카드를 사용.
- 2026-05-12 — **풀 v5 파이프라인 완주.** 1,447건 generate (6.7시간) + filter + build 자동 체이닝.
  - **최종 학습 데이터셋: 1,411 트리플** (filter 후, 19개 영상 균등 분포, 41건 이모지 거름).
  - thoughts median 463자, reply median 33자.
  - **카드 분포**: 콜백 91%, 놀리기 52%, 비유 43%, 라임 1% (한국어 라임 한계).
  - **답변당 카드 수**: 0장 57건(진지 신호) / 1장 99건 / 2장 1,230건 / 3장 25건.
  - **안전 모드**: 29건이 "카드 전부 금지" 모드로 차분 위로 답변. 자동전사 노이즈에서도 잘 발동.
  - 출력: `data/final_dataset.chat.jsonl` (OpenAI chat) + `data/final_dataset.dual.jsonl` (TRL SFT). 둘 다 `<think>...</think>` 포함.
  - 부수 수정: `run_pipeline.py`가 build 단계에서 Windows cp949 stdout 인코딩 에러로 죽음 → 수동으로 build 완료 + wrapper에 utf-8 reconfigure 패치.
