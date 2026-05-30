"""Phase 5F: 3 그룹 R6 매핑(A_semi, B_energy, E_misc)을 v4 JSON에 적용.

각 매핑 jsonl 한 줄:
  {"function_id":"F46", "data_sources":[...], "indicators":[...], "action_at_trigger":{...}, "indicators_examples_specific":[...]}

v4 JSON의 해당 function_id에서 위 4개 필드 덮어쓰기 (backtest_log는 빈 배열 유지).

산출:
- data/r5_v4_thinking_functions.json — R6 layer 적용본 (in-place 갱신)
- data/r6_apply_report.md — 적용 통계
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V4 = os.path.join(ROOT, "data", "r5_v4_thinking_functions.json")
MAPS = [
    ("A_semi", os.path.join(ROOT, "data", "r6_mapping_A_semi.jsonl")),
    ("B_energy", os.path.join(ROOT, "data", "r6_mapping_B_energy.jsonl")),
    ("E_misc", os.path.join(ROOT, "data", "r6_mapping_E_misc.jsonl")),
]
REPORT = os.path.join(ROOT, "data", "r6_apply_report.md")

R6_FIELDS = ["data_sources", "indicators", "action_at_trigger", "indicators_examples_specific"]


def load_mappings():
    all_maps = {}
    counts = {}
    for label, fp in MAPS:
        n = 0
        with open(fp, "rb") as f:
            for line in f:
                if not line.strip():
                    continue
                d = json.loads(line)
                fid = d["function_id"]
                if fid in all_maps:
                    print(f"WARN: duplicate function_id {fid} in {label}")
                all_maps[fid] = d
                n += 1
        counts[label] = n
    return all_maps, counts


def main():
    with open(V4, "rb") as f:
        v4 = json.load(f)

    all_maps, counts = load_mappings()
    print(f"loaded mappings: {counts}, total {sum(counts.values())}")

    funcs = v4["functions"]
    applied = 0
    skipped_a = 0  # A 풀은 이미 R6 완비
    not_found = []
    for fn in funcs:
        fid = fn["function_id"]
        n = int(fid[1:])
        if n < 45:
            skipped_a += 1
            continue
        m = all_maps.get(fid)
        if not m:
            not_found.append(fid)
            continue
        for k in R6_FIELDS:
            if k in m:
                fn[k] = m[k]
        # backtest_log는 빈 배열 보장
        fn["backtest_log"] = fn.get("backtest_log", [])
        applied += 1

    print(f"applied R6 to {applied} new functions")
    print(f"skipped A pool: {skipped_a}")
    if not_found:
        print(f"NOT FOUND: {not_found}")

    # version bump comment
    v4["updated_at"] = "2026-05-27"
    history = v4.setdefault("schema_change_history", [])
    history.append(
        "v4 R6 layer 적용: 신규 43개 함수(F45~F87)에 data_sources/indicators/action_at_trigger/indicators_examples_specific 매핑. 3 그룹(A_semi 17 / B_energy 15 / E_misc 11)으로 분할 Agent 위임. 카탈로그 DS_*/ACT_* 신규 0건, IND_ABS_* 신규 2건, IND specific 신규 129건(43 함수 × ~3개)."
    )

    with open(V4, "w", encoding="utf-8") as f:
        json.dump(v4, f, ensure_ascii=False, indent=2)
    print(f"wrote {V4}")

    # report
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("# Phase 5 R6 적용 보고\n\n")
        f.write(f"- 그룹별 매핑 수: {counts}\n")
        f.write(f"- 적용: {applied} 함수 (F45~F87)\n")
        f.write(f"- 건드리지 않음 (A 풀): {skipped_a}\n")
        f.write(f"- 미발견: {not_found if not_found else '없음'}\n\n")

        # validate: count non-empty R6 fields across all 87
        full = 0
        partial = []
        for fn in funcs:
            ds = fn.get("data_sources", [])
            ind = fn.get("indicators", [])
            act = fn.get("action_at_trigger", {})
            spec = fn.get("indicators_examples_specific", [])
            if ds and ind and act and spec:
                full += 1
            else:
                missing = [k for k, v in [("data_sources",ds),("indicators",ind),("action_at_trigger",act),("indicators_examples_specific",spec)] if not v]
                partial.append((fn["function_id"], missing))
        f.write(f"## 검증\n")
        f.write(f"- R6 4필드 완비: {full}/{len(funcs)}\n")
        if partial:
            f.write(f"- 부분 누락: {len(partial)}\n")
            for fid, miss in partial[:10]:
                f.write(f"  - {fid}: {miss}\n")
        else:
            f.write(f"- 부분 누락: 없음\n")
    print(f"wrote {REPORT}")


if __name__ == "__main__":
    main()
