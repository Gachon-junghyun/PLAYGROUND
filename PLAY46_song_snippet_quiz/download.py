# PLAY46_song_snippet_quiz/download.py
"""유튜브에서 노래 오디오를 받아 clips/*.mp3 로 저장하고 playlist.json 을 만든다.

PLAY33 의 yt-dlp 사용 패턴만 빌려왔고 코드는 독립이다 (다른 PLAY import 안 함).

곡 목록은:
    1) songs.txt 가 있으면 거기서 한 줄에 "제목 - 아티스트" (아티스트 생략 가능)
    2) 없으면 아래 DEFAULT_SONGS

이미 받은 곡은 건너뛴다(파일 존재 + playlist 등록 기준). 반복 실행 안전.

사용:
    python download.py              # songs.txt 또는 기본 목록 전부
    python download.py --limit 4    # 앞에서 4곡만 (빠른 확인용)

요구: yt-dlp, ffmpeg(+ffprobe) 가 PATH 에 있어야 함.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from yt_dlp import YoutubeDL

HERE = Path(__file__).resolve().parent
CLIPS = HERE / "clips"
PLAYLIST = HERE / "playlist.json"

# Windows 콘솔 한글 깨짐 방지
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# 누구나 한 번쯤 들어봤을 만한 곡들 (확인 즉시 가능하도록 기본 제공).
DEFAULT_SONGS = [
    "Dynamite - BTS",
    "Gangnam Style - PSY",
    "Hype Boy - NewJeans",
    "Shape of You - Ed Sheeran",
    "Blinding Lights - The Weeknd",
    "Bohemian Rhapsody - Queen",
    "Billie Jean - Michael Jackson",
    "Rolling in the Deep - Adele",
    "Uptown Funk - Mark Ronson Bruno Mars",
    "Believer - Imagine Dragons",
    "Lovely - Billie Eilish Khalid",
    "Viva La Vida - Coldplay",
]


def slugify(text: str) -> str:
    s = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE).strip().lower()
    s = re.sub(r"[\s]+", "_", s)
    return s[:60] or "song"


def parse_song(line: str) -> tuple[str, str]:
    """'제목 - 아티스트' → (title, artist). 구분자 없으면 artist 빈 문자열."""
    if " - " in line:
        title, artist = line.split(" - ", 1)
        return title.strip(), artist.strip()
    return line.strip(), ""


def load_songs() -> list[str]:
    txt = HERE / "songs.txt"
    if txt.exists():
        lines = [l.strip() for l in txt.read_text(encoding="utf-8").splitlines()]
        songs = [l for l in lines if l and not l.startswith("#")]
        if songs:
            return songs
    return DEFAULT_SONGS


def probe_duration(path: Path) -> float:
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True, text=True, check=True,
        )
        return float(out.stdout.strip())
    except Exception:
        return 0.0


def download_one(title: str, artist: str) -> dict | None:
    """검색 1건 다운로드 → mp3. 성공 시 playlist 엔트리 반환."""
    slug = slugify(f"{title}_{artist}" if artist else title)
    mp3 = CLIPS / f"{slug}.mp3"
    query = f"ytsearch1:{title} {artist} official audio".strip()

    if not mp3.exists():
        opts = {
            "format": "bestaudio/best",
            "outtmpl": str(CLIPS / f"{slug}.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
            "ignoreerrors": True,
            "noplaylist": True,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
        }
        try:
            with YoutubeDL(opts) as ydl:
                ydl.download([query])
        except Exception as e:
            print(f"[FAIL] {title}: {e}", file=sys.stderr)
            return None

    if not mp3.exists():
        print(f"[FAIL] {title}: mp3 생성 안 됨", file=sys.stderr)
        return None

    dur = probe_duration(mp3)
    print(f"[OK] {title} ({artist or '?'}) → {mp3.name}  {dur:.0f}s")
    return {
        "title": title,
        "artist": artist,
        "file": mp3.name,
        "duration": round(dur, 2),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="유튜브 → clips/*.mp3 + playlist.json")
    ap.add_argument("--limit", type=int, default=None, help="앞에서 N곡만")
    args = ap.parse_args()

    CLIPS.mkdir(parents=True, exist_ok=True)
    songs = load_songs()
    if args.limit:
        songs = songs[: args.limit]

    existing = {}
    if PLAYLIST.exists():
        for e in json.loads(PLAYLIST.read_text(encoding="utf-8")):
            existing[e["file"]] = e

    entries = dict(existing)
    for line in songs:
        title, artist = parse_song(line)
        slug = slugify(f"{title}_{artist}" if artist else title)
        fname = f"{slug}.mp3"
        if fname in entries and (CLIPS / fname).exists():
            print(f"[skip] {title} (이미 있음)")
            continue
        e = download_one(title, artist)
        if e:
            entries[e["file"]] = e

    rows = [e for e in entries.values() if (CLIPS / e["file"]).exists() and e["duration"] > 0]
    PLAYLIST.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[DONE] playlist.json: {len(rows)}곡")


if __name__ == "__main__":
    main()
