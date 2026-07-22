# PLAY47_lecture_transcribe/transcribe.py
"""로컬 강의 영상/오디오 폴더 → Whisper(faster-whisper) 전사 → <원본명>.txt.

PLAY33의 전사 방식(faster_whisper.WhisperModel, large-v3/cuda/float16)을 로컬 파일용으로
자체 포함(PLAY33 import 안 함). 다운로드 단계 없이 폴더 안 미디어를 바로 전사한다.

무거운 작업 → 디스패치/긴 입력에선 background 로 띄우고 run.log 의 DONE/FAILED 폴링:
    python -u transcribe.py "....\\디지털마케팅" > run.log 2>&1   (run_in_background)

직접 실행:
    python transcribe.py "C:\\path\\to\\folder"
    python transcribe.py "C:\\path\\to\\one_file.mp4"                 # 단건
    python transcribe.py "C:\\path\\to\\folder" --device cpu --compute-type int8 --model small
    python transcribe.py "C:\\path\\to\\folder" --no-timestamps       # 본문만(타임스탬프 X)
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# 전사 대상으로 볼 확장자 (영상/오디오 모두 ffmpeg 가 디코드)
MEDIA_EXTS = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".ts",
              ".m4a", ".mp3", ".wav", ".flac", ".ogg", ".aac"}


def fmt_ts(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def find_media(target: Path) -> list[Path]:
    if target.is_file():
        return [target]
    return sorted(p for p in target.iterdir()
                  if p.is_file() and p.suffix.lower() in MEDIA_EXTS)


def main() -> None:
    p = argparse.ArgumentParser(description="로컬 미디어 폴더/파일 → Whisper 전사")
    p.add_argument("target", help="전사할 폴더 또는 단일 파일 경로")
    p.add_argument("--model", default="large-v3",
                   help="whisper 모델: tiny/base/small/medium/large-v3 (기본 large-v3)")
    p.add_argument("--language", default="ko",
                   help="언어 강제 (기본 ko). 자동감지를 원하면 빈값: --language \"\"")
    p.add_argument("--device", default="cuda", help="cuda / cpu / auto (기본 cuda)")
    p.add_argument("--compute-type", default="float16",
                   help="float16 / int8_float16 / int8 / float32 (기본 float16)")
    p.add_argument("--outdir", default=None,
                   help="출력 폴더 (기본: 원본 파일과 같은 폴더에 <원본명>.txt)")
    p.add_argument("--no-timestamps", action="store_true",
                   help="줄마다 [hh:mm:ss] 붙이지 않고 본문만 저장")
    p.add_argument("--overwrite", action="store_true",
                   help="이미 .txt 가 있어도 다시 전사 (기본은 skip)")
    args = p.parse_args()

    target = Path(args.target)
    if not target.exists():
        print(f"FAILED: 경로 없음 -> {target}", flush=True)
        sys.exit(1)

    media = find_media(target)
    if not media:
        print(f"FAILED: 미디어 파일 없음 (지원 확장자: {sorted(MEDIA_EXTS)})", flush=True)
        sys.exit(1)

    print(f"[init] 대상 {len(media)}개 | 모델 로드: {args.model} "
          f"(device={args.device}, compute={args.compute_type})", flush=True)
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel(args.model, device=args.device,
                             compute_type=args.compute_type)
    except Exception as e:
        print(f"FAILED: 모델 로드 실패 -> {e!r} "
              f"(GPU 없으면 --device cpu --compute-type int8 --model small)", flush=True)
        sys.exit(1)

    lang = args.language or None
    total = len(media)
    ok = 0

    for i, src in enumerate(media, 1):
        outdir = Path(args.outdir) if args.outdir else src.parent
        outdir.mkdir(parents=True, exist_ok=True)
        out = outdir / f"{src.stem}.txt"

        if out.exists() and not args.overwrite:
            print(f"[skip {i}/{total}] {out.name} 이미 있음", flush=True)
            ok += 1
            continue

        print(f"[work {i}/{total}] {src.name}", flush=True)
        t0 = time.time()
        try:
            segments, info = model.transcribe(str(src), language=lang,
                                              vad_filter=True, beam_size=5)
            n = 0
            # .partial 로 먼저 쓰고 끝나면 rename → 중간에 끊겨도 완성본만 .txt 로 남음
            tmp = out.with_suffix(".txt.partial")
            with tmp.open("w", encoding="utf-8") as f:
                for seg in segments:
                    line = seg.text.strip()
                    if not args.no_timestamps:
                        line = f"[{fmt_ts(seg.start)}] {line}"
                    f.write(line + "\n")
                    n += 1
                    if n % 50 == 0:
                        f.flush()
                        print(f"  ... {n} segs (~{fmt_ts(seg.end)} 지점, "
                              f"{time.time() - t0:.0f}s 경과)", flush=True)
            tmp.replace(out)
            print(f"  [ok] {out.name} ({n} segs, lang={info.language}, "
                  f"{time.time() - t0:.0f}s)", flush=True)
            ok += 1
        except Exception as e:
            print(f"  [err] {src.name} -> {e!r}", flush=True)
            continue

    print(f"[summary] {ok}/{total} 전사 완료", flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
