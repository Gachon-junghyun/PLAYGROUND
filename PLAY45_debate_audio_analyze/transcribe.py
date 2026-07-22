# PLAY45_debate_audio_analyze/transcribe.py
"""녹음(.m4a 등) → faster-whisper 전사 → 타임스탬프 박힌 전사본.

whisper 전사 로직은 PLAY33_yt_career_harvest/scripts/03_pipeline.py 에서 가져와
단건 로컬 파일용으로 떼어냈다 (PLAY 독립 — 외부 PLAY import 안 함).

산출물 (output/):
  - segments.jsonl  : 한 줄 = {"i", "start", "end", "text"}  (분석/화자추정용 원천)
  - transcript.txt  : [mm:ss–mm:ss] 텍스트  (사람이 읽는 용)

장시간 작업이다(~1시간 오디오면 수~십수 분). background 로 띄워라:
    python -u transcribe.py > output/run.log 2>&1   (run_in_background)
그 다음 run.log 의 DONE / FAILED 폴링.

사용:
    python transcribe.py
    python transcribe.py --input input/bokjeong2.m4a --model large-v3
    python transcribe.py --device cpu --compute-type int8   # GPU 없을 때
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Windows 콘솔(cp949)에서 한글 깨짐 방지
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def _ts(sec: float) -> str:
    m, s = divmod(int(sec), 60)
    return f"{m:02d}:{s:02d}"


def main() -> None:
    p = argparse.ArgumentParser(description="단일 녹음 파일 → whisper 전사")
    p.add_argument("--input", default=str(HERE / "input" / "bokjeong2.m4a"))
    p.add_argument("--outdir", default=str(HERE / "output"))
    p.add_argument("--model", default="large-v3",
                   help="tiny/base/small/medium/large-v3 (기본 large-v3)")
    p.add_argument("--language", default="ko", help="언어 강제 (기본 ko)")
    p.add_argument("--device", default="cuda", help="cuda / cpu / auto")
    p.add_argument("--compute-type", default="float16",
                   help="float16 / int8_float16 / int8 / float32")
    args = p.parse_args()

    src = Path(args.input)
    if not src.exists():
        print(f"FAILED: 입력 파일 없음 -> {src}", flush=True)
        sys.exit(1)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    print(f"[init] 모델 로드: {args.model} (device={args.device}, "
          f"compute_type={args.compute_type})", flush=True)
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel(args.model, device=args.device,
                             compute_type=args.compute_type)
    except Exception as e:
        print(f"FAILED: 모델 로드 실패 -> {e!r} "
              f"(GPU 없으면 --device cpu --compute-type int8)", flush=True)
        sys.exit(1)

    print(f"[asr] 전사 시작: {src.name}", flush=True)
    try:
        segments, info = model.transcribe(
            str(src), language=(args.language or None),
            vad_filter=True, beam_size=5)
        print(f"[asr] lang={info.language} "
              f"duration={_ts(info.duration)} (총 {info.duration:.0f}s)", flush=True)

        jsonl_path = outdir / "segments.jsonl"
        txt_path = outdir / "transcript.txt"
        n = 0
        with jsonl_path.open("w", encoding="utf-8") as jf, \
             txt_path.open("w", encoding="utf-8") as tf:
            for seg in segments:  # generator → 진행하며 즉시 flush (중단 내성)
                text = seg.text.strip()
                rec = {"i": n, "start": round(seg.start, 2),
                       "end": round(seg.end, 2), "text": text}
                jf.write(json.dumps(rec, ensure_ascii=False) + "\n")
                jf.flush()
                tf.write(f"[{_ts(seg.start)}-{_ts(seg.end)}] {text}\n")
                tf.flush()
                n += 1
                if n % 20 == 0:  # 진행 라인 (오디오 진행 위치 기준)
                    print(f"  [seg {n}] @{_ts(seg.end)} / {_ts(info.duration)}",
                          flush=True)
        print(f"[done] 세그먼트 {n}개 -> {txt_path.name}, {jsonl_path.name}",
              flush=True)
        print("DONE", flush=True)
    except Exception as e:
        print(f"FAILED: 전사 중 오류 -> {e!r}", flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
