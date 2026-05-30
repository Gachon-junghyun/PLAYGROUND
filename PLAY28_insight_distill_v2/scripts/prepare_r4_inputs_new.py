"""R4 신규 batch 분할 (PLAY28 v2 incremental 라운드).

missing_videos.jsonl 28건 video_id를 transcripts/와 매치해
채널별 4 batch jsonl로 분할.

  A7  지식부장관 9   → E067~E076  (7~10장)
  A8  오선 8         → E077~E084  (4~8장)
  A9  머니코믹스 7   → E085~E091  (5~7장)
  A10 김단테 4       → E092~E099  (5~8장)

출력: data/r4_inputs_new/<batch>.jsonl
입력 스키마: {video_id, channel, file_path, title_hint, size_bytes}
"""
from __future__ import annotations
import json, re
from pathlib import Path

ROOT = Path(__file__).parent.parent
TRANSCRIPT_DIR = Path(r"C:\Users\fivep\OneDrive\Desktop\HAN_LAB\experiments\youtube_whisper\transcripts")
MISSING_JSONL = ROOT / "data" / "missing_videos.jsonl"
OUT_DIR = ROOT / "data" / "r4_inputs_new"

FILE_VID_RE = re.compile(r"\[([a-zA-Z0-9_-]{11})\]\.txt$")

ID_RANGES = {
    "A7_jisikbu_new":     ("E067", "E076", "7~10"),
    "A8_oseon_new":       ("E077", "E084", "4~8"),
    "A9_moneycomics_new": ("E085", "E091", "5~7"),
    "A10_kimdante_new":   ("E092", "E099", "5~8"),
}

CHANNEL_TO_BATCH = {
    "지식부장관":              "A7_jisikbu_new",
    "오선의 미국 증시 라이프":  "A8_oseon_new",
    "머니코믹스":              "A9_moneycomics_new",
    "김단테 월가아재":         "A10_kimdante_new",
}


def main() -> None:
    rows = [json.loads(l) for l in MISSING_JSONL.read_text(encoding="utf-8").splitlines() if l.strip()]
    target_vids = {r["video_id"]: r["channel"] for r in rows}

    transcripts: dict[str, Path] = {}
    for fp in TRANSCRIPT_DIR.glob("*.txt"):
        m = FILE_VID_RE.search(fp.name)
        if m and m.group(1) in target_vids:
            transcripts[m.group(1)] = fp

    missing_tx = sorted(set(target_vids) - set(transcripts))
    if missing_tx:
        print(f"[warn] 자막 없는 video_id {len(missing_tx)}건 (다운로드 미완료?):")
        for v in missing_tx[:20]:
            print(f"  {v}  ({target_vids[v]})")

    batches: dict[str, list[dict]] = {b: [] for b in ID_RANGES}
    for vid, fp in transcripts.items():
        ch = target_vids[vid]
        b = CHANNEL_TO_BATCH.get(ch)
        if not b:
            print(f"[skip] 미지정 채널: {ch} / {vid}")
            continue
        batches[b].append({
            "video_id": vid,
            "channel": ch,
            "file_path": str(fp),
            "title_hint": fp.name.rsplit("[", 1)[0].strip(),
            "size_bytes": fp.stat().st_size,
        })

    for b in batches:
        batches[b].sort(key=lambda v: -v["size_bytes"])

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n{'BATCH':<22} {'영상':>4} {'KB':>7} {'~tok':>8}  {'ID':<14} {'카드':<6}")
    print("-" * 72)
    grand_b = 0
    grand_v = 0
    for name, vids in batches.items():
        fp = OUT_DIR / f"{name}.jsonl"
        with fp.open("w", encoding="utf-8") as f:
            for v in vids:
                f.write(json.dumps(v, ensure_ascii=False) + "\n")
        total_b = sum(v["size_bytes"] for v in vids)
        grand_b += total_b
        grand_v += len(vids)
        s, e, hint = ID_RANGES[name]
        print(f"{name:<22} {len(vids):>4} {total_b/1024:>7.1f} {total_b//4:>8,}  {s}~{e:<8} {hint}")
    print("-" * 72)
    print(f"{'TOTAL':<22} {grand_v:>4} {grand_b/1024:>7.1f} {grand_b//4:>8,}  E067~E099    ~21~33")


if __name__ == "__main__":
    main()
