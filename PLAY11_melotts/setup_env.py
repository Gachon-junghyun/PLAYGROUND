"""Install MeloTTS into PLAY11_melotts/.venv/ (isolated, no global pollution).

Run with:
    python -u setup_env.py > setup.log 2>&1

Emits step lines and a final DONE / FAILED sentinel for polling.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
VENV = ROOT / ".venv"
VENV_PY = VENV / "Scripts" / "python.exe"  # Windows
SITE = VENV / "Lib" / "site-packages"
SHIMS = ROOT / "_shims"

STEPS: list[tuple[str, list[str]]] = [
    ("create venv", [sys.executable, "-m", "venv", str(VENV)]),
    ("upgrade pip", [str(VENV_PY), "-m", "pip", "install", "--upgrade", "pip"]),
    (
        "install torch CPU",
        [
            str(VENV_PY), "-m", "pip", "install",
            "--index-url", "https://download.pytorch.org/whl/cpu",
            "torch",
        ],
    ),
    (
        "install MeloTTS",
        [
            str(VENV_PY), "-m", "pip", "install",
            "git+https://github.com/myshell-ai/MeloTTS.git",
        ],
    ),
    (
        "NLTK averaged_perceptron_tagger_eng",
        [
            str(VENV_PY), "-c",
            "import nltk; nltk.download('averaged_perceptron_tagger_eng')",
        ],
    ),
    (
        "unidic JP dictionary (required even for non-JP — melo imports japanese.py)",
        [str(VENV_PY), "-m", "unidic", "download"],
    ),
]


def install_shims() -> None:
    """Copy _shims/<pkg>/ into venv site-packages. Needed for KR (eunjeon)
    because building real eunjeon on Windows requires VS Build Tools."""
    if not SHIMS.exists():
        return
    for pkg_dir in SHIMS.iterdir():
        if not pkg_dir.is_dir():
            continue
        dest = SITE / pkg_dir.name
        # Skip if real package already installed (don't overwrite).
        if dest.exists():
            print(f"[shim] {pkg_dir.name}: real package present, skipping shim", flush=True)
            continue
        shutil.copytree(pkg_dir, dest)
        print(f"[shim] installed {pkg_dir.name} -> {dest}", flush=True)


def main() -> int:
    print("[start]", flush=True)
    total = len(STEPS)
    for i, (name, cmd) in enumerate(STEPS, 1):
        print(f"[step {i}/{total}] {name}", flush=True)
        r = subprocess.run(cmd)
        if r.returncode != 0:
            print(f"FAILED: step {i} ({name}) exit={r.returncode}", flush=True)
            return 1
    print(f"[step {total + 1}/{total + 1}] install shims (eunjeon for KR)", flush=True)
    install_shims()
    print("DONE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
