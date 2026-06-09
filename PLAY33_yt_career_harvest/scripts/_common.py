# PLAY33_yt_career_harvest/scripts/_common.py
"""yt-dlp 래퍼 + 신규 영상 캐시 공통. (PLAY 독립 — 외부 PLAY import 안 함)

여기 있는 함수만으로 01_discover / 02_fetch / 03_pipeline 이 다 돌아간다.
faster_whisper 는 03 에서만 import (무거운 의존성 격리).
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date
from pathlib import Path

from yt_dlp import YoutubeDL

# Windows 콘솔(cp949)에서 한글이 깨지지 않게 utf-8 강제
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ─── 경로 ─────────────────────────────────────────────
# 주제별 격리: env var PLAY33_TOPIC 설정 시 data_<topic>/ 로, 없으면 기존 data/ (하위호환).
# 한 파이프라인 회전(01→02→03)을 같은 env로 돌려야 경로가 일관된다.
PLAY_DIR = Path(__file__).resolve().parent.parent
_TOPIC = os.environ.get("PLAY33_TOPIC", "").strip()
DATA_DIR = PLAY_DIR / (f"data_{_TOPIC}" if _TOPIC else "data")
TRANSCRIPT_DIR = DATA_DIR / "transcripts"
SEEN_PATH = DATA_DIR / "seen.json"

VIDEO_URL_FMT = "https://www.youtube.com/watch?v={id}"


# ─── 채널 정규화 / 영상 목록 ──────────────────────────
def normalize_channel(channel: str) -> str:
    """채널 식별자를 /videos 탭 URL로 정규화 (@핸들·평문·전체URL 허용)."""
    c = channel.strip()
    if c.startswith(("http://", "https://")):
        c = c.rstrip("/")
        return c if c.endswith("/videos") else c + "/videos"
    if not c.startswith("@"):
        c = "@" + c
    return f"https://www.youtube.com/{c}/videos"


def _flatten(info: dict | None) -> list[dict]:
    """yt-dlp가 entries 안에 entries를 중첩으로 줄 때 평탄화."""
    if not info:
        return []
    if info.get("entries") is not None:
        out: list[dict] = []
        for e in info["entries"]:
            out.extend(_flatten(e))
        return out
    return [info] if info.get("id") else []


def _resolve_via_search(channel: str) -> str | None:
    """핸들 직매칭 실패 시 폴백: 검색 1건 → 그 영상의 채널 /videos URL."""
    opts = {"quiet": True, "extract_flat": True, "skip_download": True, "ignoreerrors": True}
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"ytsearch1:{channel}", download=False)
    entries = (info or {}).get("entries") or []
    if not entries:
        return None
    e = entries[0] or {}
    url = e.get("channel_url")
    if not url and e.get("channel_id"):
        url = f"https://www.youtube.com/channel/{e['channel_id']}"
    return (url.rstrip("/") + "/videos") if url else None


def fetch_latest(channel: str, limit: int = 16) -> list[dict]:
    """채널 최신 영상 limit개 → [{video_id, title, url}] (다운로드 X)."""
    opts = {
        "extract_flat": True,
        "playlistend": limit,
        "quiet": True,
        "skip_download": True,
        "ignoreerrors": True,
    }

    def _try(url: str) -> list[dict]:
        with YoutubeDL(opts) as ydl:
            return _flatten(ydl.extract_info(url, download=False))

    entries = _try(normalize_channel(channel))
    if not entries:
        fb = _resolve_via_search(channel)
        if fb:
            print(f"[..] '{channel}': 핸들 직매칭 실패 → 검색 폴백", file=sys.stderr)
            entries = _try(fb)

    out: list[dict] = []
    for e in entries:
        vid = e.get("id")
        if not vid or len(vid) != 11:  # 11자리 영상 ID만 (채널/플레이리스트 혼입 컷)
            continue
        out.append({"video_id": vid, "title": e.get("title", "?"),
                    "url": VIDEO_URL_FMT.format(id=vid)})
        if len(out) >= limit:
            break
    return out


# ─── 키워드 → 채널 발견 (구독자 필터) ─────────────────
def _candidate_channels(keyword: str, search_count: int) -> dict[str, dict]:
    opts = {"extract_flat": True, "quiet": True, "skip_download": True, "ignoreerrors": True}
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"ytsearch{search_count}:{keyword}", download=False)
    out: dict[str, dict] = {}
    for e in ((info or {}).get("entries") or []):
        if not e:
            continue
        cid = e.get("channel_id") or e.get("uploader_id")
        url = e.get("channel_url") or e.get("uploader_url")
        name = e.get("channel") or e.get("uploader") or "?"
        if cid and url:
            out.setdefault(cid, {"channel_id": cid, "name": name, "url": url})
    return out


def _subscriber_count(channel_url: str) -> int | None:
    opts = {"extract_flat": True, "playlistend": 1, "quiet": True,
            "skip_download": True, "ignoreerrors": True}
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(channel_url, download=False)
    return info.get("channel_follower_count") if info else None


def search_channels(keyword: str, min_subscribers: int = 120_000,
                    search_count: int = 50) -> list[dict]:
    """키워드로 채널 발견 → 구독자 min_subscribers 이상만 (내림차순)."""
    cands = _candidate_channels(keyword, search_count)
    print(f"[..] 후보 채널 {len(cands)}개 → 구독자 조회 중...", file=sys.stderr)
    passed: list[dict] = []
    for meta in cands.values():
        subs = _subscriber_count(meta["url"])
        if subs is not None and subs >= min_subscribers:
            passed.append({**meta, "subscribers": subs})
    passed.sort(key=lambda d: d["subscribers"], reverse=True)
    return passed


# ─── 신규 영상 캐시 (이미 처리한 영상 스킵) ───────────
def load_seen() -> dict[str, str]:
    if not SEEN_PATH.exists():
        return {}
    try:
        return json.loads(SEEN_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def mark_seen(video_id: str) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    seen = load_seen()
    seen[video_id] = date.today().isoformat()
    SEEN_PATH.write_text(json.dumps(seen, ensure_ascii=False, indent=2), encoding="utf-8")


def filter_new(videos: list[dict]) -> list[dict]:
    """이미 처리한 video_id 제외."""
    seen = load_seen()
    return [v for v in videos if v["video_id"] not in seen]


# ─── jsonl 헬퍼 ───────────────────────────────────────
def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(s) for line in path.read_text(encoding="utf-8").splitlines()
            if (s := line.strip())]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
