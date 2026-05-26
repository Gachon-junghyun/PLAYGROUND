"""SQLite layer for block-writer. Stdlib only.

Data model (post-document support):
  documents : one row per writing piece. has its own title.
  blocks    : per-document scratch blocks (guidelines + propositions).
  doc_items : per-document canvas items (para / section / card / text / divider / quote).
  meta      : singleton config. tracks current_doc_id (last-opened doc).

State shape exchanged with the frontend (per-document):
  state = { title, blocks, doc }

Old single-document DBs auto-migrate on init(): a default "글 1" document is created
and all existing rows are assigned to it.
"""
from __future__ import annotations
import sqlite3
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).parent / "blocks.db"

TABLES_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  title TEXT NOT NULL DEFAULT '',
  current_doc_id TEXT,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS documents (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL DEFAULT '',
  position INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS blocks (
  id TEXT PRIMARY KEY,
  document_id TEXT REFERENCES documents(id) ON DELETE CASCADE,
  type TEXT NOT NULL CHECK (type IN ('proposition','guideline')),
  title TEXT NOT NULL DEFAULT '',
  body TEXT NOT NULL DEFAULT '',
  parent_id TEXT REFERENCES blocks(id) ON DELETE SET NULL,
  position INTEGER NOT NULL DEFAULT 0,
  -- Editorial metadata (added round 7):
  role TEXT,            -- claim / evidence / counter / definition / example / quote / implication / emotion / question / hypothesis / (null)
  source TEXT,          -- 1차 출처 (URL, 인용, 사건명 등)
  note TEXT,            -- 자기 메모: 캔버스에 안 보이는 메타 인지 공간
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS doc_items (
  id TEXT PRIMARY KEY,
  document_id TEXT REFERENCES documents(id) ON DELETE CASCADE,
  position INTEGER NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('para','section','card','text','divider','quote')),
  text TEXT,
  source TEXT,
  block_id TEXT REFERENCES blocks(id) ON DELETE SET NULL,
  title TEXT,
  body TEXT,
  block_type TEXT,
  level INTEGER,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
"""

INDEXES_SCHEMA = """
CREATE INDEX IF NOT EXISTS idx_documents_position ON documents(position);
CREATE INDEX IF NOT EXISTS idx_blocks_doc ON blocks(document_id);
CREATE INDEX IF NOT EXISTS idx_blocks_parent ON blocks(parent_id);
CREATE INDEX IF NOT EXISTS idx_blocks_position ON blocks(position);
CREATE INDEX IF NOT EXISTS idx_doc_items_doc ON doc_items(document_id);
CREATE INDEX IF NOT EXISTS idx_doc_items_position ON doc_items(position);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return secrets.token_hex(4)


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(DB_PATH)
    c.execute("PRAGMA foreign_keys = ON")
    c.row_factory = sqlite3.Row
    return c


# ============================================================
# init + migrations
# ============================================================
def init() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _conn() as c:
        c.executescript(TABLES_SCHEMA)
        c.execute(
            "INSERT OR IGNORE INTO meta (id, title, updated_at) VALUES (1, '', ?)",
            (_now(),),
        )
        # ---- column migrations on existing DBs ----
        di_cols = {r["name"] for r in c.execute("PRAGMA table_info(doc_items)")}
        for col, ddl in [
            ("title",       "ALTER TABLE doc_items ADD COLUMN title TEXT"),
            ("body",        "ALTER TABLE doc_items ADD COLUMN body TEXT"),
            ("block_type",  "ALTER TABLE doc_items ADD COLUMN block_type TEXT"),
            ("level",       "ALTER TABLE doc_items ADD COLUMN level INTEGER"),
            ("document_id", "ALTER TABLE doc_items ADD COLUMN document_id TEXT REFERENCES documents(id) ON DELETE CASCADE"),
        ]:
            if col not in di_cols:
                c.execute(ddl)
        b_cols = {r["name"] for r in c.execute("PRAGMA table_info(blocks)")}
        if "document_id" not in b_cols:
            c.execute("ALTER TABLE blocks ADD COLUMN document_id TEXT REFERENCES documents(id) ON DELETE CASCADE")
        for col, ddl in [
            ("role",   "ALTER TABLE blocks ADD COLUMN role TEXT"),
            ("source", "ALTER TABLE blocks ADD COLUMN source TEXT"),
            ("note",   "ALTER TABLE blocks ADD COLUMN note TEXT"),
        ]:
            if col not in b_cols:
                c.execute(ddl)
        m_cols = {r["name"] for r in c.execute("PRAGMA table_info(meta)")}
        if "current_doc_id" not in m_cols:
            c.execute("ALTER TABLE meta ADD COLUMN current_doc_id TEXT")
        c.commit()

        # ---- now that all columns are present, create indexes ----
        c.executescript(INDEXES_SCHEMA)
        c.commit()

        # ---- data migration: if there are rows without a document, move them to a default doc ----
        orphan_blocks = c.execute("SELECT COUNT(*) FROM blocks WHERE document_id IS NULL").fetchone()[0]
        orphan_docs   = c.execute("SELECT COUNT(*) FROM doc_items WHERE document_id IS NULL").fetchone()[0]
        meta = c.execute("SELECT title, current_doc_id FROM meta WHERE id = 1").fetchone()
        legacy_title = (meta["title"] or "").strip() if meta else ""

        if orphan_blocks > 0 or orphan_docs > 0 or (legacy_title and not _list_doc_rows(c)):
            default_doc_id = _new_id()
            ts = _now()
            c.execute(
                "INSERT INTO documents (id, title, position, created_at, updated_at) VALUES (?, ?, 0, ?, ?)",
                (default_doc_id, legacy_title or "글 1", ts, ts),
            )
            c.execute("UPDATE blocks SET document_id = ? WHERE document_id IS NULL", (default_doc_id,))
            c.execute("UPDATE doc_items SET document_id = ? WHERE document_id IS NULL", (default_doc_id,))
            c.execute(
                "UPDATE meta SET title = '', current_doc_id = ?, updated_at = ? WHERE id = 1",
                (default_doc_id, ts),
            )
            c.commit()

        # ---- ensure at least one document exists ----
        n_docs = c.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        if n_docs == 0:
            d_id = _new_id()
            ts = _now()
            c.execute(
                "INSERT INTO documents (id, title, position, created_at, updated_at) VALUES (?, ?, 0, ?, ?)",
                (d_id, "글 1", ts, ts),
            )
            c.execute("UPDATE meta SET current_doc_id = ?, updated_at = ? WHERE id = 1", (d_id, ts))
            c.commit()

        # ---- ensure current_doc_id points at a real document ----
        meta = c.execute("SELECT current_doc_id FROM meta WHERE id = 1").fetchone()
        cur = meta["current_doc_id"] if meta else None
        ok = False
        if cur:
            ok = bool(c.execute("SELECT 1 FROM documents WHERE id = ?", (cur,)).fetchone())
        if not ok:
            first = c.execute("SELECT id FROM documents ORDER BY position, created_at LIMIT 1").fetchone()
            if first:
                c.execute("UPDATE meta SET current_doc_id = ?, updated_at = ? WHERE id = 1", (first["id"], _now()))
                c.commit()


def _list_doc_rows(c) -> list:
    return list(c.execute("SELECT id FROM documents"))


# ============================================================
# documents
# ============================================================
def list_documents() -> list[dict[str, Any]]:
    with _conn() as c:
        rows = c.execute(
            "SELECT id, title, position, created_at, updated_at FROM documents ORDER BY position, created_at"
        ).fetchall()
        return [
            {
                "id": r["id"],
                "title": r["title"] or "",
                "position": r["position"],
                "createdAt": r["created_at"],
                "updatedAt": r["updated_at"],
            }
            for r in rows
        ]


def create_document(title: str = "") -> str:
    did = _new_id()
    ts = _now()
    with _conn() as c:
        max_pos = c.execute("SELECT COALESCE(MAX(position), -1) + 1 FROM documents").fetchone()[0]
        c.execute(
            "INSERT INTO documents (id, title, position, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (did, title or "", max_pos, ts, ts),
        )
        c.commit()
    return did


def rename_document(doc_id: str, title: str) -> bool:
    ts = _now()
    with _conn() as c:
        cur = c.execute(
            "UPDATE documents SET title = ?, updated_at = ? WHERE id = ?",
            (title or "", ts, doc_id),
        )
        c.commit()
        return cur.rowcount > 0


def delete_document(doc_id: str) -> bool:
    with _conn() as c:
        # If we're deleting the current doc, fall back to another.
        meta = c.execute("SELECT current_doc_id FROM meta WHERE id = 1").fetchone()
        cur = c.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        ok = cur.rowcount > 0
        if ok and meta and meta["current_doc_id"] == doc_id:
            nxt = c.execute("SELECT id FROM documents ORDER BY position, created_at LIMIT 1").fetchone()
            if nxt:
                c.execute("UPDATE meta SET current_doc_id = ?, updated_at = ? WHERE id = 1", (nxt["id"], _now()))
            else:
                # No documents left — create an empty one
                new_id = _new_id()
                ts = _now()
                c.execute(
                    "INSERT INTO documents (id, title, position, created_at, updated_at) VALUES (?, ?, 0, ?, ?)",
                    (new_id, "글 1", ts, ts),
                )
                c.execute("UPDATE meta SET current_doc_id = ?, updated_at = ? WHERE id = 1", (new_id, ts))
        c.commit()
        return ok


def get_current_doc_id() -> str | None:
    with _conn() as c:
        r = c.execute("SELECT current_doc_id FROM meta WHERE id = 1").fetchone()
        return r["current_doc_id"] if r else None


def set_current_doc(doc_id: str) -> bool:
    with _conn() as c:
        ok = c.execute("SELECT 1 FROM documents WHERE id = ?", (doc_id,)).fetchone()
        if not ok:
            return False
        c.execute("UPDATE meta SET current_doc_id = ?, updated_at = ? WHERE id = 1", (doc_id, _now()))
        c.commit()
        return True


def _resolve_doc(doc_id: str | None) -> str:
    """Return doc_id or the current one. If neither exists, raises."""
    if doc_id:
        return doc_id
    cur = get_current_doc_id()
    if not cur:
        raise ValueError("no current document set and no doc_id given")
    return cur


# ============================================================
# state per document
# ============================================================
def get_state(doc_id: str | None = None) -> dict[str, Any]:
    doc_id = _resolve_doc(doc_id)
    with _conn() as c:
        row = c.execute("SELECT title FROM documents WHERE id = ?", (doc_id,)).fetchone()
        if not row:
            raise ValueError(f"no such document: {doc_id}")
        title = row["title"] or ""
        blocks: list[dict[str, Any]] = []
        for r in c.execute(
            "SELECT id, type, title, body, parent_id, role, source, note FROM blocks "
            "WHERE document_id = ? ORDER BY position, id",
            (doc_id,),
        ):
            b: dict[str, Any] = {
                "id": r["id"],
                "type": r["type"],
                "title": r["title"] or "",
                "body": r["body"] or "",
            }
            if r["parent_id"]:
                b["parentId"] = r["parent_id"]
            if r["role"]:
                b["role"] = r["role"]
            if r["source"]:
                b["source"] = r["source"]
            if r["note"]:
                b["note"] = r["note"]
            blocks.append(b)
        doc: list[dict[str, Any]] = []
        for r in c.execute(
            "SELECT id, kind, text, source, block_id, title, body, block_type, level "
            "FROM doc_items WHERE document_id = ? ORDER BY position, id",
            (doc_id,),
        ):
            d: dict[str, Any] = {"id": r["id"], "kind": r["kind"]}
            if r["text"] is not None:
                d["text"] = r["text"]
            if r["source"]:
                d["source"] = r["source"]
            if r["block_id"]:
                d["blockId"] = r["block_id"]
            if r["title"] is not None:
                d["title"] = r["title"]
            if r["body"] is not None:
                d["body"] = r["body"]
            if r["block_type"]:
                d["blockType"] = r["block_type"]
            if r["level"] is not None:
                d["level"] = r["level"]
            doc.append(d)
        return {"title": title, "blocks": blocks, "doc": doc}


def set_state(state: dict[str, Any], doc_id: str | None = None) -> None:
    """Replace the entire state of a single document."""
    doc_id = _resolve_doc(doc_id)
    title = (state or {}).get("title", "") or ""
    blocks = (state or {}).get("blocks") or []
    doc = (state or {}).get("doc") or []
    ts = _now()
    with _conn() as c:
        # Ensure document exists.
        exists = c.execute("SELECT 1 FROM documents WHERE id = ?", (doc_id,)).fetchone()
        if not exists:
            raise ValueError(f"no such document: {doc_id}")
        c.execute(
            "UPDATE documents SET title = ?, updated_at = ? WHERE id = ?",
            (title, ts, doc_id),
        )
        c.execute("DELETE FROM doc_items WHERE document_id = ?", (doc_id,))
        c.execute("DELETE FROM blocks WHERE document_id = ?", (doc_id,))
        for i, b in enumerate(blocks):
            bid = b.get("id") or _new_id()
            btype = b.get("type", "proposition")
            if btype not in ("proposition", "guideline"):
                btype = "proposition"
            c.execute(
                "INSERT INTO blocks (id, document_id, type, title, body, parent_id, position, role, source, note, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?, ?)",
                (
                    bid, doc_id, btype,
                    b.get("title", "") or "", b.get("body", "") or "",
                    i,
                    b.get("role"), b.get("source"), b.get("note"),
                    ts, ts,
                ),
            )
        for b in blocks:
            pid = b.get("parentId")
            if pid:
                c.execute("UPDATE blocks SET parent_id = ? WHERE id = ?", (pid, b.get("id")))
        for i, d in enumerate(doc):
            kind = d.get("kind", "para")
            if kind not in ("para", "section", "card", "text", "divider", "quote"):
                kind = "para"
            did = d.get("id") or _new_id()
            c.execute(
                "INSERT INTO doc_items "
                "(id, document_id, kind, text, source, block_id, title, body, block_type, level, position, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    did, doc_id, kind,
                    d.get("text"), d.get("source"), d.get("blockId"),
                    d.get("title"), d.get("body"), d.get("blockType"), d.get("level"),
                    i, ts, ts,
                ),
            )
        c.commit()


def merge_state(incoming: dict[str, Any], doc_id: str | None = None) -> None:
    """Append incoming state into a single document. Remaps all incoming ids."""
    doc_id = _resolve_doc(doc_id)
    inc_blocks = (incoming or {}).get("blocks") or []
    inc_doc = (incoming or {}).get("doc") or []

    id_map: dict[str, str] = {}
    for b in inc_blocks:
        if "id" in b:
            id_map[b["id"]] = _new_id()

    ts = _now()
    with _conn() as c:
        exists = c.execute("SELECT 1 FROM documents WHERE id = ?", (doc_id,)).fetchone()
        if not exists:
            raise ValueError(f"no such document: {doc_id}")
        block_count = c.execute(
            "SELECT COUNT(*) FROM blocks WHERE document_id = ?", (doc_id,)
        ).fetchone()[0]
        last = c.execute(
            "SELECT id, kind, text, position FROM doc_items WHERE document_id = ? "
            "ORDER BY position DESC, id DESC LIMIT 1",
            (doc_id,),
        ).fetchone()
        if last and last["kind"] == "para" and not (last["text"] or "").strip():
            c.execute("DELETE FROM doc_items WHERE id = ?", (last["id"],))
        doc_count = c.execute(
            "SELECT COUNT(*) FROM doc_items WHERE document_id = ?", (doc_id,)
        ).fetchone()[0]

        for i, b in enumerate(inc_blocks):
            new_bid = id_map.get(b.get("id", ""), _new_id())
            btype = b.get("type", "proposition")
            if btype not in ("proposition", "guideline"):
                btype = "proposition"
            c.execute(
                "INSERT INTO blocks (id, document_id, type, title, body, parent_id, position, role, source, note, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?, ?)",
                (
                    new_bid, doc_id, btype,
                    b.get("title", "") or "", b.get("body", "") or "",
                    block_count + i,
                    b.get("role"), b.get("source"), b.get("note"),
                    ts, ts,
                ),
            )
        for b in inc_blocks:
            pid = b.get("parentId")
            if pid and pid in id_map:
                c.execute(
                    "UPDATE blocks SET parent_id = ? WHERE id = ?",
                    (id_map[pid], id_map[b["id"]]),
                )
        for i, d in enumerate(inc_doc):
            block_ref = d.get("blockId")
            if block_ref and block_ref in id_map:
                block_ref = id_map[block_ref]
            elif block_ref:
                hit = c.execute(
                    "SELECT 1 FROM blocks WHERE id = ? AND document_id = ?",
                    (block_ref, doc_id),
                ).fetchone()
                if not hit:
                    block_ref = None
            kind = d.get("kind", "para")
            if kind not in ("para", "section", "card", "text", "divider", "quote"):
                kind = "para"
            c.execute(
                "INSERT INTO doc_items "
                "(id, document_id, kind, text, source, block_id, title, body, block_type, level, position, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    _new_id(), doc_id, kind,
                    d.get("text"), d.get("source"), block_ref,
                    d.get("title"), d.get("body"), d.get("blockType"), d.get("level"),
                    doc_count + i, ts, ts,
                ),
            )
        # Title fallback: adopt incoming title if current is empty
        cur_title = c.execute(
            "SELECT title FROM documents WHERE id = ?", (doc_id,)
        ).fetchone()["title"]
        inc_title = (incoming or {}).get("title")
        if not cur_title and inc_title:
            c.execute(
                "UPDATE documents SET title = ?, updated_at = ? WHERE id = ?",
                (inc_title, ts, doc_id),
            )
        c.commit()


# ============================================================
# block-level helpers
# ============================================================
def search_blocks(query: str, doc_id: str | None = None) -> list[dict[str, Any]]:
    """Case-insensitive substring search. Optionally scoped to a document."""
    q = f"%{query}%"
    with _conn() as c:
        if doc_id:
            rows = c.execute(
                "SELECT id, document_id, type, title, body, parent_id FROM blocks "
                "WHERE document_id = ? AND (title LIKE ? COLLATE NOCASE OR body LIKE ? COLLATE NOCASE) "
                "ORDER BY type, title",
                (doc_id, q, q),
            ).fetchall()
        else:
            rows = c.execute(
                "SELECT id, document_id, type, title, body, parent_id FROM blocks "
                "WHERE title LIKE ? COLLATE NOCASE OR body LIKE ? COLLATE NOCASE "
                "ORDER BY type, title",
                (q, q),
            ).fetchall()
        out = []
        for r in rows:
            b = {
                "id": r["id"],
                "documentId": r["document_id"],
                "type": r["type"],
                "title": r["title"] or "",
                "body": r["body"] or "",
            }
            if r["parent_id"]:
                b["parentId"] = r["parent_id"]
            out.append(b)
        return out


def add_block(
    *,
    type: str,
    title: str = "",
    body: str = "",
    parent_id: str | None = None,
    role: str | None = None,
    source: str | None = None,
    note: str | None = None,
    doc_id: str | None = None,
) -> str:
    if type not in ("proposition", "guideline"):
        raise ValueError(f"bad type: {type}")
    doc_id = _resolve_doc(doc_id)
    bid = _new_id()
    ts = _now()
    with _conn() as c:
        ok = c.execute("SELECT 1 FROM documents WHERE id = ?", (doc_id,)).fetchone()
        if not ok:
            raise ValueError(f"no such document: {doc_id}")
        next_pos = c.execute(
            "SELECT COALESCE(MAX(position), -1) + 1 FROM blocks WHERE document_id = ?",
            (doc_id,),
        ).fetchone()[0]
        if parent_id:
            parent_ok = c.execute(
                "SELECT 1 FROM blocks WHERE id = ? AND document_id = ? AND type = 'guideline'",
                (parent_id, doc_id),
            ).fetchone()
            if not parent_ok:
                raise ValueError(f"parent_id {parent_id} is not a guideline in this document")
            if type != "proposition":
                raise ValueError("only propositions can have a parent_id")
        c.execute(
            "INSERT INTO blocks (id, document_id, type, title, body, parent_id, position, role, source, note, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (bid, doc_id, type, title, body, parent_id, next_pos, role, source, note, ts, ts),
        )
        c.commit()
    return bid


def delete_block(block_id: str) -> bool:
    with _conn() as c:
        cur = c.execute("DELETE FROM blocks WHERE id = ?", (block_id,))
        c.commit()
        return cur.rowcount > 0


def update_block(block_id: str, **fields: Any) -> bool:
    allowed = {"title", "body", "parent_id", "role", "source", "note"}
    sets = {k: v for k, v in fields.items() if k in allowed}
    if not sets:
        return False
    ts = _now()
    cols = ", ".join(f"{k} = ?" for k in sets) + ", updated_at = ?"
    vals = list(sets.values()) + [ts, block_id]
    with _conn() as c:
        cur = c.execute(f"UPDATE blocks SET {cols} WHERE id = ?", vals)
        c.commit()
        return cur.rowcount > 0
