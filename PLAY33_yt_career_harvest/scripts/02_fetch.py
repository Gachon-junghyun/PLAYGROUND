# PLAY33_yt_career_harvest/scripts/02_fetch.py
"""채널 → 최신 N개 영상 → 신규만 골라 data/queue.jsonl.

입력은 둘 중 하나:
    --from-channels data/channels.jsonl   (01_discover 산출물)
    --channel "@핸들 또는 채널이름"        (단일 채널 직접)

제목 필터(--match): 채널의 최신 N편을 *스캔*한 뒤 제목에 키워드가 든 영상만 남긴다.
대형 종합 채널이 온토픽 비율이 낮은 문제를 줄이는 용도. --keep 으로 채널당 상한.

사용:
    python scripts/02_fetch.py --from-channels data/channels.jsonl -n 8
    python scripts/02_fetch.py --channel "노마드 코더" -n 10
    python scripts/02_fetch.py --from-channels data/channels.jsonl -n 8 --all   # 캐시 무시
    # 제목 필터: 최신 40편 스캔 → 토론 키워드 매칭만, 채널당 최대 8편
    python scripts/02_fetch.py --from-channels data/channels.jsonl -n 40 \
        --match "토론,말싸움,논쟁,논증,반박,설득,디베이트,말빨,언변" --keep 8
"""
from __future__ import annotations

import argparse
from pathlib import Path

from _common import DATA_DIR, fetch_latest, filter_new, read_jsonl, write_jsonl


def main() -> None:
    p = argparse.ArgumentParser(description="채널 → 신규 영상 큐 생성")
    p.add_argument("--from-channels", default=None, help="01_discover 산출 channels.jsonl 경로")
    p.add_argument("--channel", default=None, help="단일 채널 핸들/이름/URL")
    p.add_argument("-n", "--limit", type=int, default=8,
                   help="채널당 스캔할 최신 영상 수 (기본 8; --match 쓰면 넉넉히 30~40 권장)")
    p.add_argument("--match", default=None,
                   help="제목 키워드 필터 (콤마 구분). 지정 시 제목에 하나라도 포함된 영상만.")
    p.add_argument("--keep", type=int, default=None,
                   help="채널당 매칭 영상 최대 보관 수 (기본 무제한)")
    p.add_argument("--all", action="store_true", help="seen 캐시 무시하고 전부 포함")
    p.add_argument("--out", default=str(DATA_DIR / "queue.jsonl"),
                   help="출력 큐 jsonl (기본 data/queue.jsonl)")
    args = p.parse_args()

    if bool(args.from_channels) == bool(args.channel):
        p.error("--from-channels 또는 --channel 중 정확히 하나만 지정")

    if args.channel:
        channels = [{"name": args.channel, "url": args.channel}]
    else:
        channels = read_jsonl(Path(args.from_channels))
        if not channels:
            p.error(f"채널 목록이 비어있음: {args.from_channels}")

    keywords = [k.strip().lower() for k in args.match.split(",")] if args.match else []
    keywords = [k for k in keywords if k]

    def title_ok(title: str) -> bool:
        return not keywords or any(k in title.lower() for k in keywords)

    videos: list[dict] = []
    for c in channels:
        latest = fetch_latest(c["url"], args.limit)
        matched = [v for v in latest if title_ok(v.get("title", ""))]
        if args.keep:
            matched = matched[:args.keep]
        for v in matched:
            videos.append({**v, "channel": c.get("name", "?")})
        tail = f" → {len(matched)}개 매칭" if keywords else ""
        print(f"[..] {c.get('name','?')}: {len(latest)}개 스캔{tail}")

    fresh = videos if args.all else filter_new(videos)
    skipped = len(videos) - len(fresh)
    write_jsonl(Path(args.out), fresh)
    print(f"[OK] 총 {len(videos)}개 중 신규 {len(fresh)}개 (캐시로 {skipped}개 스킵) → {args.out}")


if __name__ == "__main__":
    main()
