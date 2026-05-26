"""Parse a structured lecture script and synthesize per-slide WAVs.

Two input formats are auto-detected:

Format A — tagged blocks (e.g. 코스닥3000_강의스크립트.txt):
    ─── separator ───
      슬라이드 N.  <title>
    ─── separator ───
    [화면] ...
    [발화]
    <text to synthesize, possibly multi-paragraph>
    [핵심] ...

  Only [발화] blocks are synthesized.

Format B — bracketed headers, plain body (e.g. GIC 강의 스크립트):
    [슬라이드 N. <title>]

    <plain paragraph body, fully synthesized>

    ================  (separator: '=' or '═' or '─')

  Everything between two slide headers (excluding the header line and
  separators) is the speech text. Optional `--out-dir` chooses output
  location; default is out/slides relative to this script.

One WAV per slide -> <out_dir>/slide_NN.wav.

Run:
    .venv/Scripts/python.exe -u tts_lecture.py 코스닥3000_강의스크립트.txt
    .venv/Scripts/python.exe -u tts_lecture.py path/to/gic_script.txt --out-dir out/gic
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except AttributeError:
    pass

ROOT = Path(__file__).parent
DEFAULT_OUT_DIR = ROOT / "out" / "slides"

SLIDE_RE = re.compile(r"^\s*슬라이드\s+(\d+)\.\s*(.*)$")
BRACKET_SLIDE_RE = re.compile(r"^\s*\[\s*슬라이드\s+(\d+)\.\s*(.+?)\s*\]\s*$")
TAG_RE = re.compile(r"^\[(화면|발화|핵심)\]")
DECOR_RE = re.compile(r"^[═─=]{5,}\s*$")


def normalize_for_kr_tts(text: str) -> str:
    """Replace symbols that crash MeloTTS Korean g2p (KeyError)."""
    # "+155%" -> " 플러스 155%". MeloTTS handles % via num2words.
    text = re.sub(r"\+(\d)", r" 플러스 \1", text)
    # Leftover bare "+" -> drop.
    text = text.replace("+", " ")
    return text


def parse_slides_bracket(text: str) -> list[tuple[int, str, str]]:
    """Format B: [슬라이드 N. 제목] header, full body is speech."""
    lines = text.splitlines()
    slides: list[tuple[int, str, str]] = []

    cur_num: int | None = None
    cur_title: str = ""
    cur_body: list[str] = []

    def flush():
        if cur_num is not None:
            body = "\n".join(cur_body).strip()
            if body:
                slides.append((cur_num, cur_title, body))

    for line in lines:
        m = BRACKET_SLIDE_RE.match(line)
        if m:
            flush()
            cur_num = int(m.group(1))
            cur_title = m.group(2).strip()
            cur_body = []
            continue
        if DECOR_RE.match(line):
            continue
        if cur_num is not None:
            cur_body.append(line)

    flush()
    return slides


def parse_slides_tagged(text: str) -> list[tuple[int, str, str]]:
    """Format A: bare 슬라이드 N. header, only [발화] block is speech."""
    lines = text.splitlines()
    slides: list[tuple[int, str, str]] = []

    i = 0
    cur_num: int | None = None
    cur_title: str = ""
    cur_speech: list[str] = []
    in_speech = False
    in_other_tag = False

    def flush():
        if cur_num is not None and cur_speech:
            speech = "\n".join(cur_speech).strip()
            if speech:
                slides.append((cur_num, cur_title, speech))

    while i < len(lines):
        line = lines[i]
        m = SLIDE_RE.match(line)
        if m:
            flush()
            cur_num = int(m.group(1))
            cur_title = m.group(2).strip()
            cur_speech = []
            in_speech = False
            in_other_tag = False
            i += 1
            continue

        tag_m = TAG_RE.match(line)
        if tag_m:
            tag = tag_m.group(1)
            if tag == "발화":
                in_speech = True
                in_other_tag = False
                after_tag = line[tag_m.end():].strip()
                if after_tag:
                    cur_speech.append(after_tag)
            else:
                in_speech = False
                in_other_tag = True
            i += 1
            continue

        if DECOR_RE.match(line):
            in_speech = False
            in_other_tag = False
            i += 1
            continue

        if in_speech:
            cur_speech.append(line)
        i += 1

    flush()
    return slides


def parse_slides(text: str) -> list[tuple[int, str, str]]:
    """Auto-detect format and dispatch. Bracket-header wins if present."""
    if any(BRACKET_SLIDE_RE.match(ln) for ln in text.splitlines()):
        return parse_slides_bracket(text)
    return parse_slides_tagged(text)


def main() -> int:
    if len(sys.argv) < 2:
        print(
            "usage: tts_lecture.py <script.txt> [--only N,N,N] [--out-dir DIR]",
            file=sys.stderr,
        )
        return 2

    src = Path(sys.argv[1])
    only_set: set[int] | None = None
    if "--only" in sys.argv:
        idx = sys.argv.index("--only")
        only_set = {int(x) for x in sys.argv[idx + 1].split(",")}

    out_dir = DEFAULT_OUT_DIR
    if "--out-dir" in sys.argv:
        idx = sys.argv.index("--out-dir")
        out_dir = Path(sys.argv[idx + 1])
        if not out_dir.is_absolute():
            out_dir = ROOT / out_dir

    text = src.read_text(encoding="utf-8")
    slides = parse_slides(text)
    print(f"[parsed] {len(slides)} slides with speech", flush=True)

    out_dir.mkdir(parents=True, exist_ok=True)

    # Save parsed speech to a sidecar file for review.
    sidecar = out_dir / "_parsed.txt"
    with sidecar.open("w", encoding="utf-8") as f:
        for num, title, speech in slides:
            f.write(f"=== 슬라이드 {num}. {title} ===\n{speech}\n\n")
    print(f"[wrote] {sidecar}", flush=True)

    print("[loading] melo TTS (KR)...", flush=True)
    from melo.api import TTS

    model = TTS(language="KR", device="cpu")
    spk_id = model.hps.data.spk2id["KR"]

    targets = [s for s in slides if only_set is None or s[0] in only_set]
    for idx, (num, title, speech) in enumerate(targets, 1):
        flat = " ".join(s.strip() for s in speech.splitlines() if s.strip())
        flat = normalize_for_kr_tts(flat)
        out_path = out_dir / f"slide_{num:02d}.wav"
        char_count = len(flat)
        print(
            f"[synth {idx}/{len(targets)}] slide {num} ({char_count} chars): {title}",
            flush=True,
        )
        try:
            model.tts_to_file(flat, spk_id, str(out_path), speed=1.0)
            print(f"  -> {out_path.name}", flush=True)
        except Exception as e:
            print(f"  FAILED slide {num}: {type(e).__name__}: {e}", flush=True)

    print("DONE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
