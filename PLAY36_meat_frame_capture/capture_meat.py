# PLAY36_meat_frame_capture/capture_meat.py
"""mp4 영상 → Whisper 전사(타임스탬프) → 나레이션이 '고기'를 설명하는 구간 탐지
→ 그 시점의 영상 프레임을 ffmpeg로 캡처해 저장.

핵심 아이디어: 발화자가 고기를 설명할 때 보통 그 고기를 화면에 비춘다.
그래서 '고기 키워드'가 들어간 자막 구간의 타임스탬프에서 프레임을 뽑으면
"그때 고기가 어떻게 생겼나"를 이미지로 모아볼 수 있다.

⚠️ 무거움(Whisper). 긴 영상은 background 패턴으로 돌려라:
    python -u capture_meat.py --video x.mp4 > run.log 2>&1   (run_in_background)
    그 뒤 run.log 의 DONE / FAILED 폴링.

사용 예:
    python capture_meat.py --video meat.mp4
    python capture_meat.py --url "https://youtu.be/xxxx"          # 다운로드부터
    python capture_meat.py --video meat.mp4 --device cpu --compute-type int8 --model small
    python capture_meat.py --video meat.mp4 --keywords "고기,삼겹살,마이야르" --min-gap 8
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

# Windows 콘솔(cp949)에서 한글 깨짐 방지
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# 고기가 화면에 나올 법한 설명 키워드 (자막 부분일치, 대소문자 무시)
DEFAULT_KEYWORDS = [
    "고기", "삼겹살", "목살", "등심", "채끝", "갈비", "스테이크", "소고기", "돼지",
    "한우", "껍질", "껍데기", "비계", "지방", "마블링", "마이야르", "육즙", "단면",
    "익", "굽", "구워", "구운", "색", "바삭", "겉바", "훈연", "숯불", "불판", "석쇠",
    "레어", "미디엄", "웰던", "숙성", "에이징", "바크", "스모크",
]


def _fail(msg: str) -> None:
    print(f"FAILED: {msg}", flush=True)
    sys.exit(1)


def _mmss(t: float) -> str:
    """초 → mmss 문자열 (파일명용, 콜론 없이)."""
    m, s = divmod(int(t), 60)
    return f"{m:02d}m{s:02d}s"


def _slug(text: str, limit: int = 24) -> str:
    """자막 텍스트 → 파일명 안전 슬러그 (한글 유지, 특수문자 제거)."""
    t = re.sub(r"[^0-9A-Za-z가-힣]+", "_", text).strip("_")
    return (t[:limit] or "clip")


def download_mp4(url: str, out_dir: Path) -> Path:
    """yt-dlp 로 영상(비디오+오디오) mp4 다운로드. 프레임 추출에 영상 스트림 필수."""
    try:
        from yt_dlp import YoutubeDL
    except Exception:
        _fail("yt-dlp 미설치 — pip install yt-dlp (또는 --video 로 로컬 mp4 지정)")
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "source.mp4"
    opts = {
        "outtmpl": str(out_dir / "source.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "merge_output_format": "mp4",
        # 프레임 캡처엔 1080p면 충분 — 4K 받느라 다운로드가 길어지는 것 방지
        "format": ("bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/"
                   "best[height<=1080][ext=mp4]/best[ext=mp4]/best"),
    }
    with YoutubeDL(opts) as ydl:
        ydl.extract_info(url, download=True)
    if not target.exists():  # 병합 확장자가 다르면 첫 source.* 채택
        cands = sorted(out_dir.glob("source.*"))
        if not cands:
            _fail("다운로드 결과 파일을 찾지 못함")
        target = cands[0]
    return target


def transcribe(video: Path, model: str, device: str, compute_type: str,
               lang: str | None) -> list[dict]:
    """faster-whisper 로 세그먼트별 (start, end, text) 추출."""
    print(f"[init] 모델 로드: {model} (device={device}, compute_type={compute_type})",
          flush=True)
    try:
        from faster_whisper import WhisperModel
        wm = WhisperModel(model, device=device, compute_type=compute_type)
    except Exception as e:
        _fail(f"모델 로드 실패 → {e!r} (GPU 없으면 --device cpu --compute-type int8)")
    print(f"[asr] {video.name} 전사 중...", flush=True)
    segments, info = wm.transcribe(str(video), language=lang, vad_filter=True,
                                   beam_size=5)
    out = []
    for seg in segments:
        out.append({"start": float(seg.start), "end": float(seg.end),
                    "text": seg.text.strip()})
    print(f"[asr] 세그먼트 {len(out)}개 (lang={info.language})", flush=True)
    return out


def grab_frame(ffmpeg: str, video: Path, t: float, out_path: Path) -> bool:
    """ffmpeg 로 t초 지점 프레임 1장 추출. 빠른 seek 위해 -ss 를 -i 앞에."""
    cmd = [ffmpeg, "-y", "-ss", f"{t:.2f}", "-i", str(video),
           "-frames:v", "1", "-q:v", "2", str(out_path)]
    r = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return r.returncode == 0 and out_path.exists()


def main() -> None:
    p = argparse.ArgumentParser(description="mp4 → Whisper → 고기 설명 구간 프레임 캡처")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--video", help="로컬 mp4 경로")
    src.add_argument("--url", help="유튜브 등 URL (yt-dlp로 다운로드)")
    p.add_argument("--out", default=None, help="출력 폴더 (기본: ./out_<영상이름>)")
    p.add_argument("--model", default="large-v3", help="whisper 모델 (기본 large-v3)")
    p.add_argument("--device", default="cuda", help="cuda/cpu/auto (기본 cuda)")
    p.add_argument("--compute-type", default="float16",
                   help="float16/int8_float16/int8/float32 (기본 float16)")
    p.add_argument("--lang", default="ko", help="언어 강제 (기본 ko, 자동감지는 빈값)")
    p.add_argument("--keywords", default=None,
                   help="고기 키워드 콤마구분 (미지정 시 내장 기본셋)")
    p.add_argument("--min-gap", type=float, default=6.0,
                   help="연속 캡처 최소 간격(초) — 비슷한 프레임 폭증 방지 (기본 6)")
    p.add_argument("--pad", type=float, default=0.0,
                   help="캡처 시점 보정(초). 세그먼트 중간 기준에서 +/- 이동 (기본 0)")
    p.add_argument("--max-frames", type=int, default=200,
                   help="최대 캡처 장수 안전장치 (기본 200)")
    args = p.parse_args()

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        _fail("ffmpeg 를 PATH 에서 찾지 못함 — winget install Gyan.FFmpeg")

    # 출력 폴더
    if args.url and not args.out:
        out_dir = Path("out_url")
    elif args.out:
        out_dir = Path(args.out)
    else:
        out_dir = Path(f"out_{Path(args.video).stem}")
    out_dir.mkdir(parents=True, exist_ok=True)
    frames_dir = out_dir / "frames"
    frames_dir.mkdir(exist_ok=True)

    # 영상 확보
    if args.url:
        print(f"[dl] {args.url}", flush=True)
        video = download_mp4(args.url, out_dir)
    else:
        video = Path(args.video)
        if not video.exists():
            _fail(f"영상 파일 없음: {video}")
    print(f"[video] {video}", flush=True)

    # 전사
    segs = transcribe(video, args.model, args.device, args.compute_type,
                      args.lang or None)
    if not segs:
        _fail("전사 결과가 비었음 (오디오 없음/무음?)")

    # 타임스탬프 전사 저장
    timed = out_dir / "transcript_timed.txt"
    with timed.open("w", encoding="utf-8") as f:
        for s in segs:
            f.write(f"[{_mmss(s['start'])}] {s['text']}\n")

    # 키워드 필터 + 간격 dedup
    kws = ([k.strip() for k in args.keywords.split(",") if k.strip()]
           if args.keywords else DEFAULT_KEYWORDS)
    kws_l = [k.lower() for k in kws]

    captures: list[dict] = []
    last_t = -1e9
    for s in segs:
        text_l = s["text"].lower()
        hit = [k for k, kl in zip(kws, kws_l) if kl in text_l]
        if not hit:
            continue
        # 세그먼트 중간 + pad 를 대표 시점으로 (설명 도중 화면에 고기가 있을 확률↑)
        t = max(0.0, (s["start"] + s["end"]) / 2.0 + args.pad)
        if t - last_t < args.min_gap:
            continue  # 직전 캡처와 너무 가까우면 스킵
        last_t = t
        captures.append({"t": t, "start": s["start"], "end": s["end"],
                         "text": s["text"], "matched": hit})
        if len(captures) >= args.max_frames:
            print(f"[warn] max-frames({args.max_frames}) 도달 — 이후 구간 스킵",
                  flush=True)
            break

    print(f"[match] 고기 설명 구간 {len(captures)}개 → 프레임 추출", flush=True)

    # 프레임 추출
    ok = 0
    for i, c in enumerate(captures, 1):
        name = f"{i:03d}_{_mmss(c['t'])}_{_slug(c['text'])}.jpg"
        fp = frames_dir / name
        if grab_frame(ffmpeg, video, c["t"], fp):
            c["frame"] = str(fp.relative_to(out_dir))
            ok += 1
            print(f"  [ok {i}/{len(captures)}] {name}  ←  {c['text'][:40]}", flush=True)
        else:
            c["frame"] = None
            print(f"  [err {i}] 프레임 추출 실패 t={c['t']:.1f}", flush=True)

    # 인덱스 저장 (jsonl + 사람이 보는 md)
    with (out_dir / "captures.jsonl").open("w", encoding="utf-8") as f:
        for c in captures:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    with (out_dir / "index.md").open("w", encoding="utf-8") as f:
        f.write(f"# 고기 프레임 캡처 — {video.name}\n\n")
        f.write(f"- 영상: `{video.name}`\n- 캡처: {ok}/{len(captures)}장\n")
        f.write(f"- 키워드: {', '.join(kws)}\n\n")
        for c in captures:
            if not c.get("frame"):
                continue
            f.write(f"### [{_mmss(c['t'])}] {', '.join(c['matched'])}\n")
            f.write(f"> {c['text']}\n\n")
            f.write(f"![{_mmss(c['t'])}]({c['frame']})\n\n")

    print(f"[summary] {ok}/{len(captures)} 프레임 저장 → {frames_dir}", flush=True)
    print(f"[out] 인덱스: {out_dir / 'index.md'} | 전사: {timed}", flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
