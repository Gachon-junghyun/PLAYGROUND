"""통과 사고함수 → v5 작업사본(r5_v5_working.json) append. 원본 v4 절대 불변.

  python 04_merge_v4.py            # data/stress/survived.jsonl 머지
  python 04_merge_v4.py --status   # 작업사본 현황만

승격 게이트는 stress_test 단계에서 이미 적용됨(survives + source_card_count>=2).
여기서는 survived.jsonl 의 함수에 function_id F88+ 순차 할당 후 append만.
redesign_queue 항목은 기존 함수 anti_signal 보강(작업사본에만).
"""
import argparse
import datetime
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import V4_LIB, V5_WORKING, STRESS_DIR, REDESIGN_QUEUE, ensure_dirs

# v5 신규 함수가 반드시 채워야 할 17필드 기본값 (PLAY32 Phase 4 방식 — R6 빈 필드 박기)
_R6_DEFAULTS = {
    "verification_questions": [], "anti_signal": "", "source_cards": [],
    "source_card_count": 1, "framework_resonance": [], "applies_to_domain": [],
    "example_application": {}, "related_functions": [], "data_sources": [],
    "indicators": [], "action_at_trigger": {}, "backtest_log": [],
    "indicators_examples_specific": [],
}


def _ensure_working():
    if not V5_WORKING.exists():
        ensure_dirs()
        v4 = json.loads(V4_LIB.read_text(encoding="utf-8"))
        v4["version"] = "v5-working"
        v4["source"] = f"copy of {V4_LIB.name} (원본 불변) + PLAY43 survived merges"
        v4["created_at"] = str(datetime.date.today())
        V5_WORKING.write_text(json.dumps(v4, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[init] v4 → {V5_WORKING.name} 복사 (원본 무변경)")
    return json.loads(V5_WORKING.read_text(encoding="utf-8"))


def _next_fid(lib):
    nums = [int(f["function_id"][1:]) for f in lib["functions"]
            if f["function_id"].startswith("F") and f["function_id"][1:].isdigit()]
    return (max(nums) + 1) if nums else 1


def show_status():
    if not V5_WORKING.exists():
        print("작업사본 없음 — 아직 머지 안 됨. 원본 v4 그대로.")
        return
    lib = json.loads(V5_WORKING.read_text(encoding="utf-8"))
    base = json.loads(V4_LIB.read_text(encoding="utf-8"))
    print(f"[status] v5-working {lib['total_functions']}함수 + 후보 {len(lib.get('candidates', []))} "
          f"(원본 v4 {base['total_functions']}함수)")
    added = [f for f in lib["functions"] if f["function_id"] not in
             {b["function_id"] for b in base["functions"]}]
    for f in added:
        print(f"  +정식 {f['function_id']}  {f.get('name', '')}  (scc={f.get('source_card_count')})")
    for c in lib.get("candidates", []):
        print(f"  ~후보 {c.get('function_id')}  {c.get('name', '')[:42]}  (scc={c.get('source_card_count')})")


def merge(args):
    survived_f = STRESS_DIR / "survived.jsonl"
    pending_f = STRESS_DIR / "candidates_pending.jsonl"
    if not survived_f.exists() and not pending_f.exists():
        print("survived/candidates_pending 없음 — 스트레스 테스트 먼저 (data/stress/)")
        return

    def _read(p):
        return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()] if p.exists() else []

    survived = _read(survived_f)      # 적대검증 생존 AND scc>=2 → functions[] 정식 등재
    pending = _read(pending_f)        # 적대검증 생존이나 scc<2 → candidates[] 보류
    lib = _ensure_working()
    lib.setdefault("candidates", [])
    existing_names = {f.get("name") for f in lib["functions"]}
    cand_names = {c.get("name") for c in lib["candidates"]}

    # ── 정식 등재 (F88+) ──
    added = 0
    for fn in survived:
        if fn.get("name") in existing_names:
            print(f"  [skip] 동명 함수 이미 존재: {fn.get('name')}")
            continue
        for k, default in _R6_DEFAULTS.items():
            fn.setdefault(k, default)
        fn["function_id"] = f"F{_next_fid(lib):02d}"
        lib["functions"].append(fn)
        existing_names.add(fn.get("name"))
        print(f"  [official] {fn['function_id']}  {fn.get('name')}  (scc={fn.get('source_card_count')})")
        added += 1

    # ── 후보 보류 (temp id 유지, 2번째 카드 대기) ──
    held = 0
    for c in pending:
        if c.get("name") in cand_names or c.get("name") in existing_names:
            print(f"  [skip] 후보 중복: {c.get('name')}")
            continue
        lib["candidates"].append(c)
        cand_names.add(c.get("name"))
        print(f"  [candidate] {c.get('function_id')}  {c.get('name','')[:40]}  (scc={c.get('source_card_count')}, 적대검증 생존)")
        held += 1

    lib["total_functions"] = len(lib["functions"])
    lib["total_candidates"] = len(lib["candidates"])
    lib["updated_at"] = str(datetime.date.today())
    V5_WORKING.write_text(json.dumps(lib, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[merge] 정식 +{added} (총 {lib['total_functions']}) / 후보 +{held} (총 {lib['total_candidates']})")
    print("        ※ 단일카드 후보는 2번째 리포트가 같은 사고를 내면 scc>=2로 정식 승격(다음 주기).")


def main():
    ap = argparse.ArgumentParser(description="PLAY43 v5 작업사본 머지")
    ap.add_argument("--status", action="store_true", help="현황만 출력")
    args = ap.parse_args()
    if args.status:
        show_status()
    else:
        merge(args)


if __name__ == "__main__":
    main()
