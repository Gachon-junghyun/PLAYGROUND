import json
rows = [json.loads(l) for l in open("data_dating/queue_all.jsonl", encoding="utf-8") if l.strip()]
by_ch = {}
for i, r in enumerate(rows):
    by_ch.setdefault(r["channel"], []).append((i, r["title"]))
for ch, items in by_ch.items():
    print(f"\n=== {ch} ({len(items)}) ===")
    for i, t in items:
        print(f"  [{i:>3}] {t}")
print(f"\nTOTAL: {len(rows)}")
