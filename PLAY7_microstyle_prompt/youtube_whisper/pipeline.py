# FILE: experiments/youtube_whisper/pipeline.py
"""URL/제목 → 다운로드 → Whisper 스크립트까지 한 번에.

사용 예:
    # 단건
    python pipeline.py "https://www.youtube.com/watch?v=xxxx"
    python pipeline.py "노이즈 캔슬링 작동 원리" --language ko

    # 배치 (한 줄당 URL 또는 제목, # 주석 가능)
    python pipeline.py -r list.txt --language ko
"""
from __future__ import annotations

import argparse
from pathlib import Path

from faster_whisper import WhisperModel

from yt_download import download
from transcribe import transcribe_one


def load_queries(path: Path) -> list[str]:
    """리스트 파일 파싱: 한 줄당 1쿼리, '#' 주석 / 빈 줄 무시."""
    lines = path.read_text(encoding="utf-8").splitlines()
    return [s for line in lines if (s := line.strip()) and not s.startswith("#")]


def run_batch(
    queries: list[str],
    audio_only: bool = False,
    model_size: str = "large-v3",
    language: str | None = None,
    device: str = "cuda",
    compute_type: str = "float16",
) -> list[Path]:
    """여러 쿼리를 모델 1회 로드로 처리. 실패한 항목은 스킵.

    1) Whisper 모델을 먼저 1번만 로드
    2) 각 쿼리: yt-dlp 다운로드 → 전사 → .txt/.srt 저장
    """
    print(f"[init] 모델 로드: {model_size} (device={device}, compute_type={compute_type})")
    model = WhisperModel(model_size, device=device, compute_type=compute_type)

    results: list[Path] = []
    failed: list[tuple[str, str]] = []
    total = len(queries)
    for i, q in enumerate(queries, 1):
        print(f"\n=== [{i}/{total}] {q} ===")
        try:
            print("[1/2] 다운로드")
            media = download(q, audio_only=audio_only)
            print(f"\n[2/2] 전사: {media.name}")
            txt = transcribe_one(media, model, language)
            results.append(txt)
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


def main() -> None:
    p = argparse.ArgumentParser(description="YouTube → 다운로드 → Whisper 스크립트 파이프라인")
    p.add_argument("query", nargs="?", default=None,
                   help="YouTube URL 또는 검색할 제목 (단건). -r 사용 시 생략.")
    p.add_argument("-r", "--from-file", type=Path, default=None,
                   help="리스트 파일 경로 (한 줄당 URL/제목, # 주석 가능)")
    p.add_argument("--keep-audio-only", action="store_true",
                   help="영상 대신 mp3로만 받기 (용량 절감)")
    p.add_argument("--model", default="large-v3",
                   help="whisper 모델: tiny / base / small / medium / large-v3 (기본: large-v3)")
    p.add_argument("--language", default=None, help="언어 강제 (예: ko, en). 미지정 시 자동 감지.")
    p.add_argument("--device", default="cuda", help="cuda / cpu / auto (기본: cuda)")
    p.add_argument("--compute-type", default="float16",
                   help="float16 / int8_float16 / int8 / float32 (기본: float16)")
    args = p.parse_args()

    if bool(args.query) == bool(args.from_file):
        p.error("query 또는 -r 중 정확히 하나만 지정할 것")

    if args.from_file:
        if not args.from_file.exists():
            p.error(f"리스트 파일 없음: {args.from_file}")
        queries = load_queries(args.from_file)
        if not queries:
            print(f"[!] 리스트 파일이 비어있음: {args.from_file}")
            return
        print(f"[..] 리스트 {len(queries)}건 로드: {args.from_file}")
        run_batch(
            queries,
            audio_only=args.keep_audio_only,
            model_size=args.model,
            language=args.language,
            device=args.device,
            compute_type=args.compute_type,
        )
    else:
        run(
            query=args.query,
            audio_only=args.keep_audio_only,
            model_size=args.model,
            language=args.language,
            device=args.device,
            compute_type=args.compute_type,
        )


if __name__ == "__main__":
    main()
