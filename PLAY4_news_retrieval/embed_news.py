"""뉴스 본문 → gemini-embedding-001 임베딩 → article_embeddings 테이블에 추가.

incremental: 이미 article_embeddings 에 있는 url_hash 는 스킵. 따라서 같은 명령으로
여러 번 돌려도 중복 호출 없음. 새로 추가된 뉴스도 다음 실행 때 자동으로 잡힌다.

선택 기준: 본문이 비어있지 않은 뉴스 중 RANDOM() 으로 N 개 (시드 고정으로 재현 가능).
이유는 README "가정 & 제약" 참고.
"""
from __future__ import annotations

import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
DB_PATH = HERE / "data" / "news_alert.db"
DOTENV_PATH = HERE / ".env"

EMBED_MODEL = "gemini-embedding-001"
EMBED_DIM = 3072
TRUNCATE_CHARS = 8000           # 8K 토큰 한도 보수적 추정
SLEEP_BETWEEN = 0.10            # 호출 간 sleep (초). 25 RPS 한도 안쪽.
RETRY_DELAYS = [10, 30, 60, 120]
PROGRESS_EVERY = 50             # 몇 건마다 진행 라인 찍을지
RNG_SEED = 20260508             # 재현성. SQL 의 RANDOM() 시드.


def _load_env():
    """간단 .env 파서 — python-dotenv 없이도 동작."""
    if not DOTENV_PATH.exists():
        return
    for line in DOTENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


def _get_client():
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY 가 .env 에서 로드되지 않음.")
    from google import genai
    return genai.Client(api_key=api_key)


def _is_rate_limit(e: Exception) -> bool:
    s = str(e).lower()
    return any(k in s for k in ("429", "resource_exhausted", "quota", "rate limit", "rate_limit"))


def _is_transient(e: Exception) -> bool:
    s = str(e).lower()
    return any(k in s for k in ("500", "502", "503", "504", "unavailable", "deadline", "timeout"))


def embed_one(client, text: str) -> np.ndarray:
    """단건 임베딩 + 재시도. mvp/module_embedding/_client.py 패턴 따름."""
    from google.genai import types
    last = None
    for attempt in range(len(RETRY_DELAYS) + 1):
        try:
            r = client.models.embed_content(
                model=EMBED_MODEL,
                contents=text,
                config=types.EmbedContentConfig(task_type="SEMANTIC_SIMILARITY"),
            )
            obj = r.embeddings[0] if hasattr(r, "embeddings") else r.embedding
            vals = obj.values if hasattr(obj, "values") else list(obj)
            return np.array(list(vals), dtype=np.float32)
        except Exception as e:
            last = e
            retryable = _is_rate_limit(e) or _is_transient(e)
            if attempt >= len(RETRY_DELAYS) or not retryable:
                break
            delay = RETRY_DELAYS[attempt]
            tag = "rate_limit" if _is_rate_limit(e) else "transient"
            print(f"  [retry {attempt+1}/{len(RETRY_DELAYS)}] {tag}: {delay}s 대기 ({e})", flush=True)
            time.sleep(delay)
    raise last


def select_pending(con: sqlite3.Connection, target_total: int) -> list[tuple[str, str]]:
    """이미 임베딩된 것을 제외하고, 부족한 만큼 무작위로 골라 반환.

    Returns: [(url_hash, body), ...]
    """
    cur = con.cursor()
    already = cur.execute("SELECT COUNT(*) FROM article_embeddings").fetchone()[0]
    need = max(0, target_total - already)
    print(f"[select] already={already}, target_total={target_total}, need={need}", flush=True)
    if need <= 0:
        return []
    rows = cur.execute(
        """
        SELECT ac.url_hash, ac.body
        FROM article_contents ac
        LEFT JOIN article_embeddings ae ON ac.url_hash = ae.url_hash
        WHERE ae.url_hash IS NULL
          AND ac.body IS NOT NULL
          AND length(ac.body) > 0
        ORDER BY (substr(ac.url_hash, 1, 8))   -- url_hash 의 앞 8 hex 로 의사-RANDOM 정렬, 재현성 있음
        LIMIT ?
        """,
        (need,),
    ).fetchall()
    return rows


def main():
    if len(sys.argv) < 2:
        print("Usage: python embed_news.py <target_total> [--dry-run]", flush=True)
        sys.exit(2)
    target = int(sys.argv[1])
    dry = "--dry-run" in sys.argv

    print(f"[start] target_total={target} dry={dry} db={DB_PATH}", flush=True)
    _load_env()

    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA journal_mode=WAL")
    pending = select_pending(con, target)
    if not pending:
        print("[done] 추가 임베딩할 항목 없음.", flush=True)
        print("DONE", flush=True)
        return

    if dry:
        # 5건만 임베딩해보고 끝
        pending = pending[:5]
        print(f"[dry] 처음 {len(pending)} 건만 처리", flush=True)

    try:
        client = _get_client()
    except Exception as e:
        print(f"FAILED: client init: {e}", flush=True)
        sys.exit(1)

    cur = con.cursor()
    ok = 0
    failed = 0
    t0 = time.time()
    for i, (url_hash, body) in enumerate(pending, 1):
        text = body[:TRUNCATE_CHARS]
        try:
            vec = embed_one(client, text)
        except Exception as e:
            failed += 1
            print(f"  [skip] {url_hash[:8]}: {e}", flush=True)
            time.sleep(SLEEP_BETWEEN)
            continue
        if vec.shape[0] != EMBED_DIM:
            failed += 1
            print(f"  [skip] {url_hash[:8]}: dim={vec.shape[0]} 예상={EMBED_DIM}", flush=True)
            continue
        cur.execute(
            "INSERT OR REPLACE INTO article_embeddings "
            "(url_hash, embedding, embed_model, embed_dim, embedded_at) "
            "VALUES (?,?,?,?,?)",
            (
                url_hash,
                vec.tobytes(),
                EMBED_MODEL,
                EMBED_DIM,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        ok += 1
        if ok % PROGRESS_EVERY == 0 or i == len(pending):
            con.commit()
            elapsed = time.time() - t0
            rate = ok / elapsed if elapsed > 0 else 0
            remain = (len(pending) - i) / rate if rate > 0 else -1
            print(
                f"[progress] {i}/{len(pending)}  ok={ok} fail={failed}  "
                f"{rate:.1f}/s  ETA={remain:.0f}s",
                flush=True,
            )
        time.sleep(SLEEP_BETWEEN)

    con.commit()
    con.close()
    elapsed = time.time() - t0
    print(f"[summary] ok={ok} fail={failed} elapsed={elapsed:.1f}s", flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"FAILED: {e}", flush=True)
        sys.exit(1)
