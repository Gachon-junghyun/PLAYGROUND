"""R4 Agent 입력 준비 — 자막 .txt를 9개 batch jsonl로 분할.

9 Agent 병렬용. 채널/화자 경계 존중. 카드 ID 영역 E001~E066 사전 할당.

  A1 머니그라피 top4    → E001~E006 (4~6장)
  A2 머니그라피 mid4    → E007~E012 (4~6장)
  A3 머니그라피 small8  → E013~E020 (6~8장, 잡담 토크쇼 비중↑)
  A4a 머니코믹스 top8   → E021~E026 (5~6장)
  A4b 머니코믹스 bot8   → E027~E032 (5~6장)
  A5a 김단테 14         → E033~E044 (10~12장)
  A5b 오선 16           → E045~E050 (4~6장)
  A6a 지식부장관 top8   → E051~E058 (6~8장)
  A6b 지식부장관 bot8   → E059~E066 (4~6장)
"""
from __future__ import annotations
import json, re
from pathlib import Path

ROOT = Path(__file__).parent.parent
TRANSCRIPT_DIR = Path(r"C:\Users\fivep\OneDrive\Desktop\HAN_LAB\experiments\youtube_whisper\transcripts")
LIST_TXT = Path(r"C:\Users\fivep\OneDrive\Desktop\HAN_LAB\experiments\youtube_whisper\list.txt")
OUT_DIR = ROOT / "data" / "r4_inputs"

CH_HEADER_RE = re.compile(r"^#\s*===\s*(.+?)\s*\(\d+개\)\s*===")
VID_RE = re.compile(r"v=([a-zA-Z0-9_-]{11})")
FILE_VID_RE = re.compile(r"\[([a-zA-Z0-9_-]{11})\]\.txt$")

ID_RANGES = {
    "A1_moneygraphy_top4":   ("E001", "E006",  "4~6"),
    "A2_moneygraphy_mid4":   ("E007", "E012",  "4~6"),
    "A3_moneygraphy_small8": ("E013", "E020",  "6~8"),
    "A4a_moneycomics_top8":  ("E021", "E026",  "5~6"),
    "A4b_moneycomics_bot8":  ("E027", "E032",  "5~6"),
    "A5a_kimdante":          ("E033", "E044",  "10~12"),
    "A5b_oseon":             ("E045", "E050",  "4~6"),
    "A6a_jisikbu_top8":      ("E051", "E058",  "6~8"),
    "A6b_jisikbu_bot8":      ("E059", "E066",  "4~6"),
}


def build_channel_map() -> dict[str, str]:
    mp: dict[str, str] = {}
    current = "?"
    for line in LIST_TXT.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        m = CH_HEADER_RE.match(line)
        if m:
            current = m.group(1).strip()
            continue
        vm = VID_RE.search(line)
        if vm:
            mp[vm.group(1)] = current
    return mp


def main() -> None:
    ch_map = build_channel_map()

    videos_by_ch: dict[str, list[dict]] = {}
    for fp in sorted(TRANSCRIPT_DIR.glob("*.txt")):
        m = FILE_VID_RE.search(fp.name)
        if not m:
            continue
        vid = m.group(1)
        ch = ch_map.get(vid, "?")
        videos_by_ch.setdefault(ch, []).append({
            "video_id": vid,
            "channel": ch,
            "file_path": str(fp),
            "title_hint": fp.name.rsplit("[", 1)[0].strip(),
            "size_bytes": fp.stat().st_size,
        })

    for ch in videos_by_ch:
        videos_by_ch[ch].sort(key=lambda v: -v["size_bytes"])

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    mg  = videos_by_ch.get("머니그라피", [])
    mc  = videos_by_ch.get("머니코믹스", [])
    kd  = videos_by_ch.get("김단테 월가아재", [])
    os_ = videos_by_ch.get("오선의 미국 증시 라이프", [])
    js  = videos_by_ch.get("지식부장관", [])

    splits = [
        ("A1_moneygraphy_top4",   mg[:4]),
        ("A2_moneygraphy_mid4",   mg[4:8]),
        ("A3_moneygraphy_small8", mg[8:]),
        ("A4a_moneycomics_top8",  mc[:8]),
        ("A4b_moneycomics_bot8",  mc[8:]),
        ("A5a_kimdante",          kd),
        ("A5b_oseon",             os_),
        ("A6a_jisikbu_top8",      js[:8]),
        ("A6b_jisikbu_bot8",      js[8:]),
    ]

    print(f"{'BATCH':<27} {'영상':>4} {'KB':>7} {'~tok':>8}  {'ID':<14} {'카드':<6}")
    print("-" * 78)
    grand_b = 0
    grand_v = 0
    for name, vids in splits:
        fp = OUT_DIR / f"{name}.jsonl"
        with fp.open("w", encoding="utf-8") as f:
            for v in vids:
                f.write(json.dumps(v, ensure_ascii=False) + "\n")
        total_b = sum(v["size_bytes"] for v in vids)
        grand_b += total_b
        grand_v += len(vids)
        s, e, hint = ID_RANGES[name]
        print(f"{name:<27} {len(vids):>4} {total_b/1024:>7.1f} {total_b//4:>8,}  {s}~{e:<8} {hint}")
    print("-" * 78)
    print(f"{'TOTAL':<27} {grand_v:>4} {grand_b/1024:>7.1f} {grand_b//4:>8,}  E001~E066    ~50~70")


if __name__ == "__main__":
    main()
