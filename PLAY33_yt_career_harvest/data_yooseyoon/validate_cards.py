# data_yooseyoon/validate_cards.py
"""cards/B*.jsonl 병합·검증: card_id 중복, evidence 누락, 축/영상/신뢰도 분포."""
from __future__ import annotations
import json, sys
from pathlib import Path
from collections import Counter

for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

HERE = Path(__file__).resolve().parent
CARDS = sorted((HERE/"cards").glob("B*.jsonl"))
rows=[]
for p in CARDS:
    for line in p.read_text(encoding="utf-8").splitlines():
        line=line.strip()
        if line:
            rows.append((p.name, json.loads(line)))

print(f"[files] {[p.name for p in CARDS]}")
print(f"[total] {len(rows)} cards")

ids=[c["card_id"] for _,c in rows]
dup=[k for k,n in Counter(ids).items() if n>1]
print(f"[dup card_id] {len(dup)} -> {dup}")

no_ev=[c["card_id"] for _,c in rows if not c.get("evidence_quote","").strip()]
print(f"[missing evidence] {len(no_ev)} -> {no_ev}")

print("\n[axis]")
for k,n in Counter(c["axis"] for _,c in rows).most_common():
    print(f"  {k:20} {n}")

print("\n[confidence]")
for k,n in Counter((c.get('confidence','?').split('—')[0].split('-')[0].strip()[:6]) for _,c in rows).most_common():
    print(f"  {k:10} {n}")

print("\n[video]")
for k,n in Counter(c.get("source_video",{}).get("video_id","?") for _,c in rows).most_common():
    print(f"  {k:14} {n}")

# 병합 저장
out=HERE/"cards"/"_all.jsonl"
with out.open("w",encoding="utf-8") as f:
    for _,c in rows: f.write(json.dumps(c,ensure_ascii=False)+"\n")
print(f"\n[merged] -> {out}")
