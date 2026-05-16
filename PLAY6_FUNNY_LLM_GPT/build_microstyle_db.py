from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable


BASE = Path(__file__).resolve().parent
DEFAULT_TRANSCRIPTS = BASE / "youtube_whisper" / "transcripts"
DATA_DIR = BASE / "data"
REPORT_DIR = BASE / "reports"


REACTION_PATTERNS = [
    r"^네\??$",
    r"^왜요\??$",
    r"^뭐야\??$",
    r"^뭔데\??$",
    r"^아니\b",
    r"^아\b",
    r"^오\b",
    r"^와\b",
    r"^에이\b",
    r"^그렇구나$",
    r"^괜찮",
    r"ㄱㄱ|ㄴㄴ|ㅇㅋ|ㅇㅈ|ㄹㅇ|ㄱㅊ",
]

DEVICE_KEYWORDS = {
    "묘사": ["묘사", "상황극", "1인 다역", "장면", "직접 묘사"],
    "반전": ["반전", "꺾", "갑자기", "방점", "미괄식"],
    "회수": ["다시", "까먹었을 때", "툭 던지는", "소재삼아"],
    "완곡화": ["완곡", "부담", "조심", "어디 쪽"],
    "과장": ["대박", "국가적", "개", "겁나", "너무너무"],
    "능청": ["알아요", "생긴 대로", "그딴", "물론", "원래"],
    "질문": ["물어", "질문", "여쭤", "어떻게", "왜"],
    "수습": ["괜찮", "수습", "해결", "대안", "도움"],
}

FUNCTION_KEYWORDS = {
    "위로": ["괜찮", "아냐", "부담 감소", "상처", "불안"],
    "동의": ["맞", "그렇", "인정", "ㅇㅈ"],
    "받아치기": ["뭔데", "뭐야", "왜요", "네가 뭔데", "이러네"],
    "정정": ["아니", "그게 아니라", "그렇다기보다는", "바로잡"],
    "수습": ["수습", "해결", "대안", "완화"],
    "대화유지": ["질문", "이어", "대화", "계속", "말벗"],
    "긴장완화": ["웃", "재밌", "농담", "머쓱", "민망"],
}

RISK_KEYWORDS = ["무례", "불편", "부담", "조롱", "상처", "지뢰", "실패", "망한", "욕"]


@dataclass
class Source:
    source_id: str
    path: str
    line_count: int
    sha1: str


@dataclass
class Chunk:
    chunk_id: str
    source_id: str
    source_path: str
    start_line: int
    end_line: int
    text: str


@dataclass
class Candidate:
    candidate_id: str
    source_id: str
    source_path: str
    line_number: int
    utterance: str
    context_before: list[str]
    context_after: list[str]
    candidate_type: str
    score: int
    tags: dict[str, list[str] | str]
    note: str


def read_lines(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def stable_id(*parts: str, length: int = 12) -> str:
    raw = "\n".join(parts).encode("utf-8")
    return hashlib.sha1(raw).hexdigest()[:length]


def iter_transcript_files(root: Path) -> Iterable[Path]:
    yield from sorted(p for p in root.rglob("*.txt") if p.is_file())


def load_sources(root: Path) -> tuple[list[Source], dict[str, list[str]]]:
    sources: list[Source] = []
    content_by_hash: dict[str, str] = {}
    lines_by_source: dict[str, list[str]] = {}

    for path in iter_transcript_files(root):
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            continue
        sha1 = hashlib.sha1(text.encode("utf-8")).hexdigest()
        if sha1 in content_by_hash:
            continue
        source_id = f"src_{stable_id(str(path.relative_to(BASE)), sha1)}"
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        sources.append(Source(source_id, str(path.relative_to(BASE)), len(lines), sha1))
        lines_by_source[source_id] = lines
        content_by_hash[sha1] = source_id

    return sources, lines_by_source


def make_chunks(sources: list[Source], lines_by_source: dict[str, list[str]], size: int, overlap: int) -> list[Chunk]:
    chunks: list[Chunk] = []
    step = max(1, size - overlap)
    for source in sources:
        lines = lines_by_source[source.source_id]
        for start in range(0, len(lines), step):
            window = lines[start:start + size]
            if not window:
                continue
            chunk_id = f"chk_{stable_id(source.source_id, str(start + 1), ' '.join(window[:2]))}"
            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    source_id=source.source_id,
                    source_path=source.path,
                    start_line=start + 1,
                    end_line=start + len(window),
                    text="\n".join(window),
                )
            )
            if start + size >= len(lines):
                break
    return chunks


def has_reaction_shape(line: str) -> bool:
    compact = re.sub(r"\s+", "", line)
    if len(compact) <= 12 and any(ch in line for ch in ["?", "!", "아", "오", "와", "네", "왜", "뭐"]):
        return True
    return any(re.search(pattern, line) for pattern in REACTION_PATTERNS)


def collect_matches(line: str, table: dict[str, list[str]]) -> list[str]:
    hits = []
    for key, words in table.items():
        if any(word in line for word in words):
            hits.append(key)
    return hits


def classify_line(line: str, before: list[str], after: list[str]) -> tuple[str, int, dict[str, list[str] | str], str]:
    joined_context = "\n".join(before + [line] + after)
    devices = sorted(set(collect_matches(joined_context, DEVICE_KEYWORDS)))
    functions = sorted(set(collect_matches(joined_context, FUNCTION_KEYWORDS)))
    risk = "high" if any(word in joined_context for word in RISK_KEYWORDS) else "low"

    score = 0
    if has_reaction_shape(line):
        score += 4
    if "?" in line:
        score += 2
    if devices:
        score += 2 + min(3, len(devices))
    if functions:
        score += 1 + min(2, len(functions))
    if any(word in line for word in ["웃", "재밌", "노잼", "센스", "삼행시", "장난"]):
        score += 3
    if len(line) <= 30:
        score += 1
    if len(line) > 120:
        score -= 2

    if has_reaction_shape(line) and len(line) <= 40:
        candidate_type = "micro_reaction"
        note = "짧은 리액션 또는 받아치기 후보"
    elif any(word in joined_context for word in ["재밌", "웃", "노잼", "삼행시", "개그", "유머"]):
        candidate_type = "humor_device"
        note = "재미를 만드는 장치나 설명 후보"
    elif any(word in joined_context for word in ["무례", "부담", "친해", "센스", "호감", "완곡"]):
        candidate_type = "social_judgment"
        note = "관계 거리와 눈치 판단 후보"
    elif "?" in line or any(word in line for word in ["물어", "질문", "여쭤"]):
        candidate_type = "conversation_move"
        note = "대화를 이어가는 질문/전환 후보"
    else:
        candidate_type = "principle"
        note = "말하기 원리 후보"

    tags: dict[str, list[str] | str] = {
        "style_devices": devices,
        "reply_functions": functions,
        "risk": risk,
        "energy": "high" if any(w in joined_context for w in ["!", "대박", "개", "너무"]) else "medium",
    }
    return candidate_type, score, tags, note


def extract_candidates(
    sources: list[Source],
    lines_by_source: dict[str, list[str]],
    min_score: int,
    context: int,
) -> list[Candidate]:
    candidates: list[Candidate] = []
    seen: set[str] = set()

    for source in sources:
        lines = lines_by_source[source.source_id]
        for index, line in enumerate(lines):
            before = lines[max(0, index - context):index]
            after = lines[index + 1:index + 1 + context]
            candidate_type, score, tags, note = classify_line(line, before, after)
            if score < min_score:
                continue
            fingerprint = stable_id(line, "\n".join(before), "\n".join(after), length=16)
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            candidate_id = f"cand_{stable_id(source.source_id, str(index + 1), line)}"
            candidates.append(
                Candidate(
                    candidate_id=candidate_id,
                    source_id=source.source_id,
                    source_path=source.path,
                    line_number=index + 1,
                    utterance=line,
                    context_before=before,
                    context_after=after,
                    candidate_type=candidate_type,
                    score=score,
                    tags=tags,
                    note=note,
                )
            )

    return sorted(candidates, key=lambda c: (-c.score, c.source_path, c.line_number))


def write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def make_annotator_task(candidate: Candidate) -> dict:
    return {
        "task_id": f"task_{candidate.candidate_id.removeprefix('cand_')}",
        "instruction": (
            "아래 전사 후보를 한국어 마이크로스타일 DB 항목으로 정리하라. "
            "원문을 그대로 외우는 데이터가 아니라, 상황/기능/말투 장치/피해야 할 맥락/재사용 템플릿을 뽑아라."
        ),
        "schema": {
            "entry_type": "micro_reaction | humor_device | social_judgment | conversation_move | principle",
            "utterance": "핵심 발화 또는 요약",
            "context": "이 발화가 작동하는 상황",
            "social_function": ["위로", "동의", "받아치기", "정정", "수습", "대화유지", "긴장완화"],
            "style_devices": ["묘사", "반전", "회수", "완곡화", "과장", "능청", "질문", "수습"],
            "usable_when": ["사용 가능한 맥락"],
            "avoid_when": ["피해야 할 맥락"],
            "rewrite_templates": ["비슷한 기능의 새 문장 2~5개"],
        },
        "source": {
            "candidate_id": candidate.candidate_id,
            "source_path": candidate.source_path,
            "line_number": candidate.line_number,
        },
        "input": {
            "context_before": candidate.context_before,
            "utterance": candidate.utterance,
            "context_after": candidate.context_after,
            "heuristic_tags": candidate.tags,
            "heuristic_type": candidate.candidate_type,
        },
    }


def write_sqlite(path: Path, sources: list[Source], chunks: list[Chunk], candidates: list[Candidate]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    con = sqlite3.connect(path)
    try:
        con.execute("PRAGMA journal_mode=WAL")
        con.execute(
            """
            CREATE TABLE sources (
                source_id TEXT PRIMARY KEY,
                path TEXT NOT NULL,
                line_count INTEGER NOT NULL,
                sha1 TEXT NOT NULL
            )
            """
        )
        con.execute(
            """
            CREATE TABLE chunks (
                chunk_id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                source_path TEXT NOT NULL,
                start_line INTEGER NOT NULL,
                end_line INTEGER NOT NULL,
                text TEXT NOT NULL
            )
            """
        )
        con.execute(
            """
            CREATE TABLE candidates (
                candidate_id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                source_path TEXT NOT NULL,
                line_number INTEGER NOT NULL,
                utterance TEXT NOT NULL,
                context_before TEXT NOT NULL,
                context_after TEXT NOT NULL,
                candidate_type TEXT NOT NULL,
                score INTEGER NOT NULL,
                tags_json TEXT NOT NULL,
                note TEXT NOT NULL
            )
            """
        )
        con.executemany(
            "INSERT INTO sources VALUES (:source_id, :path, :line_count, :sha1)",
            [asdict(s) for s in sources],
        )
        con.executemany(
            "INSERT INTO chunks VALUES (:chunk_id, :source_id, :source_path, :start_line, :end_line, :text)",
            [asdict(c) for c in chunks],
        )
        con.executemany(
            """
            INSERT INTO candidates VALUES (
                :candidate_id, :source_id, :source_path, :line_number, :utterance,
                :context_before, :context_after, :candidate_type, :score, :tags_json, :note
            )
            """,
            [
                {
                    **asdict(c),
                    "context_before": json.dumps(c.context_before, ensure_ascii=False),
                    "context_after": json.dumps(c.context_after, ensure_ascii=False),
                    "tags_json": json.dumps(c.tags, ensure_ascii=False),
                }
                for c in candidates
            ],
        )
        con.execute("CREATE INDEX idx_candidates_type_score ON candidates(candidate_type, score DESC)")
        con.execute("CREATE INDEX idx_candidates_source_line ON candidates(source_path, line_number)")
        con.commit()
    finally:
        con.close()


def write_report(path: Path, sources: list[Source], chunks: list[Chunk], candidates: list[Candidate]) -> None:
    by_type = Counter(c.candidate_type for c in candidates)
    by_source = Counter(c.source_path for c in candidates)
    devices = Counter()
    functions = Counter()
    for c in candidates:
        devices.update(c.tags.get("style_devices", []))
        functions.update(c.tags.get("reply_functions", []))

    top_examples = candidates[:20]
    lines = [
        "# Microstyle DB Build Report",
        "",
        "## Summary",
        f"- Sources: {len(sources)}",
        f"- Chunks: {len(chunks)}",
        f"- Candidates: {len(candidates)}",
        "",
        "## Candidate Types",
    ]
    for key, count in by_type.most_common():
        lines.append(f"- {key}: {count}")
    lines.extend(["", "## Top Style Devices"])
    for key, count in devices.most_common(12):
        lines.append(f"- {key}: {count}")
    lines.extend(["", "## Top Reply Functions"])
    for key, count in functions.most_common(12):
        lines.append(f"- {key}: {count}")
    lines.extend(["", "## Candidates By Source"])
    for key, count in by_source.most_common():
        lines.append(f"- `{key}`: {count}")
    lines.extend(["", "## High Score Examples"])
    for c in top_examples:
        lines.append("")
        lines.append(f"### {c.candidate_id} ({c.score}, {c.candidate_type})")
        lines.append(f"- Source: `{c.source_path}:{c.line_number}`")
        lines.append(f"- Utterance: {c.utterance}")
        if c.context_before:
            lines.append(f"- Before: {' / '.join(c.context_before[-2:])}")
        if c.context_after:
            lines.append(f"- After: {' / '.join(c.context_after[:2])}")
        lines.append(f"- Tags: `{json.dumps(c.tags, ensure_ascii=False)}`")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a Korean microstyle candidate database from transcript text.")
    parser.add_argument("--transcripts", type=Path, default=DEFAULT_TRANSCRIPTS, help="Transcript root directory.")
    parser.add_argument("--chunk-lines", type=int, default=24, help="Lines per raw chunk.")
    parser.add_argument("--overlap", type=int, default=4, help="Overlapping lines between chunks.")
    parser.add_argument("--min-score", type=int, default=5, help="Minimum heuristic score for a candidate.")
    parser.add_argument("--context", type=int, default=3, help="Lines before/after a candidate.")
    args = parser.parse_args()

    if not args.transcripts.exists():
        raise SystemExit(f"Transcript directory not found: {args.transcripts}")

    sources, lines_by_source = load_sources(args.transcripts)
    chunks = make_chunks(sources, lines_by_source, args.chunk_lines, args.overlap)
    candidates = extract_candidates(sources, lines_by_source, args.min_score, args.context)
    tasks = [make_annotator_task(c) for c in candidates]

    DATA_DIR.mkdir(exist_ok=True)
    REPORT_DIR.mkdir(exist_ok=True)

    write_jsonl(DATA_DIR / "sources.jsonl", [asdict(s) for s in sources])
    write_jsonl(DATA_DIR / "raw_chunks.jsonl", [asdict(c) for c in chunks])
    write_jsonl(DATA_DIR / "microstyle_candidates.jsonl", [asdict(c) for c in candidates])
    write_jsonl(DATA_DIR / "annotator_tasks.jsonl", tasks)
    write_sqlite(DATA_DIR / "microstyle.db", sources, chunks, candidates)
    write_report(REPORT_DIR / "summary.md", sources, chunks, candidates)

    print(f"[OK] sources: {len(sources)}")
    print(f"[OK] chunks: {len(chunks)} -> {DATA_DIR / 'raw_chunks.jsonl'}")
    print(f"[OK] candidates: {len(candidates)} -> {DATA_DIR / 'microstyle_candidates.jsonl'}")
    print(f"[OK] annotator tasks: {len(tasks)} -> {DATA_DIR / 'annotator_tasks.jsonl'}")
    print(f"[OK] sqlite: {DATA_DIR / 'microstyle.db'}")
    print(f"[OK] report: {REPORT_DIR / 'summary.md'}")


if __name__ == "__main__":
    main()
