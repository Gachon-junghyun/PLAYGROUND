"""R0 Agent 입력 준비 — 자막 파일을 5개 batch jsonl로 분류.

5 Agent 병렬 호출용:
  - r0_inputs/A1_moneygraphy_p1.jsonl (머니그라피 1차, 영상 0~7)
  - r0_inputs/A2_moneygraphy_p2.jsonl (머니그라피 2차, 영상 8~15)
  - r0_inputs/A3_moneycomics.jsonl    (머니코믹스 16개)
  - r0_inputs/A4_kimdante_oseon.jsonl (김단테 14 + 오선 10)
  - r0_inputs/A5_jisikbu.jsonl        (지식부장관 16)
"""
from __future__ import annotations
import json, os, re
from pathlib import Path

ROOT = Path(__file__).parent.parent
TRANSCRIPT_DIR = Path(r"C:\Users\fivep\OneDrive\Desktop\HAN_LAB\experiments\youtube_whisper\transcripts")
LIST_TXT = Path(r"C:\Users\fivep\OneDrive\Desktop\HAN_LAB\experiments\youtube_whisper\list.txt")
OUT_DIR = ROOT / "data" / "r0_inputs"

CH_HEADER_RE = re.compile(r"^#\s*===\s*(.+?)\s*\(\d+개\)\s*===")
VID_RE = re.compile(r"v=([a-zA-Z0-9_-]{11})")
FILE_VID_RE = re.compile(r"\[([a-zA-Z0-9_-]{11})\]\.txt$")


def build_channel_map() -> dict[str, str]:
    """video_id → 채널명"""
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

    # transcripts/*.txt 스캔
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

    # 채널별 정렬 (size 큰 순)
    for ch in videos_by_ch:
        videos_by_ch[ch].sort(key=lambda v: -v["size_bytes"])

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # 분할 정책 — A1(153K 토큰) 컨텍스트 부담으로 머니그라피 4+4+8 분할
    splits = [
        ("A1_moneygraphy_top4",  videos_by_ch.get("머니그라피", [])[:4]),
        ("A2_moneygraphy_mid4",  videos_by_ch.get("머니그라피", [])[4:8]),
        ("A3_moneygraphy_small8",videos_by_ch.get("머니그라피", [])[8:]),
        ("A4_moneycomics",       videos_by_ch.get("머니코믹스", [])),
        ("A5_kimdante_oseon",    videos_by_ch.get("김단테 월가아재", []) + videos_by_ch.get("오선의 미국 증시 라이프", [])),
        ("A6_jisikbu",           videos_by_ch.get("지식부장관", [])),
    ]

    print(f"{'BATCH':<25} {'영상':>5} {'총 KB':>8} {'추정 토큰':>10}")
    for name, vids in splits:
        fp = OUT_DIR / f"{name}.jsonl"
        with fp.open("w", encoding="utf-8") as f:
            for v in vids:
                f.write(json.dumps(v, ensure_ascii=False) + "\n")
        total_b = sum(v["size_bytes"] for v in vids)
        print(f"{name:<25} {len(vids):>5} {total_b/1024:>8.1f} {total_b//4:>10,}")


if __name__ == "__main__":
    main()
