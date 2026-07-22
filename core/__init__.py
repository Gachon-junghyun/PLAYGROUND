"""core — PLAYGROUND 공용 인프라.

실험(PLAY)이 아니라 실험이 *딛고 서는 바닥*. 규칙:
- 의존 방향은 PLAY → core 한 방향. core 는 어떤 PLAY 도 import 하지 않는다.
- 무거운 의존성(faster_whisper/torch, yfinance)은 함수 안에서 lazy import.
  `import core` 만으로는 아무 무거운 것도 안 끌려온다(서브모듈 import 안 함).
- 소비자는 무설치 path shim 으로 가져다 쓴다 — core/README.md 참고.

서브모듈:
  core.media   — YouTube 발견/다운로드 + Whisper 전사 (yt-dlp + faster-whisper)
  core.market  — OHLCV fetcher (yfinance → KRX → dummy)
"""

from __future__ import annotations

import sys

__version__ = "0.1.0"


def enable_utf8() -> None:
    """Windows 콘솔(cp949)에서 한글 깨짐 방지. idempotent, 실패 무해."""
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass


enable_utf8()
