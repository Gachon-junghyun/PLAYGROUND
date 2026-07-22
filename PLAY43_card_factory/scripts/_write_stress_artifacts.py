"""스트레스 워크플로우 결과(.output)를 PLAY43 data/ 산출물로 떨군다 (1회용 브리지).

워크플로우는 파일 접근 불가 → 메인이 결과를 받아 파일로 기록하는 orchestrator Step 3 후처리.
  python _write_stress_artifacts.py <workflow.output 경로>
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import STRESS_DIR, REDESIGN_QUEUE, CARDS_DIR, ensure_dirs

ensure_dirs()
out_path = Path(sys.argv[1])
res = json.loads(out_path.read_text(encoding="utf-8"))["result"]

# 신규 후보 full 객체 (cardify 산출에서 로드 — verdict와 조인)
cand_by_id = {}
for fp in CARDS_DIR.glob("*.functions.jsonl"):
    for line in fp.read_text(encoding="utf-8").splitlines():
        if line.strip():
            f = json.loads(line)
            cand_by_id[f.get("function_id")] = f

# 1) 전체 스트레스 리포트
(STRESS_DIR / "stress_report.json").write_text(
    json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")

# 2) survived.jsonl — scc>=2 정식 승격분 (이번 라운드 0)
survived = res.get("survived", [])
(STRESS_DIR / "survived.jsonl").write_text(
    "\n".join(json.dumps(s, ensure_ascii=False) for s in survived), encoding="utf-8")

# 3) candidates_pending.jsonl — 적대검증 생존했으나 단일카드라 보류(2번째 카드 대기)
held_ids = [h["id"] for h in res.get("held_single_card", [])]
verdict_by_id = {x["id"]: x["verdict"] for x in res.get("results", [])}
held = []
for hid in held_ids:
    full = dict(cand_by_id.get(hid, {"function_id": hid}))
    full["_stress_verdict"] = verdict_by_id.get(hid, {})
    full["status"] = "candidate_single_card"
    held.append(full)
(STRESS_DIR / "candidates_pending.jsonl").write_text(
    "\n".join(json.dumps(h, ensure_ascii=False) for h in held), encoding="utf-8")

# 4) function_redesign_queue.jsonl — 라이브러리 진화 후보 (append)
with REDESIGN_QUEUE.open("a", encoding="utf-8") as f:
    for rd in res.get("redesign", []):
        f.write(json.dumps(rd, ensure_ascii=False) + "\n")

print("WROTE stress_report.json /",
      f"survived={len(survived)} /",
      f"candidates_pending={len(held)} /",
      f"redesign_appended={len(res.get('redesign', []))}")
