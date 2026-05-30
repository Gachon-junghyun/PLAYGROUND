"""Phase 1: 두 풀(A=mvp R5 v3, B=PLAY31 신규)을 한 jsonl로 합친다.

각 함수에 origin 메타를 박는다:
  origin = "A_mvp_v3"  → 기존 44개
  origin = "B_play31"  → 신규 66개 (출처 배치 파일도 같이 기록)

source_card_count 정규화: 기존엔 정수, 신규엔 같은 의미 → 그대로 유지.

출력: data/pool_combined.jsonl (110줄)
"""
import json
import glob
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MVP_R5 = r"C:\Users\fivep\OneDrive\Desktop\mvp\research_Mvp\insight_corpus\r5_thinking_functions.json"
PLAY31_DIR = os.path.normpath(os.path.join(ROOT, "..", "PLAY31_broker_report_distill", "data", "cards"))
OUT = os.path.join(ROOT, "data", "pool_combined.jsonl")


def collect_a():
    with open(MVP_R5, "rb") as f:
        data = json.load(f)
    out = []
    for fn in data["functions"]:
        fn = dict(fn)
        fn["_origin"] = "A_mvp_v3"
        fn["_origin_file"] = "mvp/research_Mvp/insight_corpus/r5_thinking_functions.json"
        out.append(fn)
    return out


def collect_b():
    out = []
    for fp in sorted(glob.glob(os.path.join(PLAY31_DIR, "*.functions.jsonl"))):
        batch = os.path.basename(fp).replace(".functions.jsonl", "")
        with open(fp, "rb") as f:
            for line in f:
                if not line.strip():
                    continue
                fn = json.loads(line)
                fn["_origin"] = "B_play31"
                fn["_origin_file"] = f"PLAY31_broker_report_distill/data/cards/{batch}.functions.jsonl"
                fn["_origin_batch"] = batch
                out.append(fn)
    return out


def main():
    a = collect_a()
    b = collect_b()
    print(f"A (mvp v3): {len(a)} functions")
    print(f"B (PLAY31): {len(b)} functions")
    print(f"TOTAL: {len(a)+len(b)}")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        for fn in a + b:
            f.write(json.dumps(fn, ensure_ascii=False) + "\n")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
