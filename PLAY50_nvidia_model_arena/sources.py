"""데이터 소스 — mvp/research_Mvp 의 DB와 텍스트차트 모듈을 read-only 로 끌어온다.

절대 mvp 쪽에 쓰지 않는다(순수 조회). 경로는 환경변수 MVP_DIR 로 덮어쓸 수 있고,
기본값은 이 사용자의 research_Mvp 위치다.

제공:
    sample_news(window_hours, frac, cap)  → 최근 뉴스에서 랜덤 frac(35%) 제목 샘플
    fetch_bodies(url_hashes)              → article_contents 본문 (ok/short 만)
    active_watchlist(limit)               → open/partial 워치리스트 (tickers 파싱)
    text_chart(ticker)                    → module_text_chart 로 텍스트 차트(+메타/CHART_READ)
"""
from __future__ import annotations

import json
import os
import random
import re
import sqlite3
import sys
from pathlib import Path

MVP_DIR = Path(os.environ.get("MVP_DIR", r"C:\Users\fivep\OneDrive\Desktop\mvp\research_Mvp"))
NEWS_DB = MVP_DIR / "news_alert.db"
WL_DB = MVP_DIR / "watchlist.db"

_KR_CODE = re.compile(r"^\d{6}$")  # 한국 종목코드(6자리) → yfinance 는 .KS/.KQ 접미사 필요


def _connect(db: Path) -> sqlite3.Connection:
    if not db.exists():
        raise FileNotFoundError(f"DB 없음: {db}  (환경변수 MVP_DIR 로 경로 조정 가능)")
    # read-only URI — 원본을 절대 건드리지 않는다.
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def sample_news(window_hours: float = 4.0, frac: float = 0.35, cap: int = 150,
                seed: int | None = None) -> tuple[list[dict], dict]:
    """최근 window_hours 시간 안에 수집된 뉴스에서 랜덤 frac 비율의 제목을 뽑는다.

    (샘플 리스트, 통계 dict) 반환. 샘플이 cap 을 넘으면 cap 개로 무작위 축소하고
    통계에 dropped 를 남긴다(조용한 절단 금지).
    """
    conn = _connect(NEWS_DB)
    rows = conn.execute(
        "SELECT url_hash, title, source, summary, published_at, fetched_at "
        "FROM seen_news WHERE fetched_at >= datetime('now', ?) "
        "AND title IS NOT NULL AND title != '' ",
        (f"-{window_hours} hours",),
    ).fetchall()
    conn.close()

    pool = [dict(r) for r in rows]
    rng = random.Random(seed)
    rng.shuffle(pool)
    n_take = int(len(pool) * frac)
    sampled = pool[:n_take]
    dropped_by_cap = 0
    if len(sampled) > cap:
        dropped_by_cap = len(sampled) - cap
        sampled = sampled[:cap]
    stats = {
        "window_hours": window_hours,
        "pool_total": len(pool),
        "frac": frac,
        "sampled_before_cap": n_take,
        "cap": cap,
        "dropped_by_cap": dropped_by_cap,
        "used": len(sampled),
    }
    return sampled, stats


def fetch_bodies(url_hashes: list[str], max_chars: int = 1200) -> dict[str, str]:
    """중요 기사 본문을 article_contents 에서 가져온다. ok/short 상태만, 앞 max_chars 로 절단."""
    if not url_hashes:
        return {}
    conn = _connect(NEWS_DB)
    qmarks = ",".join("?" * len(url_hashes))
    rows = conn.execute(
        f"SELECT url_hash, body, status FROM article_contents "
        f"WHERE url_hash IN ({qmarks}) AND status IN ('ok','short') AND body IS NOT NULL",
        url_hashes,
    ).fetchall()
    conn.close()
    out = {}
    for r in rows:
        body = (r["body"] or "").strip()
        if body:
            out[r["url_hash"]] = body[:max_chars]
    return out


def active_watchlist(limit: int = 30) -> list[dict]:
    """open/partial 상태의 워치리스트. importance high 우선. tickers 는 JSON 배열 파싱."""
    conn = _connect(WL_DB)
    rows = conn.execute(
        "SELECT item, thesis, trigger_criteria, importance, tickers "
        "FROM watchlist WHERE status IN ('open','partial') "
        "ORDER BY CASE importance WHEN 'high' THEN 0 WHEN 'mid' THEN 1 ELSE 2 END, "
        "last_updated DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    out = []
    for r in rows:
        d = dict(r)
        try:
            d["tickers"] = json.loads(d["tickers"]) if d["tickers"] else []
        except (json.JSONDecodeError, TypeError):
            d["tickers"] = []
        out.append(d)
    return out


def _yf_symbol_candidates(ticker: str) -> list[str]:
    """한국 6자리 코드는 거래소를 모르니 .KS(코스피) → .KQ(코스닥) 순으로 시도."""
    if _KR_CODE.match(ticker):
        return [f"{ticker}.KS", f"{ticker}.KQ"]
    return [ticker]


def text_chart(ticker: str, cols: int = 80) -> str | None:
    """module_text_chart 로 텍스트 차트 + 메타데이터 + CHART_READ 를 만든다.

    실패하면 None (파이프라인이 멈추지 않게). 무거운 import(pandas/yfinance)는 여기서 lazy.
    """
    if str(MVP_DIR) not in sys.path:
        sys.path.insert(0, str(MVP_DIR))
    try:
        from module_text_chart import fetch_ohlcv, plot_combined_chart, generate_metadata
        from module_text_chart.metadata import generate_chart_read
    except Exception as e:  # 모듈 자체가 없으면 차트 없이 진행
        print(f"  [sources] text_chart import 실패: {e!r}", flush=True)
        return None

    for sym in _yf_symbol_candidates(ticker):
        try:
            df = fetch_ohlcv(sym)
            if df is None or df.empty:
                continue
            chart = plot_combined_chart(df, cols=cols)
            meta = generate_metadata(df)
            try:
                read = generate_chart_read(df)
            except Exception:
                read = "(CHART_READ 생성 실패)"
            return f"[{sym}]\n{chart}\n-- 메타 --\n{meta}\n-- CHART_READ --\n{read}"
        except Exception:
            continue
    return None
