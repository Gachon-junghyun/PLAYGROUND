# core — PLAYGROUND 공용 인프라

## 목적
실험(PLAY)들이 계속 복붙해 쓰던 **인프라**를 한 곳으로 승격한 패키지. 실험이 아니라 실험이 *딛고 서는 바닥*.
현재 둘:
- `core.media` — YouTube 발견/다운로드 + Whisper 전사 (PLAY5/6/7 `youtube_whisper/` + PLAY33 `_common.py` 통합)
- `core.market` — OHLCV fetcher, yfinance→KRX→dummy 폴백 (PLAY15 승격)

## 무엇이 core 에 들어오나 (게이트)
아무거나 안 들어온다. **셋 다** 만족해야 승격:
1. **3개+ PLAY가 실제로 쓴다** (media·market 둘 다 통과)
2. **지루하고 안정적** — 자주 안 바뀜
3. **인터페이스가 깔끔** — `fetch(ticker) -> rows`, `transcribe_one(media, model) -> txt` 수준

안 그러면 잡동사니 서랍이 된다. 애매하면 PLAY 안에 인라인으로 두고, 3번째 PLAY가 같은 걸 또 쓰면 그때 승격.

## 의존 방향 (절대 규칙)
```
PLAY → core      (O)   PLAY 가 core 를 import
core → PLAY      (X)   core 는 어떤 PLAY 도 모른다
```
이거 하나만 지키면 의존 그래프가 안 꼬인다. core 가 PLAY 를 import 하는 순간 죽은 실험이 core 를 깨뜨릴 수 있음.

## 실행법 / 가져다 쓰는 법

### 사전 설치 (1회, dispatch 실행 경로에 두지 말 것)
```powershell
pip install yt-dlp                 # core.media 발견/다운로드
pip install faster-whisper         # core.media 전사 (torch 동반 — 무거움)
pip install yfinance               # core.market (선택; 없으면 KRX/dummy 폴백)
# core.media 전사·다운로드는 ffmpeg 필요 (PATH에 있어야 함)
```

### 소비자 PLAY 에서 import — 무설치 path shim (2줄)
설치 없이 쓴다. 각 PLAY 스크립트 상단에 이 스니펫을 붙이면, 위로 올라가며 `core/` 를
찾아 sys.path 에 repo 루트를 넣는다 (중첩 깊이 무관 — scripts/ 안이든 PLAY 루트든 동작):
```python
import sys, pathlib
for _p in pathlib.Path(__file__).resolve().parents:
    if (_p / "core" / "__init__.py").exists():
        sys.path.insert(0, str(_p)); break

from core.media import download, run_batch, fetch_latest, search_channels
from core.market import fetch, write_csv
```

### CLI 로도 (repo 루트에서)
```powershell
python -m core.market AAPL --days 60                 # CSV → stdout
python -m core.market 298040 --source krx --out a.csv
python -m core.media "https://youtu.be/xxxx" --language ko
python -m core.media -r list.txt --download-dir dl --transcript-dir tx
```

## 입력 / 출력

### core.market
- `fetch(ticker, days=60, source="auto") -> (rows, used_source, attempts)`
  - `rows = [{date, open, high, low, close, volume}, ...]` (오래된→최신)
  - `source`: `auto`(yfinance→krx→dummy) | `yfinance` | `krx` | `dummy`
  - 한국 6자리 ticker 면 auto 에 krx 가 자동 추가됨
- `write_csv(rows, out_path)` — `CSV_HEADER` 순서로 저장
- `CSV_HEADER = ["date","open","high","low","close","volume"]`

### core.media
- **발견(다운로드 X, GPU 불필요):**
  - `fetch_latest(channel, limit=16) -> [{video_id, title, url}]`
  - `search_channels(keyword, min_subscribers=120_000, search_count=50) -> [{channel_id, name, url, subscribers}]`
  - `normalize_channel(channel) -> "https://.../@handle/videos"`
- **다운로드:** `download(query, out_dir=Path("downloads"), audio_only=False) -> Path`
  - query 가 URL 이면 그대로, 제목이면 `ytsearch1`
- **전사(faster-whisper, lazy):**
  - `load_model(model_size="large-v3", device="cuda", compute_type="float16")`
  - `transcribe_one(media, model, out_dir=Path("transcripts"), language=None) -> Path(txt)` (.txt + .srt)
  - `run_batch(queries, download_dir, transcript_dir, ...) -> [Path]` (모델 1회 로드 후 배치)
  - `run(query, **kwargs) -> Path` (단건)

## 가정 & 제약
- **출력 경로는 cwd 기준.** 라이브러리가 자기 폴더(`core/`)에 쓰지 않게 출력 디렉토리를 인자로 받는다. 기본값 `downloads/`, `transcripts/` 는 **실행한 위치(cwd)** 기준으로 생긴다 — PLAY 안에서 부를 땐 원하는 절대/상대 경로를 명시할 것.
- **전사 기본값은 RTX 3080 가정**: `device="cuda"`, `compute_type="float16"`. CPU 머신이면 `device="cpu"`, `compute_type="int8"` 로 넘겨야 함 (안 그러면 CUDA 없음 에러). `device="auto"` 도 가능(가능하면 GPU).
- **무거운 의존성은 dispatch 실행 경로에 두지 말 것.** `load_model`/전사는 torch 를 lazy import 하지만, 그건 *미리 설치돼 있다는 가정* 하에서다. 미설치면 명확한 RuntimeError 로 죽는다(조용히 안 깨짐). 설치 자체(`pip install faster-whisper`, ffmpeg)는 사전 준비 — 45초 Bash 안에서 하지 말 것.
- **core.media 는 무상태.** seen-cache(이미 처리한 영상 스킵) 같은 상태는 안 들고 있다. 중복 스킵·진행상황 추적은 소비자 PLAY 가 자기 `data/` 에서 관리 (PLAY33 `_common.py` 의 seen-cache 처럼). 이건 일부러 core 에 안 올렸다 — 경로 규약을 강요하기 싫어서.
- **core.market 의 KRX 소스는 불안정.** KRX endpoint 의 UA/네트워크 검사로 실패할 수 있고, 그러면 dummy 로 폴백한다. 더미는 *재현 가능한 가짜 데이터*라 검증엔 쓰되 실데이터로 착각하지 말 것 (`used_source` 확인).
- **소비자 마이그레이션은 점진적.** 기존 PLAY5/6/7 `youtube_whisper/`, PLAY15, PLAY33 `_common.py` 는 아직 자기 복사본을 들고 있다. core 로 갈아끼우는 건 PLAY별로 따로 진행 (한 번에 다 안 건드림).

## 변경 이력
- 2026-06-23 — 최초 생성. PLAY15(market) + PLAY5/6/7·PLAY33(media) 인프라를 `core.market`/`core.media` 로 승격. 무설치 path shim 방식. 소비자 마이그레이션은 아직 안 함.
