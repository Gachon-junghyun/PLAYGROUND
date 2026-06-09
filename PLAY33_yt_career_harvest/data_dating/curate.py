import json
rows = [json.loads(l) for l in open("data_dating/queue_all.jsonl", encoding="utf-8") if l.strip()]
keep = [7, 9, 32, 43, 47, 62, 70, 71, 82, 86, 90, 104, 108, 111, 114, 116, 121, 29]
sel = [rows[i] for i in keep]
with open("data_dating/queue.jsonl", "w", encoding="utf-8") as out:
    out.write("\n".join(json.dumps(r, ensure_ascii=False) for r in sel) + "\n")
for r in sel:
    print(f"  {r['channel']:<14} | {r['title'][:48]}")
print("CURATED:", len(sel))
