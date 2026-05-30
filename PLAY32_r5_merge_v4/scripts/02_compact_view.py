"""Phase 2 사전 단계: pool_combined.jsonl을 Agent가 보기 좋은 compact view로 변환.

각 함수에서 클러스터링 판정에 필요한 핵심 필드만 추출.
출력: data/pool_compact.md (사람 + Agent가 한 화면에 110 함수 비교 가능)
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IN = os.path.join(ROOT, "data", "pool_combined.jsonl")
OUT = os.path.join(ROOT, "data", "pool_compact.md")


def trunc(s, n):
    if s is None:
        return ""
    s = str(s).replace("\n", " ").strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def main():
    funcs = []
    with open(IN, "rb") as f:
        for line in f:
            funcs.append(json.loads(line))

    a = [fn for fn in funcs if fn["_origin"] == "A_mvp_v3"]
    b = [fn for fn in funcs if fn["_origin"] == "B_play31"]

    with open(OUT, "w", encoding="utf-8") as f:
        f.write(f"# pool_compact (총 {len(funcs)} 함수)\n\n")
        f.write(f"- A (mvp R5 v3): {len(a)}개 (F01~F44)\n")
        f.write(f"- B (PLAY31 신규): {len(b)}개 (임시 ID)\n\n")
        f.write("각 함수: `id | scards | domains | name`\n")
        f.write("그리고 abstract_form, trigger_when, anti_signal 1줄씩.\n\n")

        for label, group in [("A_mvp_v3 (기존)", a), ("B_play31 (신규)", b)]:
            f.write(f"## {label}\n\n")
            for fn in group:
                fid = fn.get("function_id", "?")
                scards = fn.get("source_card_count", "?")
                doms = ",".join(fn.get("applies_to_domain", []))
                name = fn.get("name", "")
                af = trunc(fn.get("abstract_form", ""), 280)
                tw = trunc(fn.get("trigger_when", ""), 180)
                anti = trunc(fn.get("anti_signal", ""), 180)
                f.write(f"### {fid} | scards={scards} | {doms}\n")
                f.write(f"**name**: {name}\n\n")
                f.write(f"- abstract: {af}\n")
                f.write(f"- trigger: {tw}\n")
                f.write(f"- anti: {anti}\n\n")
    print(f"wrote {OUT}")
    print(f"size: {os.path.getsize(OUT)/1024:.1f} KB")


if __name__ == "__main__":
    main()
