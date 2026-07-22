"""SQLite 저장소 — content interning + segment 모델.

핵심 아이디어(= string interning / content-addressed):
- 같은 텍스트는 `contents` 에 딱 한 번 저장(norm UNIQUE). 등장은 전부 id 로 가리킨다.
- 화면에 계속 떠 있어 같은 (내용,앱)이 반복 잡히면, 새 행을 만들지 않고
  `segments` 한 행의 count/last_ts 만 갱신('지속'). 갭(config.SEGMENT_GAP_SEC)을
  넘겨 다시 나타나면 새 segment('재방문' 이벤트).

기존 `lines` 테이블(구버전)에서 자동 1회 마이그레이션한다(PRAGMA user_version).
"""
import json
import sqlite3

import config
import tagging

SCHEMA_VERSION = 3  # 2 이하 = 구 lines 모델 → 마이그레이션 필요


def get_conn():
    conn = sqlite3.connect(config.DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def init_db():
    conn = get_conn()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS captures(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              client_capture_id INTEGER,
              ts INTEGER NOT NULL,
              front_app TEXT, visible_apps TEXT, source TEXT,
              UNIQUE(client_capture_id)
            );
            CREATE TABLE IF NOT EXISTS contents(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              norm TEXT UNIQUE,
              text TEXT NOT NULL,
              char_len INTEGER
            );
            CREATE TABLE IF NOT EXISTS segments(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              content_id INTEGER NOT NULL,
              app TEXT,
              first_ts INTEGER NOT NULL,
              last_ts INTEGER NOT NULL,
              count INTEGER NOT NULL DEFAULT 1,
              x REAL, y REAL,
              capture_id INTEGER
            );
            CREATE INDEX IF NOT EXISTS idx_seg_lookup ON segments(content_id, app, last_ts);
            CREATE INDEX IF NOT EXISTS idx_seg_first ON segments(first_ts);
            CREATE INDEX IF NOT EXISTS idx_seg_last ON segments(last_ts);
            CREATE INDEX IF NOT EXISTS idx_captures_ts ON captures(ts);
            """
        )
        if conn.execute("PRAGMA user_version").fetchone()[0] < SCHEMA_VERSION:
            _migrate_from_lines(conn)
            conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        conn.commit()
    finally:
        conn.close()


def _migrate_from_lines(conn):
    """구 lines(행=등장) → contents+segments. 과거 데이터는 (내용,앱)별로 한 세그먼트로
    합친다(분당 갭 분할은 신규 데이터부터 정확; 과거는 근사). lines 가 없거나 비면 no-op."""
    has_lines = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='lines'"
    ).fetchone()
    if not has_lines:
        return
    if conn.execute("SELECT COUNT(*) FROM segments").fetchone()[0] > 0:
        return
    if conn.execute("SELECT COUNT(*) FROM lines").fetchone()[0] == 0:
        return
    conn.execute(
        "INSERT OR IGNORE INTO contents(norm, text, char_len) "
        "SELECT norm, MIN(text), length(MIN(text)) FROM lines "
        "WHERE norm IS NOT NULL AND norm != '' GROUP BY norm"
    )
    cmap = {r["norm"]: r["id"] for r in conn.execute("SELECT id, norm FROM contents")}
    rows = conn.execute(
        "SELECT l.norm norm, c.front_app app, MIN(c.ts) fs, MAX(c.ts) ls, COUNT(*) cnt "
        "FROM lines l JOIN captures c ON c.id = l.capture_id "
        "WHERE l.norm IS NOT NULL AND l.norm != '' GROUP BY l.norm, c.front_app"
    ).fetchall()
    conn.executemany(
        "INSERT INTO segments(content_id, app, first_ts, last_ts, count) VALUES(?,?,?,?,?)",
        [(cmap[r["norm"]], r["app"], r["fs"], r["ls"], r["cnt"]) for r in rows if r["norm"] in cmap],
    )


# --------------------------------------------------------------------------- #
# 적재
# --------------------------------------------------------------------------- #
def _get_content_id(cur, cache, norm, text):
    cid = cache.get(norm)
    if cid is not None:
        return cid
    cur.execute(
        "INSERT OR IGNORE INTO contents(norm, text, char_len) VALUES(?,?,?)",
        (norm, text, len(text)),
    )
    cid = cur.execute("SELECT id FROM contents WHERE norm = ?", (norm,)).fetchone()[0]
    cache[norm] = cid
    return cid


def _upsert_segment(cur, content_id, app, ts, x, y, capture_id):
    """반환: 새 세그먼트면 True, 기존 세그먼트 갱신(지속)이면 False."""
    row = cur.execute(
        "SELECT id, last_ts FROM segments "
        "WHERE content_id = ? AND app IS ? AND last_ts >= ? "
        "ORDER BY last_ts DESC LIMIT 1",
        (content_id, app, (ts or 0) - config.SEGMENT_GAP_SEC),
    ).fetchone()
    if row:
        cur.execute(
            "UPDATE segments SET last_ts = ?, count = count + 1, x = ?, y = ? WHERE id = ?",
            (max(row["last_ts"], ts or 0), x, y, row["id"]),
        )
        return False
    cur.execute(
        "INSERT INTO segments(content_id, app, first_ts, last_ts, count, x, y, capture_id) "
        "VALUES(?,?,?,?,1,?,?,?)",
        (content_id, app, ts, ts, x, y, capture_id),
    )
    return True


def insert_capture_batch(captures):
    """멱등(client_capture_id UNIQUE) 적재. 반환 카운트로 dedup 효과가 보인다."""
    received = len(captures)
    stored = observations = new_segments = dups = 0
    conn = get_conn()
    try:
        cur = conn.cursor()
        cache = {}
        for cap in sorted(captures, key=lambda c: c.get("ts") or 0):
            cur.execute(
                "INSERT OR IGNORE INTO captures(client_capture_id, ts, front_app, visible_apps, source)"
                " VALUES(?,?,?,?,?)",
                (
                    cap.get("client_capture_id"), cap.get("ts"), cap.get("front_app"),
                    json.dumps(cap.get("visible_apps") or [], ensure_ascii=False), cap.get("source"),
                ),
            )
            if cur.rowcount == 0:  # 중복 capture → 통째로 무시(세그먼트 count 오염 방지)
                dups += 1
                continue
            stored += 1
            cap_id, ts, app = cur.lastrowid, cap.get("ts"), cap.get("front_app")
            for ln in cap.get("lines") or []:
                norm = tagging.normalize(ln.get("text", ""))
                if not norm:
                    continue
                content_id = _get_content_id(cur, cache, norm, ln.get("text", ""))
                if _upsert_segment(cur, content_id, app, ts, ln.get("x"), ln.get("y"), cap_id):
                    new_segments += 1
                observations += 1
        conn.commit()
    finally:
        conn.close()
    return {
        "received": received,
        "stored": stored,
        "stored_lines": observations,   # 처리한 OCR 줄 수(구버전 호환 키)
        "new_segments": new_segments,    # 그중 실제로 새로 만든 세그먼트 수
        "duplicates_skipped": dups,
    }


# --------------------------------------------------------------------------- #
# 조회
# --------------------------------------------------------------------------- #
_SEG_COLS = ("c.text, c.norm, s.app front_app, s.first_ts, s.last_ts, s.count, "
             "s.x, s.y, s.content_id")


def fetch_range(ts_from, ts_to, limit):
    """[ts_from, ts_to) 와 겹치는 세그먼트를 시작시간순으로."""
    conn = get_conn()
    try:
        rows = conn.execute(
            f"SELECT {_SEG_COLS} FROM segments s JOIN contents c ON c.id = s.content_id "
            "WHERE s.last_ts >= ? AND s.first_ts < ? ORDER BY s.first_ts ASC LIMIT ?",
            (ts_from, ts_to, limit),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def search_segments(query, ts_from, ts_to, limit):
    """내용 텍스트 LIKE(공백 AND) 매칭 세그먼트를 최근순으로."""
    where, params = [], []
    for t in (query or "").split():
        where.append("c.text LIKE ?")
        params.append(f"%{t}%")
    if ts_from is not None:
        where.append("s.last_ts >= ?")
        params.append(ts_from)
    if ts_to is not None:
        where.append("s.first_ts < ?")
        params.append(ts_to)
    clause = (" WHERE " + " AND ".join(where)) if where else ""
    params.append(limit)
    conn = get_conn()
    try:
        rows = conn.execute(
            f"SELECT {_SEG_COLS} FROM segments s JOIN contents c ON c.id = s.content_id"
            + clause + " ORDER BY s.last_ts DESC LIMIT ?",
            params,
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def _chunks(seq, n=500):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def content_recall(content_ids):
    """content_id -> {fs(첫 등장), ls(마지막), total(총 관측), n_seg(등장 이벤트 수)}."""
    ids = [c for c in set(content_ids) if c is not None]
    out = {}
    if not ids:
        return out
    conn = get_conn()
    try:
        for chunk in _chunks(ids):
            ph = ",".join("?" * len(chunk))
            for r in conn.execute(
                "SELECT content_id, MIN(first_ts) fs, MAX(last_ts) ls, "
                "SUM(count) total, COUNT(*) n_seg "
                f"FROM segments WHERE content_id IN ({ph}) GROUP BY content_id",
                chunk,
            ):
                out[r["content_id"]] = {"fs": r["fs"], "ls": r["ls"],
                                        "total": r["total"], "n_seg": r["n_seg"]}
    finally:
        conn.close()
    return out


def search_contents(query, limit):
    """q 매칭 고유 내용(content) 목록을 최근 등장순으로. /history 용."""
    where, params = [], []
    for t in (query or "").split():
        where.append("c.text LIKE ?")
        params.append(f"%{t}%")
    clause = (" WHERE " + " AND ".join(where)) if where else ""
    params.append(limit)
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT c.id, c.text, MAX(s.last_ts) ls FROM contents c "
            "JOIN segments s ON s.content_id = c.id" + clause +
            " GROUP BY c.id ORDER BY ls DESC LIMIT ?",
            params,
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def segments_for_contents(content_ids, per_cap=200):
    """content_id -> [(first_ts, last_ts, count, app), ...] 시간순. 그래프 노드의 등장 이력."""
    ids = [c for c in dict.fromkeys(content_ids) if c is not None]
    out = {c: [] for c in ids}
    if not ids:
        return out
    conn = get_conn()
    try:
        for chunk in _chunks(ids):
            ph = ",".join("?" * len(chunk))
            for r in conn.execute(
                "SELECT content_id, first_ts, last_ts, count, app FROM segments "
                f"WHERE content_id IN ({ph}) ORDER BY first_ts ASC",
                chunk,
            ):
                bucket = out[r["content_id"]]
                if len(bucket) < per_cap:
                    bucket.append((r["first_ts"], r["last_ts"], r["count"], r["app"]))
    finally:
        conn.close()
    return out


def stats():
    conn = get_conn()
    try:
        caps = conn.execute("SELECT COUNT(*) FROM captures").fetchone()[0]
        contents = conn.execute("SELECT COUNT(*) FROM contents").fetchone()[0]
        segs = conn.execute("SELECT COUNT(*) FROM segments").fetchone()[0]
        obs = conn.execute("SELECT COALESCE(SUM(count),0) FROM segments").fetchone()[0]
        span = conn.execute("SELECT MIN(first_ts), MAX(last_ts) FROM segments").fetchone()
        return {"captures": caps, "contents": contents, "segments": segs,
                "observations": obs, "ts_min": span[0], "ts_max": span[1]}
    finally:
        conn.close()
