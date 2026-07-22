import json, pathlib, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = pathlib.Path(__file__).resolve().parent
files = ["ch_a.jsonl", "ch_b.jsonl", "ch_c.jsonl"]
rows = {}
for f in files:
    for line in (HERE / f).read_text(encoding="utf-8").splitlines():
        if line.strip():
            d = json.loads(line)
            rows[d["channel_id"]] = d

# 노이즈 차단(엔터/뉴스/유아영어/육아/원예/스피치 등 비-문해력)
block = {
    "MBCentertainment", "JTBC Entertainment", "tvN D ENT", "play 채널A", "KBS News",
    "EBSDocumentary (EBS 다큐)", "EBSCulture (EBS 교양)", "가든패밀리 (Garden Family) ",
    "현서 아빠표 영어", "흔한엄마*", "캐내네 스피치",
}
kept = [d for d in rows.values() if d["name"] not in block]
kept.sort(key=lambda d: d.get("subscribers", 0), reverse=True)

out = HERE / "channels.jsonl"
with out.open("w", encoding="utf-8") as fp:
    for d in kept:
        fp.write(json.dumps(d, ensure_ascii=False) + "\n")

print(f"merged unique={len(rows)}  kept(after block)={len(kept)}  -> {out.name}")
for d in kept:
    print(f"  {d.get('subscribers',0):>10,}  {d['name']}")
