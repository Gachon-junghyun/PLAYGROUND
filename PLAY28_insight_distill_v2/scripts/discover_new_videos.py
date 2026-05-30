"""신규 영상 발견기.

'안 조사한' = R4가 batch input으로 *입력 받은 적도 없는* 영상.
(주의: r4_all_cards.source_videos 에 없다고 "안 본 게" 아니다 —
 R4가 batch input으로는 봤지만 카드 채택 안 한 영상이 있다. 그건 재호출해도 같은 결과.)

  baseline    = list.txt 채널별 video_id set
  r4_inputs   = data/r4_inputs/*.jsonl 의 video_id set (R4가 *실제로* 본 영상)
  r4_source   = r4_all_cards.jsonl source_videos[].video_id set (카드 채택된 영상)
  fresh       = channel_fetch로 채널 최신 N개 영상

  reason 부여:
    - new_after_baseline    : fetch 결과의 *마지막 baseline 영상 인덱스 이내*에서 미등록 (= baseline 작성 후 새로 올라온 진짜 신규)
                              인덱스 그 이후 미등록은 baseline 작성 시점에 limit cap에 잘린 옛 영상 — 발굴 안 함
    - r4_unseen             : baseline 에 있는데 r4_inputs 에 없음 (R4가 batch input에도 안 넣었음)
    - r4_seen_not_carded    : r4_inputs 에 있는데 r4_source 에 없음 (R4가 봤지만 카드 채택 안 함, default 제외)

출력: data/missing_videos.jsonl (jsonl, 1줄=1영상)

사용:
  python scripts/discover_new_videos.py --limit 30
  python scripts/discover_new_videos.py --no-fetch              # 외부 호출 없음
  python scripts/discover_new_videos.py --channels 머니코믹스   # 특정 채널만
  python scripts/discover_new_videos.py --include-seen          # r4_seen_not_carded도 포함
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))  # _channel_fetch.py 같은 디렉토리

DEFAULT_BASELINE = Path(r"C:\Users\fivep\OneDrive\Desktop\HAN_LAB\experiments\youtube_whisper\list.txt")
DEFAULT_TRANSCRIPTS = Path(r"C:\Users\fivep\OneDrive\Desktop\HAN_LAB\experiments\youtube_whisper\transcripts")
DEFAULT_R4_CARDS = ROOT / "data" / "r4_all_cards.jsonl"
DEFAULT_R4_INPUTS = ROOT / "data" / "r4_inputs"
DEFAULT_OUT = ROOT / "data" / "missing_videos.jsonl"
DEFAULT_CHANNEL_IDS = ROOT / "data" / "channel_ids.json"

VID_RE = re.compile(r"watch\?v=([A-Za-z0-9_-]{11})")
CHAN_HEADER_RE = re.compile(r"#\s*===\s*(.+?)\s*\(\d+개\)\s*===")
FNAME_VID_RE = re.compile(r"\[([A-Za-z0-9_-]{11})\]\.txt$")


def parse_list_txt(path: Path) -> dict[str, set[str]]:
    """list.txt → {채널명: {video_id, ...}}."""
    out: dict[str, set[str]] = {}
    cur: str | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        m = CHAN_HEADER_RE.match(line)
        if m:
            cur = m.group(1).strip()
            out[cur] = set()
            continue
        if cur is None:
            continue
        m2 = VID_RE.search(line)
        if m2:
            out[cur].add(m2.group(1))
    return out


def parse_r4_videos(path: Path) -> set[str]:
    """r4_all_cards.jsonl → 카드에 채택된 video_id set."""
    out: set[str] = set()
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        card = json.loads(line)
        for sv in card.get("source_videos", []) or []:
            vid = sv.get("video_id")
            if vid:
                out.add(vid)
    return out


def parse_r4_inputs(dir_: Path) -> set[str]:
    """r4_inputs/*.jsonl → R4 batch input으로 들어간 video_id set (= R4가 실제로 본 영상)."""
    out: set[str] = set()
    if not dir_.exists():
        return out
    for p in dir_.glob("*.jsonl"):
        for line in p.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            d = json.loads(line)
            vid = d.get("video_id")
            if vid:
                out.add(vid)
    return out


def list_transcripts(dir_: Path) -> set[str]:
    """transcripts/*.txt 파일명에서 video_id 추출."""
    if not dir_.exists():
        return set()
    out = set()
    for p in dir_.glob("*.txt"):
        m = FNAME_VID_RE.search(p.name)
        if m:
            out.add(m.group(1))
    return out


def extract_vid(url: str) -> str | None:
    m = VID_RE.search(url)
    return m.group(1) if m else None


def main() -> None:
    ap = argparse.ArgumentParser(description="신규 영상 발견 + R4 안 본 영상 추출")
    ap.add_argument("--limit", type=int, default=30, help="채널당 fetch 영상 수 (기본 30)")
    ap.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    ap.add_argument("--r4-cards", type=Path, default=DEFAULT_R4_CARDS)
    ap.add_argument("--r4-inputs", type=Path, default=DEFAULT_R4_INPUTS,
                    help="R4 batch input jsonl 디렉토리 (R4가 실제로 본 영상)")
    ap.add_argument("--transcripts-dir", type=Path, default=DEFAULT_TRANSCRIPTS)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--channels", type=str, default="", help="콤마 구분 채널 subset")
    ap.add_argument("--no-fetch", action="store_true", help="외부 fetch 생략")
    ap.add_argument("--include-seen", action="store_true",
                    help="R4가 봤지만 카드 채택 안 한 영상(r4_seen_not_carded)도 포함")
    ap.add_argument("--dry-run", action="store_true", help="파일 안 쓰고 stats만")
    args = ap.parse_args()

    baseline = parse_list_txt(args.baseline)
    r4_source = parse_r4_videos(args.r4_cards)
    r4_inputs_set = parse_r4_inputs(args.r4_inputs)
    transcripts = list_transcripts(args.transcripts_dir)
    channel_ids: dict[str, str] = {}
    if DEFAULT_CHANNEL_IDS.exists():
        raw = json.loads(DEFAULT_CHANNEL_IDS.read_text(encoding="utf-8"))
        channel_ids = {k: v for k, v in raw.items() if not k.startswith("_")}

    channel_filter = {c.strip() for c in args.channels.split(",") if c.strip()}
    today = date.today().isoformat()
    rows: list[dict] = []

    # D: baseline 이후 새로 올라온 영상만 추출
    # 로직: fetch는 최신순 정렬 → 마지막 baseline 영상의 인덱스까지 스캔 →
    #       그 안의 미등록 영상 = baseline 작성 이후 추가된 진짜 신규
    #       (인덱스 그 이후 미등록 영상은 baseline 작성 시점에 limit cap에 잘린 옛 영상)
    if not args.no_fetch:
        from _channel_fetch import fetch_latest_videos
        for channel, baseline_set in baseline.items():
            if channel_filter and channel not in channel_filter:
                continue
            cid = channel_ids.get(channel)
            target = f"https://www.youtube.com/channel/{cid}" if cid else channel
            try:
                urls = fetch_latest_videos(target, args.limit)
            except Exception as e:
                print(f"[fail] {channel}: {e}", file=sys.stderr)
                continue
            fetch_vids: list[tuple[str, str]] = []
            last_bl_idx = -1
            for url in urls:
                vid = extract_vid(url)
                if not vid:
                    continue
                fetch_vids.append((vid, url))
                if vid in baseline_set:
                    last_bl_idx = len(fetch_vids) - 1
            if last_bl_idx < 0:
                print(f"[warn] {channel}: fetch {len(fetch_vids)}건 중 baseline 영상 0건 — limit 너무 작거나 채널 변경. 스킵.", file=sys.stderr)
                continue
            for vid, url in fetch_vids[:last_bl_idx + 1]:
                if vid in baseline_set:
                    continue
                rows.append({
                    "video_id": vid, "channel": channel, "url": url,
                    "reason": "new_after_baseline",
                    "has_transcript": vid in transcripts,
                    "detected_at": today,
                })

    # B: list.txt 등록 but R4 input에도 안 들어감 (= R4가 정말 안 본 영상)
    for channel, baseline_set in baseline.items():
        if channel_filter and channel not in channel_filter:
            continue
        for vid in sorted(baseline_set - r4_inputs_set):
            rows.append({
                "video_id": vid, "channel": channel,
                "url": f"https://www.youtube.com/watch?v={vid}",
                "reason": "r4_unseen",
                "has_transcript": vid in transcripts,
                "detected_at": today,
            })

    # 선택: R4가 input으로는 봤지만 카드 채택 안 한 영상 (재호출 비추천)
    if args.include_seen:
        for channel, baseline_set in baseline.items():
            if channel_filter and channel not in channel_filter:
                continue
            seen_not_carded = (baseline_set & r4_inputs_set) - r4_source
            for vid in sorted(seen_not_carded):
                rows.append({
                    "video_id": vid, "channel": channel,
                    "url": f"https://www.youtube.com/watch?v={vid}",
                    "reason": "r4_seen_not_carded",
                    "has_transcript": vid in transcripts,
                    "detected_at": today,
                })

    rows.sort(key=lambda r: (r["channel"], r["reason"], r["video_id"]))

    if not args.dry_run:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    by_reason: dict[str, int] = {}
    by_channel: dict[str, int] = {}
    no_txt = 0
    for r in rows:
        by_reason[r["reason"]] = by_reason.get(r["reason"], 0) + 1
        by_channel[r["channel"]] = by_channel.get(r["channel"], 0) + 1
        if not r["has_transcript"]:
            no_txt += 1

    print(f"[OK] 총 {len(rows)}건")
    for k in ("new_after_baseline", "r4_unseen", "r4_seen_not_carded"):
        print(f"  - reason {k}: {by_reason.get(k, 0)}")
    print(f"  - 자막 미존재:           {no_txt}")
    print(f"  - (참고) R4 input 본 영상: {len(r4_inputs_set)}, 카드 채택: {len(r4_source)}")
    for ch, n in sorted(by_channel.items(), key=lambda x: -x[1]):
        print(f"  · {ch}: {n}")
    if not args.dry_run:
        print(f"[OK] 출력 → {args.out}")


if __name__ == "__main__":
    main()
