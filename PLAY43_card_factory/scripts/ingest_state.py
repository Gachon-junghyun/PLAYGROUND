"""신규 리포트 증분 추적 — seen_reports.json {report_id: {source, title, date}}.

소스 무관 공용. report_id는 어댑터가 make_id()로 만들어 넘긴다.
"같은 리포트 두 번 카드화" 방지 — 이게 "계속 최신만 가져오는" 루프의 핵심.
"""
import json
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import SEEN_REPORTS, ensure_dirs


def _load():
    if SEEN_REPORTS.exists():
        return json.loads(SEEN_REPORTS.read_text(encoding="utf-8"))
    return {}


def _save(state):
    ensure_dirs()
    SEEN_REPORTS.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def make_id(*parts):
    """소스 식별자들을 sha1 12자 report_id로. naver=broker|title|date, SA=url_hash 직접."""
    raw = "|".join(str(p).strip() for p in parts)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def is_seen(report_id):
    return report_id in _load()


def mark_seen(report_id, source, title, date=""):
    state = _load()
    state[report_id] = {"source": source, "title": (title or "")[:200], "date": date}
    _save(state)


def stats():
    state = _load()
    by_source = {}
    for v in state.values():
        by_source[v.get("source", "?")] = by_source.get(v.get("source", "?"), 0) + 1
    return {"total": len(state), "by_source": by_source}
