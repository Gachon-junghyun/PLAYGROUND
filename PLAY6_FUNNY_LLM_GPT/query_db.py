from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path


BASE = Path(__file__).resolve().parent
DB_PATH = BASE / "data" / "microstyle.db"


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect the generated microstyle SQLite database.")
    parser.add_argument("--type", default=None, help="Candidate type filter.")
    parser.add_argument("--search", default=None, help="Substring search in utterance/context.")
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    if not DB_PATH.exists():
        raise SystemExit(f"DB not found. Run: python build_microstyle_db.py")

    clauses: list[str] = []
    params: list[str | int] = []
    if args.type:
        clauses.append("candidate_type = ?")
        params.append(args.type)
    if args.search:
        clauses.append("(utterance LIKE ? OR context_before LIKE ? OR context_after LIKE ?)")
        needle = f"%{args.search}%"
        params.extend([needle, needle, needle])

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"""
        SELECT candidate_id, score, candidate_type, source_path, line_number, utterance, tags_json
        FROM candidates
        {where}
        ORDER BY score DESC, source_path, line_number
        LIMIT ?
    """
    params.append(args.limit)

    with sqlite3.connect(DB_PATH) as con:
        for row in con.execute(sql, params):
            candidate_id, score, candidate_type, source_path, line_number, utterance, tags_json = row
            tags = json.loads(tags_json)
            print(f"[{score:02d}] {candidate_id} {candidate_type} {source_path}:{line_number}")
            print(f"  {utterance}")
            print(f"  tags={json.dumps(tags, ensure_ascii=False)}")


if __name__ == "__main__":
    main()
