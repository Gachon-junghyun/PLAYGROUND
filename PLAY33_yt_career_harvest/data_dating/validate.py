import json, glob
from collections import Counter
cards = []
for f in sorted(glob.glob("data_dating/cards/*.jsonl")):
    for ln, l in enumerate(open(f, encoding="utf-8"), 1):
        if l.strip():
            try:
                cards.append(json.loads(l))
            except Exception as e:
                print(f"PARSE ERROR {f}:{ln} -> {e}")
ids = [c["card_id"] for c in cards]
dups = [k for k, v in Counter(ids).items() if v > 1]
no_ev = [c["card_id"] for c in cards if not c.get("evidence_quote", "").strip()]
print("TOTAL CARDS:", len(cards))
print("DUP IDS:", dups or "none")
print("MISSING EVIDENCE:", no_ev or "none")
print("\n-- axis --")
for k, v in Counter(c["axis"] for c in cards).most_common():
    print(f"  {v:>3}  {k}")
print("-- stance --")
for k, v in Counter(c.get("stance", "?") for c in cards).most_common():
    print(f"  {v:>3}  {k}")
print("-- who --")
for k, v in Counter(c.get("who", "?") for c in cards).most_common():
    print(f"  {v:>3}  {k}")
print("-- channel --")
for k, v in Counter(c["source_video"]["channel"] for c in cards).most_common():
    print(f"  {v:>3}  {k}")
print("-- confidence --")
for k, v in Counter(c.get("confidence","?").split("—")[0].split("-")[0].strip() for c in cards).most_common():
    print(f"  {v:>3}  {k}")
# save merged
with open("data_dating/cards_all.jsonl", "w", encoding="utf-8") as out:
    for c in cards:
        out.write(json.dumps(c, ensure_ascii=False) + "\n")
print("\nmerged -> data_dating/cards_all.jsonl")
