"""R4 신규 카드 통합 + 검수 + 메타 통계 (PLAY28 v2 incremental).

입력:  data/r4_cards_new/*.jsonl (A7~A10)
출력:
  data/r4_new_cards.jsonl   기계용 통합본
  data/r4_new_cards.md      사람용 (4 핵심 필드 풀)
  data/r4_new_stats.md      framework/grade/화자 분포

기존 r4_all_cards.jsonl/.md/_stats.md는 *변질 없음*. 사용자 결정 후 별도 머지 단계 필요.
"""
from __future__ import annotations
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
R4_DIR = DATA / "r4_cards_new"
OUT_JSONL = DATA / "r4_new_cards.jsonl"
OUT_MD = DATA / "r4_new_cards.md"
OUT_STATS = DATA / "r4_new_stats.md"

R4_CORE_FIELDS = ["attention_hook", "implicit_question", "reasoning_move", "matched_thinking_pattern"]
REQUIRED_FIELDS = [
    "card_id", "title", "framework_used",
    *R4_CORE_FIELDS,
    "causal_chain", "expected_direction", "time_horizon", "confidence",
    "speaker_views", "source_videos", "search_blurb",
]


def load_all() -> list[dict]:
    cards: list[dict] = []
    if not R4_DIR.exists():
        return cards
    for fp in sorted(R4_DIR.glob("*.jsonl")):
        for line in fp.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            c = json.loads(line)
            c["_batch"] = fp.stem
            cards.append(c)
    return cards


def audit(cards: list[dict]) -> list[str]:
    issues: list[str] = []
    ids = Counter(c.get("card_id") for c in cards)
    for cid, n in ids.items():
        if n > 1:
            issues.append(f"DUP card_id: {cid} ({n}회)")
    for c in cards:
        cid = c.get("card_id", "?")
        for f in REQUIRED_FIELDS:
            v = c.get(f)
            if v is None:
                issues.append(f"{cid}: missing field '{f}'")
            elif isinstance(v, (list, dict, str)) and not v:
                issues.append(f"{cid}: empty field '{f}'")
        srefs = c.get("source_references", [])
        if isinstance(srefs, list) and len(srefs) < 3:
            issues.append(f"{cid}: source_references {len(srefs)}개 (권장 3+)")
    return issues


def stats(cards: list[dict]) -> dict:
    s: dict = {"total": len(cards)}
    s["framework"] = Counter(c.get("framework_used", "?") for c in cards)
    grade = Counter()
    score_list: list[int] = []
    for c in cards:
        iq = c.get("insight_quality", {}) or {}
        grade[iq.get("grade", "?")] += 1
        score = iq.get("score_0_to_10")
        if isinstance(score, (int, float)):
            score_list.append(int(score))
    s["grade"] = grade
    s["score_avg"] = sum(score_list) / len(score_list) if score_list else 0
    sp_count = Counter()
    n_sp_dist = Counter()
    for c in cards:
        sv = c.get("speaker_views", {}) or {}
        n_sp_dist[len(sv)] += 1
        for sp in sv:
            sp_count[sp] += 1
    s["speaker_appearance"] = sp_count
    s["n_speakers_dist"] = n_sp_dist
    s["direction"] = Counter((c.get("expected_direction") or "?").split()[0] for c in cards)
    s["time_horizon"] = Counter(c.get("time_horizon", "?") or "?" for c in cards)
    lab = Counter()
    for c in cards:
        for l in c.get("labels", []):
            lab[l] += 1
    s["labels"] = lab
    s["batch"] = Counter(c.get("_batch", "?") for c in cards)
    return s


def write_md_summary(cards: list[dict]) -> None:
    cards_sorted = sorted(cards, key=lambda c: c.get("card_id", ""))
    ids_range = f"{cards_sorted[0].get('card_id','?')}~{cards_sorted[-1].get('card_id','?')}" if cards_sorted else "?"
    lines = [
        f"# R4 신규 카드 (PLAY28 v2) — {len(cards_sorted)}장 ({ids_range})\n",
        "> 4 핵심 필드 풀 + 메타. 28건 신규 영상 (지식부장관 9 / 오선 8 / 머니코믹스 7 / 김단테 4).\n\n",
    ]
    current_batch = None
    for c in cards_sorted:
        batch = c.get("_batch", "?")
        if batch != current_batch:
            lines.append(f"\n---\n## {batch}\n")
            current_batch = batch
        cid = c.get("card_id", "?")
        title = c.get("title", "?")
        fw = c.get("framework_used", "?")
        labels = ", ".join(c.get("labels", []))
        sv = c.get("speaker_views", {}) or {}
        speakers = " + ".join(sv.keys()) if sv else "—"
        direction = c.get("expected_direction", "?")
        horizon = c.get("time_horizon", "?")
        iq = c.get("insight_quality", {}) or {}
        grade = iq.get("grade", "?")
        score = iq.get("score_0_to_10", "?")
        lines.append(f"\n### {cid} {title}\n")
        lines.append(f"- `framework`: **{fw}** · `labels`: {labels} · `direction`: {direction} · `horizon`: {horizon}\n")
        lines.append(f"- `speakers`: {speakers} · `grade`: {grade} ({score}/10)\n")
        lines.append(f"- **attention_hook**: {c.get('attention_hook', '?')}\n")
        lines.append(f"- **implicit_question**: {c.get('implicit_question', '?')}\n")
        lines.append(f"- **reasoning_move**: {c.get('reasoning_move', '?')}\n")
        lines.append(f"- **matched_thinking_pattern**: {c.get('matched_thinking_pattern', '?')}\n")
        cc = c.get("causal_chain", "")
        if cc:
            lines.append(f"- `causal_chain`: {cc}\n")
    OUT_MD.write_text("".join(lines), encoding="utf-8")


def write_stats_md(s: dict, issues: list[str]) -> None:
    L = [f"# R4 신규 카드 메타 통계 (PLAY28 v2)\n\n",
         f"**총 카드 수**: {s['total']}장\n",
         f"**평균 점수**: {s['score_avg']:.2f}/10\n\n"]
    L.append("## Batch별\n")
    for b, n in sorted(s["batch"].items()):
        L.append(f"- {b}: {n}\n")
    L.append("\n## framework 분포\n")
    for f, n in s["framework"].most_common():
        L.append(f"- {f}: {n}\n")
    L.append("\n## grade 분포\n")
    for g, n in s["grade"].most_common():
        L.append(f"- {g}: {n}\n")
    L.append("\n## 화자 수\n")
    for n, cnt in sorted(s["n_speakers_dist"].items()):
        L.append(f"- 화자 {n}명: {cnt}장\n")
    L.append("\n## 화자 등장 빈도\n")
    for sp, n in s["speaker_appearance"].most_common():
        L.append(f"- {sp}: {n}\n")
    L.append("\n## direction\n")
    for d, n in s["direction"].most_common():
        L.append(f"- {d}: {n}\n")
    L.append("\n## time_horizon\n")
    for t, n in s["time_horizon"].most_common():
        L.append(f"- {t}: {n}\n")
    L.append("\n## labels\n")
    for l, n in s["labels"].most_common():
        L.append(f"- {l}: {n}\n")
    L.append("\n## 검수 이슈\n")
    if issues:
        for i in issues:
            L.append(f"- {i}\n")
    else:
        L.append("- 없음\n")
    OUT_STATS.write_text("".join(L), encoding="utf-8")


def main() -> None:
    cards = load_all()
    print(f"[R4-consolidate-new] 카드 로드: {len(cards)}장")
    if not cards:
        print("[err] r4_cards_new/ 비어있음. Agent 호출 먼저.")
        return
    issues = audit(cards)
    print(f"[R4-consolidate-new] 검수 이슈: {len(issues)}건")
    cards_sorted = sorted(cards, key=lambda c: c.get("card_id", ""))
    with OUT_JSONL.open("w", encoding="utf-8") as f:
        for c in cards_sorted:
            out = {k: v for k, v in c.items() if not k.startswith("_")}
            f.write(json.dumps(out, ensure_ascii=False) + "\n")
    print(f"[R4-consolidate-new] jsonl: {OUT_JSONL.name} ({OUT_JSONL.stat().st_size:,} chars)")
    s = stats(cards)
    write_md_summary(cards)
    write_stats_md(s, issues)
    print(f"[R4-consolidate-new] md:    {OUT_MD.name}")
    print(f"[R4-consolidate-new] stats: {OUT_STATS.name}")
    print(f"\n평균 점수: {s['score_avg']:.2f}/10")
    print(f"framework top5: {dict(s['framework'].most_common(5))}")
    print(f"grade: {dict(s['grade'])}")


if __name__ == "__main__":
    main()
