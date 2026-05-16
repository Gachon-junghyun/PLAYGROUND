"""MeloTTS thin CLI wrapper.

text -> wav. Multi-language (EN, KR, JP, ZH, ES, FR).
First run downloads model weights to HF cache (~hundreds of MB) — must be
done out-of-band before dispatch use. See README.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

LANG_DEFAULT_SPEAKER = {
    "EN": "EN-Default",
    "KR": "KR",
    "JP": "JP",
    "ZH": "ZH",
    "ES": "ES",
    "FR": "FR",
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="MeloTTS text->wav")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--text", type=str, help="inline text")
    src.add_argument("--text-file", type=Path, help="utf-8 text file")

    p.add_argument(
        "--lang",
        required=True,
        choices=sorted(LANG_DEFAULT_SPEAKER.keys()),
        help="language code",
    )
    p.add_argument(
        "--speaker",
        default=None,
        help="speaker id (e.g. EN-US, EN-BR, EN-Default). Defaults per lang.",
    )
    p.add_argument("--out", type=Path, required=True, help="output wav path")
    p.add_argument("--speed", type=float, default=1.0, help="speech speed (1.0=normal)")
    p.add_argument(
        "--device",
        default="auto",
        help="auto / cpu / cuda / cuda:0 / mps",
    )
    return p.parse_args()


def read_text(args: argparse.Namespace) -> str:
    if args.text is not None:
        return args.text
    return args.text_file.read_text(encoding="utf-8").strip()


def main() -> int:
    args = parse_args()
    text = read_text(args)
    if not text:
        print("error: empty text", file=sys.stderr)
        return 2

    try:
        from melo.api import TTS
    except ImportError as e:
        print(
            "error: melo not installed. See README for pre-install steps.\n"
            f"  {e}",
            file=sys.stderr,
        )
        return 1

    model = TTS(language=args.lang, device=args.device)
    spk2id = model.hps.data.spk2id

    speaker = args.speaker or LANG_DEFAULT_SPEAKER[args.lang]
    if speaker not in spk2id:
        # Fall back to first available speaker for the language.
        available = list(spk2id.keys())
        print(
            f"warn: speaker '{speaker}' not in model. available={available}. "
            f"using '{available[0]}'.",
            file=sys.stderr,
        )
        speaker = available[0]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    model.tts_to_file(text, spk2id[speaker], str(args.out), speed=args.speed)
    print(f"wrote {args.out} ({args.lang}/{speaker}, speed={args.speed})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
