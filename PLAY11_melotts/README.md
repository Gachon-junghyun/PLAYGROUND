# PLAY11_melotts

## 목적
MyShell `MeloTTS`로 텍스트를 WAV로 합성하는 얇은 CLI 래퍼. 다국어(EN/KR/JP/ZH/ES/FR), 화자, 속도 옵션 지원. 격리된 venv로 글로벌 환경(unsloth 등) 안 건드린다.

## 실행법

### 1) 사전 준비 — 한 번만 (디스패치 외부에서)

`setup_env.py`가 모든 무거운 작업을 한다: venv 생성, torch CPU 설치, MeloTTS git 설치, NLTK 리소스, **unidic JP 사전 다운로드(~250MB)**, eunjeon shim 설치. 끝까지 5~10분.

```powershell
cd PLAY11_melotts
python -u setup_env.py
```

성공하면 마지막 줄에 `DONE`. 실패면 `FAILED: step N`.

### 2) 합성

venv의 python을 직접 호출 (activate 안 해도 됨):

```powershell
# 한국어
.venv\Scripts\python.exe synth.py --lang KR --text "안녕하세요" --out out/ko.wav

# 영어 (화자 선택)
.venv\Scripts\python.exe synth.py --lang EN --text "Hello, this is a test." --speaker EN-US --out out/en.wav --speed 1.0

# 파일 입력
.venv\Scripts\python.exe synth.py --lang KR --text-file examples.txt --out out/ko_file.wav --speed 0.9

# 다른 언어
.venv\Scripts\python.exe synth.py --lang JP --text "こんにちは" --out out/jp.wav
.venv\Scripts\python.exe synth.py --lang ZH --text "你好" --out out/zh.wav
.venv\Scripts\python.exe synth.py --lang ES --text "Hola" --out out/es.wav
.venv\Scripts\python.exe synth.py --lang FR --text "Bonjour" --out out/fr.wav
```

첫 합성 때 HF Hub에서 언어별 모델 가중치(~수백 MB)를 받아 캐시한다. 두 번째부터는 빠르다.

### 3) 강의 스크립트 일괄 합성 — `tts_lecture.py`

구조화된 스크립트를 받아 슬라이드별 WAV로 출력. 두 가지 포맷을 자동 인식한다.

```powershell
# 전체 합성 (기본 출력: out/slides/)
.venv\Scripts\python.exe tts_lecture.py 코스닥3000_강의스크립트.txt

# 특정 슬라이드만 (재시도용)
.venv\Scripts\python.exe tts_lecture.py 코스닥3000_강의스크립트.txt --only 3,7,14

# 출력 디렉토리 지정 (절대경로 또는 PLAY11 기준 상대경로)
.venv\Scripts\python.exe tts_lecture.py path\to\script.txt --out-dir out\gic_pragmatics
```

출력: `<out-dir>/slide_NN.wav` + 파싱 결과 `<out-dir>/_parsed.txt`. 한 슬라이드 실패해도 다른 건 계속 진행.

**포맷 A — 태그 블록형 (예: `코스닥3000_강의스크립트.txt`):**
- 슬라이드 헤더: `슬라이드 N.  <제목>` (decoration 라인 `───` 사이에 있음)
- 블록 태그: `[화면]`, `[발화]`, `[핵심]` 각각 줄 시작
- 합성 대상: 다음 태그나 decoration 라인을 만날 때까지의 `[발화]` 이후 텍스트만

**포맷 B — 괄호 헤더형 (예: GIC `대화_화용론_유머_프레이밍_강의스크립트.txt`):**
- 슬라이드 헤더: `[슬라이드 N. <제목>]` (한 줄)
- 본문: 헤더 다음부터 다음 헤더(또는 EOF) 전까지의 모든 본문 줄. 구분선(`====`/`───`/`═══`)은 무시.
- 합성 대상: 본문 전체 (별도 [발화] 태그 없음)

**자동 인식 규칙:** 파일에 `[슬라이드 N. ...]` 패턴이 한 줄이라도 있으면 포맷 B, 아니면 포맷 A.

**공통:**
- 본문 줄바꿈은 한 칸 공백으로 평탄화 (MeloTTS 문장 분리기에 친화적)
- decoration 라인: `═══`, `───`, `====` 5자 이상 모두 무시

**텍스트 정규화:**
- `+숫자` → `플러스 숫자` (MeloTTS 한국어 g2p가 `+` KeyError로 죽음). 그 외 단독 `+`는 공백으로.
- 다른 특수문자(①②③④, —, %, 따옴표, 숫자+단위)는 라이브러리 g2p가 처리.

## 입력 / 출력
- **입력:**
  - `--text "..."` 또는 `--text-file <path>` (UTF-8) — 둘 중 하나 필수
  - `--lang` ∈ `{EN, KR, JP, ZH, ES, FR}` 필수
  - `--speaker` (선택): 영어만 의미 있음. `EN-US, EN-BR, EN_INDIA, EN-AU, EN-Default`. 미지정 시 언어별 기본값
  - `--speed` (기본 1.0). 0.5~2.0 권장
  - `--device` (기본 `auto`): `auto / cpu / cuda / cuda:0 / mps`. setup이 torch CPU만 깔았으므로 GPU 쓸 거면 venv에 CUDA torch 별도 설치 필요
  - `--out` WAV 출력 경로 (필수, 디렉토리 자동 생성)
- **출력:** WAV 44.1kHz mono. stdout에 `wrote <path> (<lang>/<speaker>, speed=<x>)` 한 줄.

## 가정 & 제약

- **Windows 한정 환경 가정.** 사용자 환경이 Windows 10 + Python 3.11. 다른 OS에선 setup_env.py의 venv 경로(`.venv/Scripts/python.exe`)와 eunjeon shim 필요 여부가 다르다.
- **격리 venv.** 글로벌 환경엔 transformers 5.5.0 + unsloth가 깔려 있고, MeloTTS는 `transformers==4.27.4` 하드 핀이라 글로벌에 깔면 unsloth가 깨진다. 그래서 `.venv` 안에 격리. 이 디렉토리는 ~2GB, 한 PLAY 안에 두는 게 PLAY 독립성 원칙에 맞다.
- **첫 실행 모델 다운로드.** 언어별 첫 합성은 HF에서 가중치를 받는다(~수백 MB, 분 단위). 디스패치 45초 제한에 거의 확실히 잘림. 사용자가 합성하려는 언어를 미리 1회씩 워밍업하라:
  ```powershell
  .venv\Scripts\python.exe -c "from melo.api import TTS; TTS(language='KR', device='cpu')"
  ```
- **unidic 사전 필수.** MeloTTS는 `melo/text/cleaner.py`에서 모든 언어용 모듈을 모듈-레벨 import 한다 → KR 합성에도 일본어 `MeCab.Tagger()`가 초기화되어야 함 → unidic 사전 필수. setup_env.py가 자동 다운로드.
- **KR 정확도 약간 손실 (eunjeon shim 사용).** 진짜 `eunjeon`(한국어 MeCab 바인딩)은 Windows에서 빌드하려면 Visual Studio Build Tools가 필요한데 사용자 환경에 없다. `_shims/eunjeon/`에 `Mecab.pos()`가 빈 리스트를 반환하는 스텁을 두고 setup_env.py가 venv에 설치. 영향: g2pkk의 POS 기반 발음 규칙(조사 `의`, 어미 `ㄹ`, 합성어 등)이 안 먹어서 일부 어휘 발음이 룰베이스로만 처리됨. 짧고 일반적인 문장은 자연스럽게 들리지만, 복잡한 합성어/관용 표현에서 부정확할 수 있음. 진짜 eunjeon이 필요하면 VS Build Tools 설치 후 `.venv\Scripts\python.exe -m pip install eunjeon` (shim을 덮어씀).
- **CPU 전용.** setup이 torch CPU 휠을 설치한다. 짧은 문장(~5초 음성)은 CPU로 5~15초. GPU 쓰려면 venv에 CUDA torch를 별도 설치하고 `--device cuda`.
- **속도 옵션 범위 검증 안 함.** 0이나 음수 주면 라이브러리가 에러.
- **장문 처리:** MeloTTS는 내부에서 문장 split 후 concat. 매우 긴 입력은 시간 오래 걸림 → 디스패치엔 부적합. 100~200자 이내 권장.
- **검증한 동작:** KR 한 문장("안녕하세요. 멜로 티티에스 한국어 합성 테스트입니다."), EN 한 문장("Hello, this is a MeloTTS English synthesis test."). 둘 다 정상 WAV 출력 확인. JP/ZH/ES/FR은 미검증 — 첫 호출 시 각 언어별 모델 다운로드와 g2p 의존성이 추가로 필요할 수 있음.

## 변경 이력
- 2026-05-14 — 최초 생성. synth.py CLI + setup_env.py(자동 venv 격리 설치) + eunjeon shim(_shims/) + KR/EN 합성 검증.
- 2026-05-14 — tts_lecture.py 추가. 구조화된 강의 스크립트(슬라이드/[발화] 형식) → 슬라이드별 WAV 일괄 합성. `+숫자` 정규화. `코스닥3000_강의스크립트.txt` 18 슬라이드 합성 완료(총 66MB).
- 2026-05-16 — tts_lecture.py 포맷 B(괄호 헤더 `[슬라이드 N. ...]`, 본문 전체 합성) 자동 인식 추가. `--out-dir` 옵션 추가. GIC `대화_화용론_유머_프레이밍_강의스크립트.txt` 29 슬라이드 합성(`out/gic_pragmatics/`).
