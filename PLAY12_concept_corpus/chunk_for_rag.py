"""chunk_for_rag — sources + texts/ → chunks.jsonl.

문자(=대략 토큰의 1.5~3배) 단위로 sliding window 청크. RAG 색인에 그대로 들어갈 형태.
text_mode가 'none'인 source는 건너뜀.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from _common import read_jsonl, topic_dir, write_jsonl


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[tuple[int, str]]:
    if chunk_size <= 0:
        return [(0, text)]
    if overlap < 0:
        overlap = 0
    if overlap >= chunk_size:
        overlap = chunk_size // 4

    out = []
    step = chunk_size - overlap
    i = 0
    while i < len(text):
        piece = text[i : i + chunk_size]
        if not piece.strip():
            i += step
            continue
        out.append((i, piece))
        if i + chunk_size >= len(text):
            break
        i += step
    return out


def parse_where(expr: str | None) -> dict[str, str]:
    if not expr:
        return {}
    out = {}
    for clause in expr.split(","):
        if "=" not in clause:
            continue
        k, v = clause.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def match_where(src: dict, where: dict) -> bool:
    for k, v in where.items():
        if str(src.get(k)) != v:
            return False
    return True


def main():
    p = argparse.ArgumentParser()
    p.add_argument("topic")
    p.add_argument("--chunk-size", type=int, default=800, help="문자 단위")
    p.add_argument("--overlap", type=int, default=100)
    p.add_argument("--where", help="필터, 예: 'text_mode=full,authority=high'")
    args = p.parse_args()

    tdir = topic_dir(args.topic)
    src_path = tdir / "sources.jsonl"
    if not src_path.exists():
        print(f"[chunk] {src_path} 없음", file=sys.stderr)
        return 1

    where = parse_where(args.where)

    chunks: list[dict] = []
    cid = 0
    n_src_used = 0
    n_src_skipped = 0
    for src in read_jsonl(src_path):
        if src.get("text_mode") in (None, "none"):
            n_src_skipped += 1
            continue
        if where and not match_where(src, where):
            n_src_skipped += 1
            continue
        text_path = tdir / src["text_path"]
        if not text_path.exists():
            print(f"  [{src['id']}] text_path 없음 ({text_path}) — 건너뜀")
            n_src_skipped += 1
            continue

        text = text_path.read_text(encoding="utf-8")
        n_src_used += 1
        for offset, piece in chunk_text(text, args.chunk_size, args.overlap):
            cid += 1
            chunks.append({
                "id": f"chunk_{cid:05d}",
                "source_id": src["id"],
                "text_mode": src["text_mode"],
                "offset": offset,
                "length": len(piece),
                "text": piece,
                "title": src["title"],
                "authority": src["authority"],
                "url": src["url"],
            })

    n = write_jsonl(tdir / "chunks.jsonl", chunks)
    print(f"[chunk] sources used {n_src_used} (skipped {n_src_skipped}) → {n} chunks")
    print(f"  out: {tdir / 'chunks.jsonl'}")
    print(f"  chunk_size={args.chunk_size}  overlap={args.overlap}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
