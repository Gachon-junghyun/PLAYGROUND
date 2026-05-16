"""공통 유틸: slug, 경로, jsonl 입출력, SSL 컨텍스트."""

from __future__ import annotations

import json
import re
import ssl
import sys
from pathlib import Path
from typing import Iterable, Iterator

# Windows cp949 콘솔에서 한글·em-dash 깨짐 방지 (Python 3.7+).
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


# --- SSL context (Windows Python에서 시스템 CA 못 잡는 케이스 대비) ---

def make_ssl_context(verify: bool = True) -> ssl.SSLContext:
    if not verify:
        return ssl._create_unverified_context()
    ctx = ssl.create_default_context()
    try:
        ctx.load_default_certs(ssl.Purpose.SERVER_AUTH)
    except Exception:
        pass
    return ctx


_SSL_CTX = make_ssl_context(verify=True)


def get_ssl_context() -> ssl.SSLContext:
    return _SSL_CTX


def set_ssl_verify(verify: bool) -> None:
    global _SSL_CTX
    _SSL_CTX = make_ssl_context(verify=verify)
    if not verify:
        print("[ssl] WARNING: 인증서 검증 비활성화 (--insecure)", file=sys.stderr)

ROOT = Path(__file__).parent
DATA_ROOT = ROOT / "data"
REPORTS_ROOT = ROOT / "reports"

AUTHORITY_BY_TYPE = {
    "survey": "high",
    "standard": "high",
    "textbook": "high",
    "paper": "medium",
    "wiki": "medium",
    "report": "medium",
    "blog": "low",
    "news": "low",
}


def slugify(topic: str) -> str:
    s = topic.strip().lower()
    s = re.sub(r"[^\w\-가-힣]+", "_", s, flags=re.UNICODE)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "topic"


def topic_dir(topic: str) -> Path:
    d = DATA_ROOT / slugify(topic)
    d.mkdir(parents=True, exist_ok=True)
    (d / "texts").mkdir(exist_ok=True)
    return d


def read_jsonl(path: Path) -> Iterator[dict]:
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def write_jsonl(path: Path, rows: Iterable[dict]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            n += 1
    return n


def append_jsonl(path: Path, rows: Iterable[dict]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            n += 1
    return n


def authority_of(source_type: str) -> str:
    return AUTHORITY_BY_TYPE.get(source_type, "low")
