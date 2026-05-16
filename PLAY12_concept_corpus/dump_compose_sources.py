"""compose 단계에 어떤 본문이 들어갔는지 reports/<slug>_compose_inputs.md로 저장."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from _common import REPORTS_ROOT, topic_dir


def main(topic: str) -> int:
    tdir = topic_dir(topic)
    srcs_path = tdir / "sources.jsonl"
    cdir = tdir / "_compose"
    if not srcs_path.exists() or not cdir.exists():
        print(f"[dump] {srcs_path} 또는 {cdir} 없음", file=sys.stderr)
        return 1

    srcs = {
        s["id"]: s
        for s in (json.loads(l) for l in srcs_path.read_text(encoding="utf-8").splitlines() if l.strip())
    }

    out = [f"# {topic} — compose 입력 본문 dump\n",
           "compose의 batch prompt들에 실제로 박혔던 본문(SOURCES 섹션) 발췌. "
           "각 source의 본문 출처(abstract vs fetch)와 첫 300자를 표시.\n"]

    total = 0
    for bp in sorted(cdir.glob("batch_*.prompt.md")):
        text = bp.read_text(encoding="utf-8")
        body_part = text.split("SOURCES:", 1)[1] if "SOURCES:" in text else ""
        blocks = re.split(r"\n(?=\[src_\d+\])", body_part)
        n = sum(1 for b in blocks if b.strip().startswith("["))
        out.append(f"\n## {bp.name} ({n} sources)\n")
        for blk in blocks:
            blk = blk.strip()
            if not blk.startswith("["):
                continue
            m = re.match(r"\[(src_\d+)\]\s*(.+?)\n", blk)
            if not m:
                continue
            sid, title = m.group(1), m.group(2)
            src = srcs.get(sid, {})
            body_m = re.search(r"\n\s*body:\s*(.+)", blk, flags=re.DOTALL)
            body = body_m.group(1).strip() if body_m else ""
            body_preview = re.sub(r"\s+", " ", body[:300]) + ("…" if len(body) > 300 else "")
            origin = "abstract" if (
                src.get("type") in ("paper", "survey", "wiki", "standard", "textbook")
                and len(src.get("abstract", "")) >= 150
            ) else f"fetch ({src.get('text_mode', 'none')})"
            d = src.get("domain") or "—"
            auth = src.get("authority", "—")
            typ = src.get("type", "—")
            tm = src.get("text_mode", "none")
            out.append(f"### [{sid}] {title}")
            out.append(
                f"- 도메인 `{d}` · 권위 `{auth}` · 타입 `{typ}` · text_mode `{tm}` · "
                f"본문 출처 **{origin}** · 본문 길이 **{len(body)}B**"
            )
            out.append(f"- URL: {src.get('url', '—')}")
            out.append("\n```")
            out.append(body_preview)
            out.append("```\n")
            total += 1

    out.append(f"\n---\n**총 {total} sources가 compose batch prompt에 들어갔다.**\n")

    out_path = REPORTS_ROOT / f"{tdir.name}_compose_inputs.md"
    out_path.write_text("\n".join(out), encoding="utf-8")
    print(f"[dump] {out_path}  ({total} sources)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "피지컬 AI"))
