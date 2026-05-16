# PLAY7_microstyle_prompt

## 목적
Korean Microstyle LLM 프로젝트의 **Phase 1 — 프롬프트 프로토타입 + 평가 인프라.** 학습 없이 Thinker/Speaker 듀얼 레이어를 프롬프트로 구현하고, 모델이 답변하기 전 **"어떻게 받자, 어떤 비유 박자, 펀치라인 어디"** 라는 자연어 사고를 거치게 한다. 4개 후보 모델을 50개 한국어 케이스로 비교 가능.

## 디자인 핵심 — Inner Monologue

```
사용자 톡
   ↓
Thinker  →  한국어 자연어 사고
              "이거 진짜 망한 건 아니고 가벼운 푸념 같다.
               능청으로 받자. 무대에서 신발끈 밟은 정도로
               재정의하면 재밌을 것 같은데."
   ↓
Speaker  →  실제 한 줄 답변
              "ㄱㅊㄱㅊ 망한 게 아니라 무대 위에서
               잠깐 신발끈 밟은 거지 뭐"
```

분류표(humor_level/risk 같은 JSON 라벨)를 채우는 게 아니라, 친구가 톡을 받고 머릿속으로 "어떻게 받자"를 굴리는 흐름 자체를 출력한다. 최종 결과물에 사고 + 답변이 함께 보여서, 사용자가 모델이 **왜** 이렇게 답했는지 추적 가능.

진지 신호(죽음·이별·우울·해고·강한 자기비하)가 있으면 Thinker가 명시적으로 "농담 차단" 모드로 전환하고, Speaker는 비유·받아치기 없이 차분한 위로만 한다.

## 산출물
- `prompts/thinker.md` — 자연어 inner monologue 생성 프롬프트
- `prompts/speaker.md` — Thinker 사고를 받아 한 줄 답변 생성
- `prompts/judge.md` — 5축 1~5점 채점 프롬프트
- `eval/cases.jsonl` — 50개 합성 케이스 (안전 기대값 humor_level/risk 포함)
- `eval/cases_youtube.jsonl` — PLAY7 자체 자막에서 추출한 30개 실제 화자 발화
- `eval/rubric.md` — 5축 채점 기준
- `src/extract_youtube_cases.py` — `youtube_whisper/transcripts/` 에서 cases 추출
- `src/run_ollama.py` — 단일 입력 → 사고 + 답변 출력
- `src/bench.py` — `--cases` 옵션으로 임의 jsonl 평가, `--tag`로 출력 파일 구분
- `src/judge.py` — LLM-as-judge로 reply 채점 (ollama 또는 Claude API)
- `src/score.py` — 결과 집계 및 비교 리포트 생성
- `youtube_whisper/` — 사용자가 PLAY6에서 옮겨둔 YouTube 자막 파이프라인 + transcripts (PLAY7 자체 데이터)

`cases.jsonl`의 `expected_humor_level` / `expected_risk` 필드는 **안전성 검증용 라벨**로만 쓴다 (slope-grief 같은 진지 카테고리에서 모델이 까불지 않는지). Thinker는 더 이상 JSON 분류를 출력하지 않으므로, judgment vs expected 일치율은 더 이상 평가 축이 아니다.

## 실행법

### 0. 사전 준비 (디스패치 환경 밖에서, 한 번만)

[ollama.com](https://ollama.com) 설치 후 후보 모델 풀:

```powershell
ollama serve   # 백그라운드 (보통 자동 시작됨)
ollama pull gemma3:4b
ollama pull gemma4:e4b
ollama pull exaone3.5:2.4b
ollama pull qwen2.5:3b
# Judge용 더 큰 모델 (선택)
ollama pull gemma3:12b
```

### 1. 한 케이스 실험 (smoke)

**Windows PowerShell 한글 인자 함정:** 콘솔 코드페이지가 cp949면 `--input "나 오늘 발표 망한 듯"`이 깨져서 모델에 들어간다. 두 가지 회피책:

```powershell
# 방법 A: 콘솔을 UTF-8로 (한 번만)
chcp 65001
python -u PLAY7_microstyle_prompt/src/run_ollama.py --model gemma4:e4b --input "나 오늘 발표 망한 듯"

# 방법 B: 파일에서 읽기 (가장 안전)
"나 오늘 발표 망한 듯" | Out-File -Encoding utf8 input.txt
python -u PLAY7_microstyle_prompt/src/run_ollama.py --model gemma4:e4b --input-file input.txt
```

표준출력에 사람이 읽기 좋은 narrative + `{input, thoughts, reply, ...}` JSON 둘 다.

### 2. 50케이스 벤치 (합성 평가셋)

```powershell
python -u PLAY7_microstyle_prompt/src/bench.py `
  --models gemma3:4b gemma4:e4b exaone3.5:2.4b qwen2.5:3b
```

→ `results/run_<model>_<ts>.jsonl` 모델별 파일.
한 모델 × 50케이스 약 12~15분 (v3 inner monologue 기준).

### 2-b. 30케이스 벤치 (실제 자막 발화)

```powershell
# 자막에서 case 추출 (자체 transcripts 사용, PLAY6 무관)
python -u PLAY7_microstyle_prompt/src/extract_youtube_cases.py --n 30

# 추출된 case로 벤치
python -u PLAY7_microstyle_prompt/src/bench.py `
  --models gemma4:e4b `
  --cases eval/cases_youtube.jsonl `
  --tag youtube
```

→ `results/run_<model>_youtube_<ts>.jsonl`. 한 모델 × 30케이스 약 8분.

### 3. 채점

#### A. 로컬 모델로 채점 (무료, 권장 시작점)

```powershell
python -u PLAY7_microstyle_prompt/src/judge.py `
  --input "PLAY7_microstyle_prompt/results/run_*.jsonl" `
  --backend ollama `
  --judge-model gemma3:12b
```

#### B. Claude API로 채점 (정확도 ↑, 비용 발생)

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
python -u PLAY7_microstyle_prompt/src/judge.py `
  --input "PLAY7_microstyle_prompt/results/run_*.jsonl" `
  --backend claude `
  --judge-model claude-haiku-4-5-20251001
```

200건 채점 시 Haiku 4.5 기준 약 $0.1~0.3 추정. **돈 들어가는 일이므로 사용자 확인 후 실행.**

### 4. 비교 리포트

```powershell
python -u PLAY7_microstyle_prompt/src/score.py
```

→ `results/report_<ts>.md`. 모델별 총점, 축별 점수, 카테고리별 점수, 워스트 5 케이스.

## 입력 / 출력

- **입력:** 사용자가 직접 (`run_ollama.py`) 또는 `eval/cases.jsonl` (`bench.py`).
- **출력:**
  - `results/run_<model>_<ts>.jsonl` — 모델 응답 + Thinker JSON
  - `results/judged_run_<model>_<ts>.jsonl` — 위 파일 + 5축 점수
  - `results/report_<ts>.md` — 사람이 읽는 비교 리포트

## 가정 & 제약

### 모델 후보 4개의 근거 (2026-05 기준 확인)
- `gemma4:e4b` — Google Gemma 4 (2026-04 발표), effective 4B edge variant. 다국어 140+ 지원. (실재 확인됨, 원본 프로젝트의 의도와 일치)
- `gemma3:4b` — Gemma 3 4B. 128K context. 비교 베이스라인.
- `exaone3.5:2.4b` — LG AI Research 한국어 특화 bilingual. 한국어 zero-shot 가장 강할 후보.
- `qwen2.5:3b` — Qwen 다국어. 한국어 적당, instruction tuning 안정.

### 사전 준비 의무
- **ollama 설치 + 모델 pull은 사용자가 미리.** 디스패치 45초 안에 다운로드 불가.
- `ollama serve`가 `localhost:11434`에서 떠 있어야 함. 안 떠 있으면 `bench.py`가 `FAILED: ollama not reachable` 종료.

### 데이터셋 50개의 한계
- 카테고리 분포: light_fail(8) / small_talk(8) / agreement(6) / refusal(4) / banter(6) / serious_grief(8) / self_deprecation(4) / relationship_conflict(4) / edge_ambiguous(2).
- 사용자 1인(작성자) 관점의 케이스. 다양한 인구·세대 말투 커버 안 됨.
- 한 발화만, 멀티턴 미포함. Phase 2부터 멀티턴 추가 권장.

### Judge 한계
- LLM-as-judge는 안정적이지만 완벽하지 않음. `eval/rubric.md`의 "사람 spot-check 70% 일치" 기준으로 검증할 것.
- 작은 로컬 judge 모델은 JSON 출력이 불안정할 수 있음. 이때는 `--backend claude` 권장.

### Ollama Reasoning 모델 주의 (`think: false`)
- **Gemma 4 / Qwen 3** 같은 reasoning-capable 모델은 기본적으로 사고 토큰을 먼저 출력해서 응답 슬롯이 비어버린다.
- 본 PLAY는 `run_ollama.py` / `judge.py`에서 ollama chat payload에 **`think: false`** 를 명시해 reasoning을 끈다.
- 사용자가 reasoning 모드의 사고 흔적을 실험하고 싶으면 코드에서 해당 라인을 지우고 `num_predict`를 크게(예: 3000) 설정.
- 비reasoning 모델(gemma3, gemma2, exaone 등)에서는 `think: false`가 무시됨 — 안전하게 켜 둬도 됨.

### 실행 시간 (디스패치 적합도)
- `run_ollama.py` 한 케이스: ~3~10초. **디스패치 OK.**
- `bench.py` 50케이스 × 1모델: ~5~15분. **디스패치 부적합.** `run_in_background: true`로 띄우고 sentinel(`DONE`/`FAILED`) 폴링.
- `bench.py` 50케이스 × 4모델: ~30~60분. **디스패치 부적합.** 사용자가 로컬에서 분리 실행 권장.
- `judge.py` 200건: ollama 로컬 ~10~20분 / Claude API ~3~5분.
- `score.py`: 1초 이내.

### 외부 액션·비용
- ollama는 로컬 무료.
- Claude judge는 비용 발생 → 사용자 명시 확인 필요.
- 데이터·결과 모두 로컬. 외부 업로드 없음.

### 시크릿
- `ANTHROPIC_API_KEY`는 환경변수로만 받음. 코드에 박지 않음. 사용자가 `$env:ANTHROPIC_API_KEY = "..."` 로 세팅.

### 다른 PLAY와의 관계
- 본 PLAY는 **독립적**. `PLAY5_FUNNY_LLM`(원본 설계 문서) / `PLAY6_FUNNY_LLM_GPT`(데이터 수집 시도) 어느 쪽도 import하지 않는다.
- 컨셉의 출처는 PLAY5의 `korean_microstyle_llm_project.md`와 `new_idea_claude.md`. 본 PLAY의 4축 태그(humor_level / reply_function / energy / risk)는 거기서 가져왔다.

## 다음 단계 (Phase 2~ 후보)
1. 본 PLAY로 4모델 비교 → 최고 모델 1개 선정.
2. **PLAY8_microstyle_dataset**: 선정 모델 + Annotator(GPT-4o 또는 Claude)로 Speaker용 2~5k 데이터셋 합성. 사용자 확인 후 진행.
3. **PLAY9_microstyle_lora**: QLoRA 학습. 평가셋 50개는 본 PLAY 것 그대로 재사용 (절대 학습에 안 넣음).

## 변경 이력
- 2026-05-11 — 최초 생성. Phase 1 풀세트(프롬프트 + 50케이스 + rubric + 4스크립트).
- 2026-05-11 — 사용자 환경(ollama, gemma4:e4b)에서 smoke 3케이스 검증 OK. 발견·수정 사항:
  - PowerShell `--input` 인자에서 한글 mojibake → `--input-file` 옵션 추가 + chcp 65001 안내.
  - gemma4:e4b가 reasoning 모드로 응답 슬롯이 비는 문제 → ollama chat payload에 `think: false` 명시.
  - `/api/generate` → `/api/chat`으로 통일, `ensure_ascii=False` + `Content-Type charset=utf-8`로 한글 페이로드 안정화.
  - 케이스당 약 10초(Thinker ~6s + Speaker ~4s, gemma4:e4b 기준). 50케이스 풀 벤치는 약 8~10분.
- 2026-05-11 — **v1 (분류 JSON)** `gemma4:e4b` 풀 50케이스 베이스라인 완료, 분석은 [results/baseline_analysis.md](results/baseline_analysis.md). 핵심: risk match 84% / humor match 52%, serious_grief 8/8 안전, banter/light_fail에서 너무 점잖음 → 다음 사이클 트리거.
- 2026-05-11 — **v3 (inner monologue) 디자인 전환.** Thinker가 4축 JSON 대신 한국어 자연어 사고 ("어떻게 받자", "이 비유 박자", "펀치라인 여기")를 출력. Speaker가 그 사고를 받아 답변. 결과에 thoughts + reply 모두 보존.
  - Smoke 3케이스에서 사고-답변 일관성 검증: L1-01 "신발끈 비유 발상" → 답변에 그대로 박힘. L1-03 "배터리 1% 비유" → 답변에 배터리 방전 비유 + 후속 질문.
  - 케이스당 latency ~17초로 늘어남 (자연어 토큰 더 많음). 50케이스 풀 벤치 ~14분.
- 2026-05-11 — **v3 풀 50케이스 베이스라인 완료**, 분석 [results/v3_analysis.md](results/v3_analysis.md). 핵심:
  - 50/50 OK, thoughts median 368자 / reply median 25자 (가이드 잘 따름).
  - **진지 카테고리 16/16 안전.** 모델이 사고에 명시적으로 "농담 금지/차단" 적고 답을 만든다.
    - H1-03 사고 인용: "지금 당장 'ㄱㅊㄱㅊ' 같은 거 보내면 진짜 최악일 듯."
    - H3-01 사고 인용: "여기서 만약 내가 가볍게 받아치면 진짜 힘들 때 더 상처만 줄 것 같아."
  - **받아치기·잡담에서 모델이 사고에서 비유를 발상한 뒤 답변에 그 비유를 박는 일관성** 확인 — Phase 4 LoRA 학습 시 입력 → 사고 → 답변 한 시퀀스 학습 가능.
- 2026-05-11 — **사용자가 youtube_whisper 파이프라인을 PLAY7 안에 옮김** (PLAY 독립성 확보). 추가 작업:
  - `src/extract_youtube_cases.py` — `youtube_whisper/transcripts/` 에서 직접 cases 추출 (backup/ 제외, 6개 영상 × 5건 균등 분포).
  - `bench.py`에 `--cases` / `--tag` 옵션 추가 → 합성·자막 평가셋 둘 다 평가 가능.
- 2026-05-11 — **자막 30건 v3 풀 베이스라인 완료**, 합성 vs 자막 비교 [results/youtube_vs_synthetic.md](results/youtube_vs_synthetic.md). 핵심:
  - 30/30 OK, 자막 입력이 더 짧아서 latency 11.5s/case (합성 13.3s 대비 ↓).
  - **모델이 자동전사 오탈자(국언의 참고사, 폼 롤리 롤리)를 사고에서 "의미 모름을 인정"하고 받아치는 재료로 사용** — 입력 노이즈 강건성 확인.
  - **자막에서 더 과감한 펀치라인 발상**: YT-05 "66가지" → "국가 단위 프로젝트급", YT-13 "30년 차 개그맨/20년 차 DJ" → "즉흥성 vs 계획" 대비 관찰, YT-29 → "거울 메타포로 칭찬 되돌리기".
  - **자막의 함정**: 입력이 방송 host 멘트라 모델이 "친구 톡"으로 가정하면 의도 추론 실패. Phase 2에서 친구 톤 발화 선별 필터 필요.
