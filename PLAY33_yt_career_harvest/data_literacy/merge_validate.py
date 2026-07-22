import json, pathlib, sys, collections
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = pathlib.Path(__file__).resolve().parent
CARDS = HERE / "cards"
batches = ["B1.jsonl", "B2.jsonl", "B3.jsonl", "B4.jsonl"]

rows, problems = [], []
for b in batches:
    p = CARDS / b
    for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            d = json.loads(line)
        except Exception as e:
            problems.append(f"{b}:{i} JSON parse fail: {e}")
            continue
        rows.append(d)

ids = [d.get("card_id") for d in rows]
dups = [k for k, v in collections.Counter(ids).items() if v > 1]
no_ev = [d["card_id"] for d in rows if not (d.get("evidence_quote") or "").strip()]
bad_axis = [d["card_id"] for d in rows
            if d.get("axis") not in {"decode_vocab","sentence_parse","context_inference",
                                     "macro_structure","active_strategy","habit_transfer"}]

axis_dist = collections.Counter(d.get("axis") for d in rows)
chan_dist = collections.Counter(d.get("source_video",{}).get("channel","?") for d in rows)
conf_dist = collections.Counter((d.get("confidence","") or "").split("—")[0].split("-")[0].strip().lower()[:4] for d in rows)

out = CARDS / "_all.jsonl"
with out.open("w", encoding="utf-8") as f:
    for d in rows:
        f.write(json.dumps(d, ensure_ascii=False) + "\n")

print(f"=== MERGE/VALIDATE ===  total cards = {len(rows)}  -> cards/_all.jsonl")
print(f"dup card_id: {dups or 'NONE'}")
print(f"empty evidence: {no_ev or 'NONE'}")
print(f"bad axis: {bad_axis or 'NONE'}")
print(f"parse problems: {problems or 'NONE'}")
print("\n-- axis 분포 --")
for k, v in axis_dist.most_common():
    print(f"  {v:>3}  {k}")
print("\n-- channel 분포 --")
for k, v in chan_dist.most_common():
    print(f"  {v:>3}  {k}")
print("\n-- confidence(앞4글자) 분포 --")
for k, v in conf_dist.most_common():
    print(f"  {v:>3}  {k}")
