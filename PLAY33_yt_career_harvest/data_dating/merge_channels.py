import json, sys
io = "data_dating/"
seen = {}
for f in ["ch_a.jsonl", "ch_b.jsonl", "ch_c.jsonl"]:
    for l in open(io + f, encoding="utf-8"):
        if l.strip():
            r = json.loads(l)
            seen.setdefault(r["channel_id"], r)
rows = sorted(seen.values(), key=lambda r: r.get("subscribers", 0), reverse=True)
with open(io + "channels.jsonl", "w", encoding="utf-8") as out:
    out.write("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")
print("merged unique channels:", len(rows))
for r in rows:
    print(f"{r.get('subscribers',0):>10,}  {r.get('name','?')}")
