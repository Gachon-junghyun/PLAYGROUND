"""B1. 적재 — records.jsonl 의 trigger 를 임베딩해 SQLite 에 저장.

설계:
- 임베딩 대상은 trigger(상황 서술)다. 본문(text)이 아니다.
- 백엔드 EMBED_BACKEND ∈ {gemini(기본), openai, bge, stub}.
    stub = 키 없이 도는 결정론적 해시 임베더(오프라인 파이프라인 검증용).
- 저장: stdlib sqlite3 한 파일.
    records(메타 전체) · vec_triggers(record_id, aspect, dim, embedding=JSON, tokens=JSON) · meta(model).
    벡터는 JSON 으로 저장해 외부 의존 없이 순수 파이썬 cosine 으로 검색 가능(retrieve.py).
    sqlite-vec 가 설치돼 있으면 retrieve 가 KNN 가속을 쓰지만, 적재 포맷은 백엔드 무관.
- 재적재: record_id upsert. meta 에 임베딩 모델명을 박아 모델 불일치 검색을 차단한다.

CLI:  python embed_store.py [records.jsonl 경로]   (기본: ../knowledge/records.jsonl)
"""
import hashlib
import json
import math
import os
import re
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_RECORDS = HERE.parent / "knowledge" / "records.jsonl"
DB_PATH = HERE / "store.db"

BACKEND = os.environ.get("EMBED_BACKEND", "gemini").lower()

# trigger 토큰화(BM25/형태소 대용): 한글/영문/숫자 연속을 토큰으로. 형태소 분석기 없이 공백+문자류.
_TOK = re.compile(r"[가-힣]+|[A-Za-z]+|[0-9]+")


def tokenize(text):
    return [t.lower() for t in _TOK.findall(text)]


# --- 임베더 ----------------------------------------------------------------
class Embedder:
    """name/dim/embed(texts, task_type) 를 가진 백엔드 래퍼."""

    def __init__(self, name, dim, fn):
        self.name = name
        self.dim = dim
        self._fn = fn

    def embed(self, texts, task_type):
        return self._fn(texts, task_type)


def _stub_embed_factory(dim=256):
    """결정론적 해시 BoW 임베더. 공유 토큰이 많을수록 가까워진다(배관 검증용)."""
    def fn(texts, task_type):
        out = []
        for t in texts:
            v = [0.0] * dim
            for tok in tokenize(t):
                h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
                v[h % dim] += 1.0
            n = math.sqrt(sum(x * x for x in v)) or 1.0
            out.append([x / n for x in v])
        return out
    return Embedder("stub-hash-256", dim, fn)


def _gemini_embedder(dim=768):
    from google import genai
    from google.genai import types
    client = genai.Client()  # GEMINI_API_KEY 환경변수

    def fn(texts, task_type):
        r = client.models.embed_content(
            model="gemini-embedding-001", contents=list(texts),
            config=types.EmbedContentConfig(task_type=task_type, output_dimensionality=dim),
        )
        return [list(e.values) for e in r.embeddings]
    return Embedder("gemini-embedding-001@768", dim, fn)


def _openai_embedder(dim=1536):
    from openai import OpenAI
    client = OpenAI()  # OPENAI_API_KEY

    def fn(texts, task_type):  # task_type 무시(대칭 모델)
        r = client.embeddings.create(model="text-embedding-3-small", input=list(texts))
        return [d.embedding for d in r.data]
    return Embedder("text-embedding-3-small", dim, fn)


def _bge_embedder():
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("BAAI/bge-m3")

    def fn(texts, task_type):
        return [v.tolist() for v in model.encode(list(texts), normalize_embeddings=True)]
    return Embedder("bge-m3", 1024, fn)


def get_embedder():
    if BACKEND == "stub":
        return _stub_embed_factory()
    if BACKEND == "gemini":
        return _gemini_embedder()
    if BACKEND == "openai":
        return _openai_embedder()
    if BACKEND == "bge":
        return _bge_embedder()
    raise SystemExit(f"unknown EMBED_BACKEND={BACKEND!r}")


# --- DB --------------------------------------------------------------------
def _init_db(con):
    con.executescript("""
        CREATE TABLE IF NOT EXISTS records(
            id TEXT PRIMARY KEY, type TEXT, text TEXT, aspect TEXT, trigger TEXT,
            tier TEXT, conflict_group TEXT, source TEXT, usage_count INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS vec_triggers(
            record_id TEXT PRIMARY KEY, aspect TEXT, embedding TEXT, tokens TEXT);
        CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT);
    """)


def build_store(records_path=DEFAULT_RECORDS, db_path=DB_PATH):
    records_path, db_path = Path(records_path), Path(db_path)
    emb = get_embedder()
    recs = [json.loads(l) for l in records_path.read_text(encoding="utf-8").splitlines() if l.strip()]

    con = sqlite3.connect(db_path)
    _init_db(con)
    # 모델 불일치 가드: 기존 DB 가 다른 모델로 적재됐으면 벡터 테이블을 비운다.
    prev = con.execute("SELECT v FROM meta WHERE k='embed_model'").fetchone()
    if prev and prev[0] != emb.name:
        con.execute("DELETE FROM vec_triggers")
    con.execute("INSERT OR REPLACE INTO meta(k,v) VALUES('embed_model',?)", (emb.name,))
    con.execute("INSERT OR REPLACE INTO meta(k,v) VALUES('dim',?)", (str(emb.dim),))

    triggers = [r["trigger"] for r in recs]
    vecs = emb.embed(triggers, "RETRIEVAL_DOCUMENT")  # trigger = 문서로 색인
    for r, v in zip(recs, vecs):
        con.execute(
            "INSERT OR REPLACE INTO records VALUES(?,?,?,?,?,?,?,?,?)",
            (r["id"], r["type"], r["text"], r["aspect"], r["trigger"], r["tier"],
             r.get("conflict_group"), r.get("source"), r.get("usage_count", 0)))
        con.execute(
            "INSERT OR REPLACE INTO vec_triggers VALUES(?,?,?,?)",
            (r["id"], r["aspect"], json.dumps(v), json.dumps(tokenize(r["trigger"]))))
    con.commit()
    n = con.execute("SELECT COUNT(*) FROM vec_triggers").fetchone()[0]
    con.close()
    print(f"[embed_store] backend={BACKEND} model={emb.name} dim={emb.dim} "
          f"records={len(recs)} stored={n} db={db_path}")


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_RECORDS
    build_store(path)
