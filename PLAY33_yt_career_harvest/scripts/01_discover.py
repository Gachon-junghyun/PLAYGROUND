# PLAY33_yt_career_harvest/scripts/01_discover.py
"""키워드 → 구독자 12만+ 채널 발견 → data/channels.jsonl.

사용:
    python scripts/01_discover.py "카카오 네이버 삼성전자 개발자 취업"
    python scripts/01_discover.py "백엔드 개발자 취업" --min-subs 100000 --search 60
"""
from __future__ import annotations

import argparse

from _common import DATA_DIR, search_channels, write_jsonl


def main() -> None:
    p = argparse.ArgumentParser(description="키워드 → 채널 발견 (구독자 필터)")
    p.add_argument("keyword", help="검색 키워드 (예: '카카오 개발자 취업')")
    p.add_argument("--min-subs", type=int, default=120_000, help="최소 구독자 수 (기본 12만)")
    p.add_argument("--search", type=int, default=50, help="긁을 검색 영상 수 (기본 50)")
    p.add_argument("--out", default=str(DATA_DIR / "channels.jsonl"),
                   help="출력 jsonl 경로 (기본 data/channels.jsonl)")
    args = p.parse_args()

    chans = search_channels(args.keyword, args.min_subs, args.search)
    if not chans:
        print(f"[!] 조건을 만족하는 채널 없음: {args.keyword}")
        return

    from pathlib import Path
    write_jsonl(Path(args.out), chans)
    print(f"[OK] {len(chans)}개 채널 (구독자 {args.min_subs:,}+) → {args.out}")
    for c in chans:
        print(f"  {c['subscribers']:>10,}  {c['name']}  |  {c['url']}")


if __name__ == "__main__":
    main()
