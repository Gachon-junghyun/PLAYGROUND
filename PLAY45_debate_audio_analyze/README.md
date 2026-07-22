# PLAY45_debate_audio_analyze

## 목적
종교(기독교) 2인 토론 녹음을 whisper로 전사하고, 두 화자의 **주장·논증 구조**를
뜯어 "뭐가 부족하고 뭐가 괜찮은지" 분석한다. (전사 = 코드, 분석 = LLM)

## 실행법
사전 준비(설치는 한 번만, 실행 경로 밖):
```powershell
pip install faster-whisper==1.2.1      # 이미 설치돼 있음
# ffmpeg 가 PATH 에 있어야 함 (이미 있음). GPU+CUDA 면 자동 사용.
```

전사 (장시간 — ~1시간 오디오는 GPU large-v3 로 수~십수 분):
```powershell
cd PLAY45_debate_audio_analyze
# 짧게 검증만:  python transcribe.py --model small
python -u transcribe.py > output/run.log 2>&1     # 백그라운드 권장
# 진행: output/run.log 의 [seg N] 라인, 끝나면 DONE / 실패면 FAILED
```

분석 (전사 끝난 뒤):
- `prompts/analysis_prompt.md` 의 프롬프트에 `output/transcript.txt` 를 붙여
  LLM(Claude 등)에게 시킨다 → 결과를 `output/analysis.md` 로 저장.
- 이 PLAY 를 디스패치로 돌리면 에이전트가 전사 후 곧바로 분석까지 써서
  `output/analysis.md` 를 만든다.

## 입력 / 출력
- 입력: `input/bokjeong2.m4a` (루트의 `복정동 2.m4a` 를 ASCII 이름으로 복사한 것).
  다른 파일은 `--input <경로>`.
- 출력:
  - `output/segments.jsonl` — `{i,start,end,text}` 줄 단위 (분석 원천)
  - `output/transcript.txt` — `[mm:ss-mm:ss] 텍스트` (사람이 읽는 용)
  - `output/analysis.md` — 화자별 주장·논리 분석 (LLM 산출)
  - `output/coaching_playbook.md` — 형(A) 매 발화에 B가 안 싸우고 받아치는 한 수씩 코칭
    (논제 4구간을 subagent 병렬로 훑어 합본)
  - `output/coaching_session.md` — 전사 이후 B와 진행한 코칭 대화 정리(항복 지점 분석·칭찬·
    CCM 논증 해부·진인사대천명 warrant·역전 가능성). `.docx`도 to_docx.py로 생성
  - `output/analysis.docx` — 위 분석을 보기 좋게 변환한 Word 문서
    (`python to_docx.py`, python-docx==1.2.0 필요)
  - `output/run.log` — 전사 진행/sentinel 로그

## 가정 & 제약
- **화자 분리(diarization)는 코드가 안 한다.** pyannote.audio 가 설치돼 있지 않고,
  HuggingFace 게이트 모델 토큰 + 무거운 의존이라 디스패치 45초/경량 원칙에 안 맞음.
  대신 화자 A/B 귀속을 **전사본의 말차례·내용 기반으로 LLM 이 추정**한다. 구조화된
  2인 토론은 턴이 길어 대체로 안정적이나 완벽하진 않음 — 애매 구간은 `[불확실]` 표기.
  진짜 화자 분리가 필요하면: `pip install pyannote.audio` + HF 토큰 후 별도 단계 추가.
- 입력 파일명이 NFD(한글 자모 분해) 정규화라 PowerShell/ffmpeg 직접 경로 매칭이 깨졌다.
  그래서 `input/bokjeong2.m4a` (ASCII) 로 복사해 사용. 루트 원본은 그대로 둠.
- 오디오 길이 약 **3705초(≈62분)**. GPU(CUDA) 가정. GPU 없으면
  `--device cpu --compute-type int8` (느림). large-v3 한국어 인식 기준.
- whisper 는 오인식이 있다(고유명사·성경 인용·동음이의). 분석 시 명백한 오류는
  `(전사오류?)` 로 표기하고 의미 위주로 해석.
- 전사는 ~62분 오디오라 디스패치 단일 Bash(45초)를 초과 → 반드시 background 패턴.
  세션이 짧으면 사용자가 `transcribe.py` 를 미리 돌려 `output/` 를 채워둬야 분석 가능.

## 변경 이력
- 2026-06-14: PLAY 생성. PLAY33 whisper 전사 로직을 단건 로컬 파일용으로 이식
  (transcribe.py), 화자분리 없이 LLM 귀속 방식 채택, 분석 프롬프트(prompts/) 작성.
- 2026-06-14: bokjeong2.m4a(61:45) 전사 완료 → segments.jsonl(1650줄)/transcript.txt,
  화자 A(형/옹호)·B(동생/도전) 귀속 후 논증 분석 작성 → output/analysis.md.
- 2026-06-14: analysis.md → analysis.docx 변환 스크립트(to_docx.py) 추가, Word 문서 생성.
- 2026-06-14: 논제 4구간(00:00~14:30 / 14:30~31:10 / 31:00~45:00 / 45:00~61:45)을
  subagent 병렬로 훑어 형(A) 발화별 받아치기 한 수씩 → output/coaching_playbook.md 합본.
  화자 라벨 주의: [57:14~57:39]은 B 발화(전사 추정 라벨 오인 교정).
- 2026-06-14: 코칭 대화 합본 coaching_session.md(+docx) 생성. 단서 기록 — 음악 논증의
  핵심 논거(진인사대천명↔음악)는 녹음 시작 전 다른 장소에서 편 것이라 전사본엔 미포착.
