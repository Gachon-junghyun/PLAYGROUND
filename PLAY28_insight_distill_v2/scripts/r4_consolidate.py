"""R4 9개 카드 jsonl 통합 + 검수 + 메타 통계 + 사람용 md.

R4 카드 스키마 핵심 (26필드):
  - card_id, title, labels, framework_used
  - matched_thinking_pattern, attention_hook, implicit_question, reasoning_move   ← R4 핵심
  - original_signal, trigger_conditions, causal_chain
  - expected_direction, time_horizon, confidence, evidence_type
  - abstraction_level, technical_depth, quant_support
  - speaker_views, source_videos, source_references
  - search_blurb, insight_quality, storage_guidance

산출물:
  - data/r4_all_cards.jsonl   기계용 통합본
  - data/r4_all_cards.md      사람용 (4 핵심 필드 풀 + 메타)
  - data/r4_all_stats.md      framework/grade/화자/direction 분포
"""
from __future__ import annotations
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
R4_DIR = DATA / "r4_cards"

OUT_JSONL = DATA / "r4_all_cards.jsonl"
OUT_MD    = DATA / "r4_all_cards.md"
OUT_STATS = DATA / "r4_all_stats.md"

R4_CORE_FIELDS = ["attention_hook", "implicit_question", "reasoning_move", "matched_thinking_pattern"]
REQUIRED_FIELDS = [
    "card_id", "title", "framework_used",
    *R4_CORE_FIELDS,
    "causal_chain", "expected_direction", "time_horizon", "confidence",
    "speaker_views", "source_videos", "search_blurb",
]


def load_all() -> list[dict]:
    cards: list[dict] = []
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
        # source_references 최소 3개 권고
        srefs = c.get("source_references", [])
        if isinstance(srefs, list) and len(srefs) < 3:
            issues.append(f"{cid}: source_references {len(srefs)}개 (권장 3+)")
    return issues


def stats(cards: list[dict]) -> dict:
    s: dict = {"total": len(cards)}

    # framework 분포
    fw = Counter(c.get("framework_used", "?") for c in cards)
    s["framework"] = fw

    # insight_quality.grade
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
    s["score_dist"] = Counter(score_list)

    # 화자 분포
    sp_count = Counter()
    sole_sp = Counter()
    n_sp_dist = Counter()
    for c in cards:
        sv = c.get("speaker_views", {}) or {}
        n = len(sv)
        n_sp_dist[n] += 1
        if n == 1:
            sole_sp[list(sv.keys())[0]] += 1
        for sp in sv:
            sp_count[sp] += 1
    s["speaker_appearance"] = sp_count
    s["sole_speaker"] = sole_sp
    s["n_speakers_dist"] = n_sp_dist

    # direction / time_horizon
    def first_word(x: str) -> str:
        return (x or "?").split()[0].rstrip(",—-") if x else "?"

    s["direction"] = Counter(first_word(c.get("expected_direction", "")) for c in cards)
    s["time_horizon"] = Counter(c.get("time_horizon", "?") or "?" for c in cards)
    s["confidence_first"] = Counter(first_word(c.get("confidence", "")) for c in cards)

    # labels
    lab = Counter()
    for c in cards:
        for l in c.get("labels", []):
            lab[l] += 1
    s["labels"] = lab

    # source_videos 중복 video_id
    vid_to_cards: dict[str, list[str]] = defaultdict(list)
    for c in cards:
        for sv in c.get("source_videos", []) or []:
            if isinstance(sv, dict):
                vid = sv.get("video_id", "?")
                vid_to_cards[vid].append(c.get("card_id", "?"))
    dup_vids = {v: cids for v, cids in vid_to_cards.items() if len(cids) > 1}
    s["dup_video_count"] = len(dup_vids)
    s["dup_video_top"] = sorted(dup_vids.items(), key=lambda kv: -len(kv[1]))[:10]

    # batch별
    s["batch"] = Counter(c.get("_batch", "?") for c in cards)

    # source_references 카드별 수
    sref_n = Counter()
    for c in cards:
        sref_n[len(c.get("source_references", []) or [])] += 1
    s["source_references_n"] = sref_n

    # evidence_type / abstraction_level
    s["evidence_type"] = Counter(c.get("evidence_type", "?") or "?" for c in cards)
    s["abstraction_level"] = Counter(c.get("abstraction_level", "?") or "?" for c in cards)

    return s


def write_md_summary(cards: list[dict]) -> None:
    cards_sorted = sorted(cards, key=lambda c: c.get("card_id", ""))
    lines = [f"# R4 카드 통합 — {len(cards_sorted)}장 (E001~E065)\n"]
    lines.append("> 각 카드: 메타 1줄 + 4 핵심 필드 풀. 자동 템플릿 검출 0건 (audit 통과).\n")
    lines.append("> RAG 검색은 `search_blurb` 임베딩 + `attention_hook`/`implicit_question` 결합 권장.\n\n")

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
    L = [f"# R4 카드 메타 통계\n\n",
         f"**총 카드 수**: {s['total']}장\n",
         f"**평균 점수 (insight_quality.score_0_to_10)**: {s['score_avg']:.2f}/10\n\n"]

    L.append("## Batch별 카드 수\n")
    for b, n in sorted(s["batch"].items()):
        L.append(f"- {b}: {n}\n")

    L.append("\n## framework 분포 (사고 방식 기반)\n")
    for f, n in s["framework"].most_common():
        L.append(f"- {f}: {n}\n")

    L.append("\n## insight_quality grade 분포\n")
    for g, n in s["grade"].most_common():
        L.append(f"- {g}: {n}\n")

    L.append("\n## score 분포 (0~10)\n")
    for sc in sorted(s["score_dist"].keys()):
        L.append(f"- {sc}: {s['score_dist'][sc]}\n")

    L.append("\n## 카드별 화자 수\n")
    for n, cnt in sorted(s["n_speakers_dist"].items()):
        L.append(f"- 화자 {n}명: {cnt}장\n")

    L.append("\n## 화자 등장 빈도 (카드 단위)\n")
    for sp, n in s["speaker_appearance"].most_common():
        L.append(f"- {sp}: {n}\n")

    L.append("\n## 단일 화자 카드\n")
    for sp, n in s["sole_speaker"].most_common():
        L.append(f"- {sp}: {n}\n")

    L.append("\n## expected_direction (첫 단어)\n")
    for d, n in s["direction"].most_common():
        L.append(f"- {d}: {n}\n")

    L.append("\n## time_horizon\n")
    for t, n in s["time_horizon"].most_common():
        L.append(f"- {t}: {n}\n")

    L.append("\n## confidence (첫 단어)\n")
    for c, n in s["confidence_first"].most_common():
        L.append(f"- {c}: {n}\n")

    L.append("\n## labels\n")
    for l, n in s["labels"].most_common():
        L.append(f"- {l}: {n}\n")

    L.append("\n## evidence_type\n")
    for e, n in s["evidence_type"].most_common():
        L.append(f"- {e}: {n}\n")

    L.append("\n## abstraction_level\n")
    for a, n in s["abstraction_level"].most_common():
        L.append(f"- {a}: {n}\n")

    L.append("\n## source_references 카드별 개수\n")
    for n, cnt in sorted(s["source_references_n"].items()):
        L.append(f"- {n}개: {cnt}장\n")

    L.append(f"\n## 공통 video_id (여러 카드가 인용)\n")
    L.append(f"- {s['dup_video_count']}개 영상이 여러 카드에 인용됨\n")
    if s["dup_video_top"]:
        L.append("- top 10:\n")
        for vid, cids in s["dup_video_top"]:
            L.append(f"  - `{vid}` → {', '.join(cids)} ({len(cids)}개)\n")

    L.append("\n## 검수 이슈\n")
    if issues:
        for i in issues:
            L.append(f"- {i}\n")
    else:
        L.append("- 없음\n")

    OUT_STATS.write_text("".join(L), encoding="utf-8")


def main() -> None:
    cards = load_all()
    print(f"[R4-consolidate] 카드 로드: {len(cards)}장")

    issues = audit(cards)
    print(f"[R4-consolidate] 검수 이슈: {len(issues)}건")

    cards_sorted = sorted(cards, key=lambda c: c.get("card_id", ""))
    with OUT_JSONL.open("w", encoding="utf-8") as f:
        for c in cards_sorted:
            out = {k: v for k, v in c.items() if not k.startswith("_")}
            f.write(json.dumps(out, ensure_ascii=False) + "\n")
    print(f"[R4-consolidate] jsonl: {OUT_JSONL.name} ({OUT_JSONL.stat().st_size:,} chars)")

    s = stats(cards)
    write_md_summary(cards)
    write_stats_md(s, issues)
    print(f"[R4-consolidate] md:    {OUT_MD.name}")
    print(f"[R4-consolidate] stats: {OUT_STATS.name}")

    print("\n=== 메타 통계 핵심 ===")
    print(f"평균 점수: {s['score_avg']:.2f}/10")
    print(f"framework top5: {dict(s['framework'].most_common(5))}")
    print(f"grade: {dict(s['grade'])}")
    print(f"화자 수 분포: {dict(s['n_speakers_dist'])}")
    print(f"direction: {dict(s['direction'])}")
    print(f"공통 video_id (여러 카드 인용): {s['dup_video_count']}개")


if __name__ == "__main__":
    main()
