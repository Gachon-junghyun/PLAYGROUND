"""core.media — YouTube 발견/다운로드 + Whisper 전사 (yt-dlp + faster-whisper).

PLAY5/6/7 의 youtube_whisper/ (다운로드+전사) 와 PLAY33 _common.py (발견+목록) 통합.

  발견:   normalize_channel, fetch_latest, search_channels
  다운로드: download
  전사:   load_model, transcribe_one, run_batch, run

설계 원칙:
- faster_whisper(torch) 는 전사 함수 안에서만 lazy import.
  `import core.media` / 발견·다운로드만 쓰는 경로엔 GPU/torch 불필요.
- 라이브러리는 자기 폴더에 쓰지 않는다 — 출력 디렉토리를 인자로 받는다(cwd 기준 기본값).
- 상태(seen-cache 등)는 안 들고 있음. 중복 스킵은 소비자 PLAY 책임.

기본 device=cuda / compute_type=float16 (RTX 3080 가정). CPU면 device='cpu',
compute_type='int8' 로 넘길 것 — README "가정 & 제약" 참고.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from yt_dlp import YoutubeDL

VIDEO_URL_FMT = "https://www.youtube.com/watch?v={id}"
MEDIA_EXTS = {".mp4", ".mkv", ".webm", ".mov", ".avi",
              ".mp3", ".wav", ".m4a", ".flac", ".ogg"}


# ─── 채널 정규화 / 영상 목록 (다운로드 X) ──────────────────────────
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


# ─── 키워드 → 채널 발견 (구독자 필터) ─────────────────────────────
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


# ─── 다운로드 (yt-dlp) ────────────────────────────────────────────
def download(query: str, out_dir: Path = Path("downloads"), audio_only: bool = False) -> Path:
    """링크면 그대로, 제목이면 ytsearch1로 첫 결과를 받는다. out_dir(cwd 기준)에 저장."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    is_url = query.startswith(("http://", "https://"))
    target = query if is_url else f"ytsearch1:{query}"

    opts: dict = {
        "outtmpl": str(out_dir / "%(title)s [%(id)s].%(ext)s"),
        "noplaylist": True,
        "quiet": False,
        "restrictfilenames": True,  # 한글/특수문자 → 안전한 파일명
    }
    if audio_only:
        opts["format"] = "bestaudio/best"
        opts["postprocessors"] = [
            {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}
        ]
    else:
        opts["format"] = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"

    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(target, download=True)
        if "entries" in info:  # ytsearch 결과는 entries로 감싸짐
            info = info["entries"][0]
        filename = ydl.prepare_filename(info)
        if audio_only:
            filename = str(Path(filename).with_suffix(".mp3"))

    saved = Path(filename)
    print(f"\n[OK] saved: {saved}")
    return saved


# ─── 전사 (faster-whisper, lazy import) ──────────────────────────
def _ts(sec: float) -> str:
    """초 → SRT 타임스탬프 (HH:MM:SS,mmm)."""
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec - h * 3600 - m * 60
    ms = int((s - int(s)) * 1000)
    return f"{h:02d}:{m:02d}:{int(s):02d},{ms:03d}"


def load_model(model_size: str = "large-v3", device: str = "cuda",
               compute_type: str = "float16"):
    """faster-whisper WhisperModel 로드 (torch 는 여기서 lazy import).

    미설치면 명확한 RuntimeError — dispatch 가정(사전 설치)을 어겼다는 신호.
    """
    try:
        from faster_whisper import WhisperModel
    except ImportError as e:
        raise RuntimeError(
            "faster-whisper 미설치. 사전 설치 필요: pip install faster-whisper "
            "(+ GPU면 CUDA/cuDNN, +ffmpeg)"
        ) from e
    return WhisperModel(model_size, device=device, compute_type=compute_type)


def transcribe_one(media: Path, model, out_dir: Path = Path("transcripts"),
                   language: str | None = None) -> Path:
    """단일 파일 → .txt(전사문) + .srt(자막) 저장. txt 경로 반환."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    segments, info = model.transcribe(
        str(media),
        language=language,
        vad_filter=True,  # 무음 구간 자동 스킵 → 환각 방지
        beam_size=5,
    )

    txt_path = out_dir / f"{Path(media).stem}.txt"
    srt_path = out_dir / f"{Path(media).stem}.srt"

    with txt_path.open("w", encoding="utf-8") as ftxt, srt_path.open("w", encoding="utf-8") as fsrt:
        for i, seg in enumerate(segments, 1):
            text = seg.text.strip()
            ftxt.write(text + "\n")
            fsrt.write(f"{i}\n{_ts(seg.start)} --> {_ts(seg.end)}\n{text}\n\n")

    print(f"[OK] {Path(media).name}  (lang={info.language}, prob={info.language_probability:.2f})")
    print(f"     -> {txt_path}")
    return txt_path


def run_batch(
    queries: list[str],
    download_dir: Path = Path("downloads"),
    transcript_dir: Path = Path("transcripts"),
    audio_only: bool = False,
    model_size: str = "large-v3",
    language: str | None = None,
    device: str = "cuda",
    compute_type: str = "float16",
) -> list[Path]:
    """여러 쿼리를 모델 1회 로드로 처리. 실패한 항목은 스킵하고 계속."""
    print(f"[init] 모델 로드: {model_size} (device={device}, compute_type={compute_type})")
    model = load_model(model_size, device=device, compute_type=compute_type)

    results: list[Path] = []
    failed: list[tuple[str, str]] = []
    total = len(queries)
    for i, q in enumerate(queries, 1):
        print(f"\n=== [{i}/{total}] {q} ===")
        try:
            print("[1/2] 다운로드")
            media = download(q, out_dir=download_dir, audio_only=audio_only)
            print(f"\n[2/2] 전사: {media.name}")
            results.append(transcribe_one(media, model, out_dir=transcript_dir, language=language))
        except Exception as e:  # 한 항목 실패가 배치 전체를 막지 않게
            print(f"[ERR] {q} -> {e!r}")
            failed.append((q, repr(e)))
            continue

    print(f"\n[DONE] {len(results)}/{total} 완료")
    if failed:
        print(f"[FAILED] {len(failed)}건:")
        for q, err in failed:
            print(f"  - {q}  ({err})")
    return results


def run(query: str, **kwargs) -> Path:
    """단건 처리. 내부적으로 run_batch에 위임."""
    return run_batch([query], **kwargs)[0]


def load_queries(path: Path) -> list[str]:
    """리스트 파일 파싱: 한 줄당 1쿼리, '#' 주석 / 빈 줄 무시."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return [s for line in lines if (s := line.strip()) and not s.startswith("#")]


def main() -> None:
    p = argparse.ArgumentParser(description="YouTube → 다운로드 → Whisper 전사 (core.media)")
    p.add_argument("query", nargs="?", default=None,
                   help="YouTube URL 또는 검색할 제목 (단건). -r 사용 시 생략.")
    p.add_argument("-r", "--from-file", type=Path, default=None,
                   help="리스트 파일 경로 (한 줄당 URL/제목, # 주석 가능)")
    p.add_argument("--download-dir", type=Path, default=Path("downloads"))
    p.add_argument("--transcript-dir", type=Path, default=Path("transcripts"))
    p.add_argument("--keep-audio-only", action="store_true", help="mp3로만 받기 (용량 절감)")
    p.add_argument("--model", default="large-v3",
                   help="whisper 모델: tiny/base/small/medium/large-v3 (기본 large-v3)")
    p.add_argument("--language", default=None, help="언어 강제 (예: ko, en). 미지정 시 자동 감지.")
    p.add_argument("--device", default="cuda", help="cuda / cpu / auto (기본 cuda)")
    p.add_argument("--compute-type", default="float16",
                   help="float16 / int8_float16 / int8 / float32 (기본 float16)")
    args = p.parse_args()

    if bool(args.query) == bool(args.from_file):
        p.error("query 또는 -r 중 정확히 하나만 지정할 것")

    queries = load_queries(args.from_file) if args.from_file else [args.query]
    if not queries:
        print(f"[!] 쿼리 없음: {args.from_file}")
        return

    run_batch(
        queries,
        download_dir=args.download_dir,
        transcript_dir=args.transcript_dir,
        audio_only=args.keep_audio_only,
        model_size=args.model,
        language=args.language,
        device=args.device,
        compute_type=args.compute_type,
    )


if __name__ == "__main__":
    main()
