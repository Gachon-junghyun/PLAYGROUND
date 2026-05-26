"""R3-A: 11개 카드 jsonl 통합 + 검수 + 메타 통계 + md 요약."""
from __future__ import annotations
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
CARD_DIRS = [DATA / "r2a_cards", DATA / "r2b_cards", DATA / "r2c_cards", DATA / "r2d_cards", DATA / "r0_cards"]

OUT_JSONL = DATA / "r2_all_cards.jsonl"
OUT_MD = DATA / "r2_all_cards.md"
OUT_STATS = DATA / "r2_all_stats.md"

REQUIRED_FIELDS = [
    "card_id", "label_origin", "title", "trigger_conditions",
    "speakers_view", "causal_chain", "expected_direction",
    "time_horizon", "confidence_meta", "search_blurb",
]
# source는 R2 카드(source_propositions) 또는 R0 카드(source_videos) 둘 중 하나


def load_all() -> list[dict]:
    cards: list[dict] = []
    for d in CARD_DIRS:
        if not d.exists():
            continue
        for fp in sorted(d.glob("*.jsonl")):
            for line in fp.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                c = json.loads(line)
                c["_source_file"] = f"{d.name}/{fp.name}"
                cards.append(c)
    return cards


def audit(cards: list[dict]) -> list[str]:
    """검수 — 문제 발견 시 리포트."""
    issues: list[str] = []
    ids = Counter(c.get("card_id") for c in cards)
    for cid, n in ids.items():
        if n > 1:
            issues.append(f"DUP card_id: {cid} ({n}회)")
    for c in cards:
        cid = c.get("card_id", "?")
        for f in REQUIRED_FIELDS:
            if f not in c:
                issues.append(f"{cid}: missing field '{f}'")
            elif isinstance(c[f], (list, dict, str)) and not c[f]:
                issues.append(f"{cid}: empty field '{f}'")
        # source: 둘 중 하나 필수
        if "source_propositions" not in c and "source_videos" not in c:
            issues.append(f"{cid}: missing source (neither source_propositions nor source_videos)")
    return issues


def stats(cards: list[dict]) -> dict:
    """카드 메타 통계."""
    s: dict = {}
    s["total"] = len(cards)

    # 화자 분포 (각 카드의 speakers_view에 등장한 화자 수)
    speaker_count = Counter()
    sole_speaker = Counter()
    n_speakers_dist = Counter()
    for c in cards:
        sv = c.get("speakers_view", {}) or {}
        n = len(sv)
        n_speakers_dist[n] += 1
        if n == 1:
            sole_speaker[list(sv.keys())[0]] += 1
        for sp in sv:
            speaker_count[sp] += 1
    s["speaker_appearance"] = speaker_count
    s["sole_speaker_cards"] = sole_speaker
    s["n_speakers_dist"] = n_speakers_dist

    # direction, time_horizon, confidence (자유 표기라 첫 단어로 grouping)
    def first_word(s: str) -> str:
        return (s or "").split()[0].rstrip(",—-") if s else "?"

    s["direction"] = Counter(first_word(c.get("expected_direction", "")) for c in cards)
    s["time_horizon"] = Counter(c.get("time_horizon", "?") or "?" for c in cards)
    s["confidence_first"] = Counter(first_word(c.get("confidence_meta", "")) for c in cards)

    # 라벨 분포 (label_origin)
    lab = Counter()
    for c in cards:
        for l in c.get("label_origin", []):
            lab[l] += 1
    s["label_origin"] = lab

    # source_propositions 중복 (R2 카드만)
    prop_to_cards: dict[str, list[str]] = defaultdict(list)
    for c in cards:
        for pid in c.get("source_propositions", []):
            prop_to_cards[pid].append(c.get("card_id", "?"))
    dup_props = {pid: cids for pid, cids in prop_to_cards.items() if len(cids) > 1}
    s["dup_props_count"] = len(dup_props)
    s["dup_props_examples"] = list(dup_props.items())[:10]

    # source_videos 중복 (R0 카드만)
    vid_to_cards: dict[str, list[str]] = defaultdict(list)
    for c in cards:
        for sv in c.get("source_videos", []):
            vid = sv.get("video_id", "?") if isinstance(sv, dict) else "?"
            vid_to_cards[vid].append(c.get("card_id", "?"))
    dup_vids = {vid: cids for vid, cids in vid_to_cards.items() if len(cids) > 1}
    s["dup_videos_count"] = len(dup_vids)

    # source 수 분포 (카드별, 둘 중 있는 쪽)
    src_n = Counter()
    for c in cards:
        n = len(c.get("source_propositions", [])) + len(c.get("source_videos", []))
        src_n[n] += 1
    s["source_n_dist"] = src_n

    # source_type 분포 (R0 vs R2)
    src_type = Counter()
    for c in cards:
        if "source_videos" in c:
            src_type["R0_transcript"] += 1
        elif "source_propositions" in c:
            src_type["R2_proposition"] += 1
        else:
            src_type["unknown"] += 1
    s["source_type"] = src_type

    return s


def write_md_summary(cards: list[dict]) -> None:
    """사람용 한눈 요약 — 카드 43장 1줄씩."""
    lines = ["# R2 카드 통합 요약 (43장)\n"]
    lines.append("> 각 카드 ID 클릭하면 jsonl에서 본문 확인 가능. RAG 검색 시 search_blurb를 임베딩 키로 사용.\n")

    # 카드 ID 순으로 정렬
    cards_sorted = sorted(cards, key=lambda c: c.get("card_id", ""))

    current_area = None
    for c in cards_sorted:
        cid = c.get("card_id", "?")
        title = c.get("title", "?")
        labels = ", ".join(c.get("label_origin", []))
        sv = c.get("speakers_view", {}) or {}
        speakers = " + ".join(sv.keys()) if sv else "—"
        direction = c.get("expected_direction", "?")
        horizon = c.get("time_horizon", "?")
        n_src = len(c.get("source_propositions", []))
        conf = (c.get("confidence_meta", "") or "")[:40]

        # 영역 헤더 (R2 = C, R0 = D)
        if cid.startswith("C") and cid[1:].isdigit():
            cnum = int(cid[1:])
            area = (
                "## R2 매크로 (C001~C016)" if cnum <= 16 else
                "## R2 산업·섹터 (C017~C028)" if cnum <= 28 else
                "## R2 기업·종목 (C029~C040)" if cnum <= 40 else
                "## R2 일반론·메타 (C041~C047)"
            )
        elif cid.startswith("D") and cid[1:].isdigit():
            dnum = int(cid[1:])
            area = (
                "## R0 머니그라피 (D001~D014)" if dnum <= 14 else
                "## R0 머니코믹스 (D015~D022)" if dnum <= 22 else
                "## R0 김단테+오선 (D023~D032)" if dnum <= 32 else
                "## R0 지식부장관 (D033~D040)"
            )
        else:
            area = "## 기타"
        if area != current_area:
            lines.append(f"\n{area}\n")
            current_area = area

        lines.append(
            f"- **{cid}** {title}  \n"
            f"  · 라벨: `{labels}` · 화자: {speakers} · 방향: {direction} · 시간: {horizon} · src: {n_src}건 · conf: {conf}\n"
        )

    OUT_MD.write_text("".join(lines), encoding="utf-8")


def write_stats_md(s: dict, issues: list[str]) -> None:
    lines = ["# R2 카드 메타 통계\n\n"]
    lines.append(f"**총 카드 수**: {s['total']}\n\n")

    lines.append("## 카드별 등장 화자 수 분포\n")
    for n, cnt in sorted(s["n_speakers_dist"].items()):
        lines.append(f"- 화자 {n}명 카드: {cnt}장\n")

    lines.append("\n## 화자 등장 빈도 (카드 단위)\n")
    for sp, n in s["speaker_appearance"].most_common():
        lines.append(f"- {sp}: {n}회\n")

    lines.append("\n## 단일 화자 카드 (해당 화자가 단독 등장)\n")
    for sp, n in s["sole_speaker_cards"].most_common():
        lines.append(f"- {sp}: {n}장\n")

    lines.append("\n## expected_direction 분포 (첫 단어 기준)\n")
    for d, n in s["direction"].most_common():
        lines.append(f"- {d}: {n}\n")

    lines.append("\n## time_horizon 분포\n")
    for t, n in s["time_horizon"].most_common():
        lines.append(f"- {t}: {n}\n")

    lines.append("\n## confidence (첫 단어 기준)\n")
    for c, n in s["confidence_first"].most_common():
        lines.append(f"- {c}: {n}\n")

    lines.append("\n## label_origin 분포\n")
    for l, n in s["label_origin"].most_common():
        lines.append(f"- {l}: {n}\n")

    lines.append("\n## source_propositions 중복\n")
    lines.append(f"- 여러 카드에 동시 인용된 명제: **{s['dup_props_count']}건**\n")
    if s["dup_props_examples"]:
        lines.append("- 예시 (최대 10건):\n")
        for pid, cids in s["dup_props_examples"]:
            lines.append(f"  - `{pid}` → {', '.join(cids)}\n")

    lines.append("\n## 카드별 source 수 분포\n")
    for n, cnt in sorted(s["source_n_dist"].items()):
        lines.append(f"- {n} src: {cnt}장\n")

    lines.append("\n## 검수 이슈\n")
    if issues:
        for i in issues:
            lines.append(f"- {i}\n")
    else:
        lines.append("- 없음 (모든 필드 채워짐, 카드 ID 충돌 없음)\n")

    OUT_STATS.write_text("".join(lines), encoding="utf-8")


def main() -> None:
    cards = load_all()
    print(f"[R3-A] 카드 로드: {len(cards)}장")

    issues = audit(cards)
    print(f"[R3-A] 검수 이슈: {len(issues)}건")

    # 통합 jsonl (정렬 후)
    cards_sorted = sorted(cards, key=lambda c: c.get("card_id", ""))
    with OUT_JSONL.open("w", encoding="utf-8") as f:
        for c in cards_sorted:
            out = {k: v for k, v in c.items() if not k.startswith("_")}
            f.write(json.dumps(out, ensure_ascii=False) + "\n")
    print(f"[R3-A] 통합 jsonl: {OUT_JSONL.name} ({OUT_JSONL.stat().st_size:,} chars)")

    s = stats(cards)
    write_md_summary(cards)
    write_stats_md(s, issues)
    print(f"[R3-A] 요약 md: {OUT_MD.name}")
    print(f"[R3-A] 통계 md: {OUT_STATS.name}")

    # 콘솔 요약
    print("\n=== 메타 통계 핵심 ===")
    print(f"화자 수 분포: {dict(s['n_speakers_dist'])}")
    print(f"단일 화자 카드: {dict(s['sole_speaker_cards'])}")
    print(f"direction(첫 단어): {dict(s['direction'])}")
    print(f"time_horizon: {dict(s['time_horizon'])}")
    print(f"confidence(첫 단어): {dict(s['confidence_first'])}")
    print(f"source 중복 명제: {s['dup_props_count']}건")


if __name__ == "__main__":
    main()
