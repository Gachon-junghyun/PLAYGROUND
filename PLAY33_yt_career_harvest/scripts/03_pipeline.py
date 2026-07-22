# PLAY33_yt_career_harvest/scripts/03_pipeline.py
"""queue.jsonl → (다운로드 mp3 → Whisper 전사) → data/transcripts/*.txt + manifest.jsonl.

⚠️ 무거운 단계다. 디스패치(45초)에서는 background 패턴으로 띄워라:
    python -u scripts/03_pipeline.py > data/run.log 2>&1   (run_in_background)
    그 다음 run.log 의 DONE / FAILED 를 폴링.

직접 실행:
    python scripts/03_pipeline.py                       # data/queue.jsonl 전체
    python scripts/03_pipeline.py --model medium --device cpu --compute-type int8
    python scripts/03_pipeline.py --url "https://youtu.be/xxxx"   # 단건 테스트
    python scripts/03_pipeline.py --url "..." --language "" --timestamps  # 영화/장편 따라보기
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from yt_dlp import YoutubeDL

from _common import (DATA_DIR, TRANSCRIPT_DIR, mark_seen, read_jsonl,
                     write_jsonl, VIDEO_URL_FMT)

DOWNLOAD_DIR = DATA_DIR / "downloads"
MANIFEST_PATH = DATA_DIR / "manifest.jsonl"


def _fmt_ts(t: float) -> str:
    """초 → [H:MM:SS] (영화/장편 따라보기용 타임스탬프)."""
    t = int(t)
    return f"{t // 3600}:{(t % 3600) // 60:02d}:{t % 60:02d}"


def _download_audio(url: str) -> Path:
    """URL → mp3 (오디오만, 전사엔 영상 불필요 → 용량 절감)."""
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    opts = {
        "outtmpl": str(DOWNLOAD_DIR / "%(id)s.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "format": "bestaudio/best",
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3",
                            "preferredquality": "192"}],
    }
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        if "entries" in info:
            info = info["entries"][0]
    return DOWNLOAD_DIR / f"{info['id']}.mp3"


def main() -> None:
    p = argparse.ArgumentParser(description="queue → 다운로드 + Whisper 전사")
    p.add_argument("--queue", default=str(DATA_DIR / "queue.jsonl"),
                   help="입력 큐 jsonl (기본 data/queue.jsonl)")
    p.add_argument("--url", default=None, help="단건 테스트용 URL (queue 무시)")
    p.add_argument("--model", default="large-v3",
                   help="whisper 모델: tiny/base/small/medium/large-v3 (기본 large-v3)")
    p.add_argument("--language", default="ko", help="언어 강제 (기본 ko, 자동감지는 빈값)")
    p.add_argument("--device", default="cuda", help="cuda / cpu / auto (기본 cuda)")
    p.add_argument("--compute-type", default="float16",
                   help="float16 / int8_float16 / int8 / float32 (기본 float16)")
    p.add_argument("--timestamps", action="store_true",
                   help="각 줄 앞에 [H:MM:SS] 시작시각 표기 (영화/장편 따라보기용, 기본 off)")
    args = p.parse_args()

    if args.url:
        vid = args.url.split("watch?v=")[-1].split("&")[0][:11]
        items = [{"video_id": vid, "url": args.url, "channel": "_adhoc", "title": "adhoc"}]
    else:
        items = read_jsonl(Path(args.queue))
    if not items:
        print("FAILED: 큐가 비어있음 (먼저 02_fetch.py 로 queue.jsonl 생성)", flush=True)
        sys.exit(1)

    print(f"[init] 모델 로드: {args.model} (device={args.device}, "
          f"compute_type={args.compute_type})", flush=True)
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel(args.model, device=args.device, compute_type=args.compute_type)
    except Exception as e:
        print(f"FAILED: 모델 로드 실패 → {e!r} "
              f"(GPU 없으면 --device cpu --compute-type int8)", flush=True)
        sys.exit(1)

    TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    manifest: list[dict] = read_jsonl(MANIFEST_PATH)
    done_ids = {m["video_id"] for m in manifest}
    lang = args.language or None
    total = len(items)
    ok = 0

    for i, it in enumerate(items, 1):
        vid = it["video_id"]
        url = it.get("url") or VIDEO_URL_FMT.format(id=vid)
        if vid in done_ids:
            print(f"[skip {i}/{total}] {vid} 이미 manifest에 있음", flush=True)
            continue
        print(f"[work {i}/{total}] {it.get('channel','?')} | {it.get('title','?')[:40]}", flush=True)
        try:
            print(f"  [dl] {url}", flush=True)
            media = _download_audio(url)
            print(f"  [asr] {media.name}", flush=True)
            segments, info = model.transcribe(str(media), language=lang,
                                              vad_filter=True, beam_size=5)
            txt_path = TRANSCRIPT_DIR / f"{vid}.txt"
            with txt_path.open("w", encoding="utf-8") as f:
                for seg in segments:
                    line = seg.text.strip()
                    if args.timestamps:
                        line = f"[{_fmt_ts(seg.start)}] {line}"
                    f.write(line + "\n")
            rec = {"video_id": vid, "channel": it.get("channel", "?"),
                   "title": it.get("title", "?"), "url": url,
                   "txt_path": str(txt_path.relative_to(DATA_DIR.parent)),
                   "lang": info.language}
            manifest.append(rec)
            write_jsonl(MANIFEST_PATH, manifest)  # 매 건 즉시 저장 (중단 내성)
            mark_seen(vid)
            ok += 1
            print(f"  [ok] {txt_path.name} (lang={info.language})", flush=True)
        except Exception as e:
            print(f"  [err] {vid} -> {e!r}", flush=True)
            continue

    print(f"[summary] {ok}/{total} 전사 완료, manifest={MANIFEST_PATH}", flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
