# venv 가이드

PLAY마다 의존성 성격이 달라서 단일 venv로 다 묶지 않는다. 아래는 코드/README/requirements를 훑고 추천한 분할.

## 루트 `.venv/` — 가벼운 데이터/스크립트용 (Python 3.11)

이 저장소를 clone 한 직후 바로 쓸 수 있도록 루트에 빈 venv 하나를 만들어둔다. 활성화는 PowerShell에서:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

이 venv에 깔 만한 **공통 라이트 의존성**(필요할 때만 깔아라, 미리 다 깔지 마라):

```powershell
pip install numpy pandas scipy scikit-learn matplotlib requests beautifulsoup4
```

**여기에 묶어서 돌릴 수 있는 PLAY:**

| PLAY | 추가 의존성 |
|---|---|
| `PLAY1_sync` | `pip install -r PLAY1_sync/requirements.txt`  (google-api-python-client 등) |
| `PLAY2_chart_embedding` | `pip install FinanceDataReader yt-dlp` (text_chart는 PLAY 내부 모듈) |
| `PLAY3_market_timing` | (위 공통만) |
| `PLAY4_news_retrieval` | `pip install feedparser sentence-transformers` — `.env`에 API 키 필요 (커밋 금지) |
| `PLAY6_FUNNY_LLM_GPT` | `pip install yt-dlp faster-whisper` (Ollama는 별도 설치) |
| `PLAY7_microstyle_prompt` | `pip install yt-dlp faster-whisper` |
| `PLAY8_microstyle_dataset` | (대부분 LLM API 클라이언트 호출) |
| `PLAY12_concept_corpus` | (위 공통만, 표준 라이브러리 위주) |

## PLAY9_microstyle_lora — **별도 venv 필수** (CUDA / Unsloth)

QLoRA 학습. PyTorch CUDA + Unsloth 조합이라 다른 PLAY와 절대 섞지 마라.

```powershell
python -m venv PLAY9_microstyle_lora\.venv
PLAY9_microstyle_lora\.venv\Scripts\Activate.ps1
# 1. PyTorch CUDA 먼저 (cu128 — nvidia-smi로 본인 CUDA 확인)
pip install --no-cache-dir "torch==2.8.0" "torchvision==0.23.0" --index-url https://download.pytorch.org/whl/cu128
# 2. 나머지
pip install -r PLAY9_microstyle_lora\requirements.txt
```

자세한 설치 노트는 `PLAY9_microstyle_lora/README.md`와 `requirements.txt` 주석.

## PLAY10_chat_playground — PLAY9 venv 재사용

`PLAY10_chat_playground/requirements.txt` 코멘트대로 **PLAY9 venv를 그대로 활성화**한 뒤 gradio만 추가:

```powershell
PLAY9_microstyle_lora\.venv\Scripts\Activate.ps1
pip install -r PLAY10_chat_playground\requirements.txt   # gradio
```

## PLAY11_melotts — **격리 venv (자동 생성)**

`setup_env.py`가 venv 생성 + torch CPU + MeloTTS + unidic 사전(~250MB)까지 다 처리한다. **수동으로 venv 만들지 말 것.**

```powershell
cd PLAY11_melotts
python -u setup_env.py
```

5~10분 걸린다. 끝나면 `PLAY11_melotts\.venv\Scripts\python.exe`로 직접 호출 (activate 불필요).

## PLAY5_FUNNY_LLM — venv 거의 불필요

대부분 텍스트/마크다운 노트. `youtube_whisper` 다운로드 폴더(약 596MB)는 `.gitignore`로 제외됨.

## 요약

- **공유 가능한 가벼운 PLAY들** → 루트 `.venv`
- **PLAY9** → 자체 CUDA venv
- **PLAY10** → PLAY9 venv 재사용
- **PLAY11** → 자체 venv (`setup_env.py`가 만들어줌)

모든 `.venv/`는 `.gitignore`에 들어가 있다.
