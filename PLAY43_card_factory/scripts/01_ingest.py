"""PLAY43 INGEST — 인사이트 리포트를 *신규만* 수집해 data/inbox/<report_id>.txt 로.

핵심 원칙: 사건(event)이 아니라 분석가의 *사고*가 담긴 리포트만. 소스 어댑터 방식.

  python 01_ingest.py --source naver --list-only        # 목록/신규 분류만
  python 01_ingest.py --source naver --pages 1 --limit 1 # 신규 PDF→txt
  python 01_ingest.py --source seekingalpha --limit 1     # db 적재 SA 분석글→txt
  python 01_ingest.py --source inbox                      # data/inbox_pdf/ PDF·txt (수동)
  python 01_ingest.py --source youtube_en                 # 골격 — 명령만 출력(다음 턴)

원본 PLAY30 코드는 import 재사용(복붙 금지). 라이브 스크래핑은 naver PDF뿐 —
seekingalpha는 mvp news_alert.db 적재분만 읽는다(mvp-db-first).
"""
import argparse
import io
import re
import sqlite3
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # 재사용 원본(PLAY30) 폴더에 .pyc 안 남기기 — 원본 불변 유지
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import (
    PLAY30_DIR, PLAY33_DIR, NEWS_ALERT_DB, INBOX_DIR, INBOX_PDF_DIR, ensure_dirs,
)
import ingest_state as state


def _write_inbox(report_id, meta, body):
    ensure_dirs()
    header = "\n".join([
        f"# REPORT {report_id}",
        f"source: {meta.get('source', '')}",
        f"title: {meta.get('title', '')}",
        f"broker: {meta.get('broker', '')}",
        f"date: {meta.get('date', '')}",
        f"url: {meta.get('url', '')}",
        "", "---", "", "",
    ])
    out = INBOX_DIR / f"{report_id}.txt"
    out.write_text(header + body, encoding="utf-8")
    return out


def _pdf_bytes_to_text(data):
    try:
        from pdfminer.high_level import extract_text
    except ImportError:
        print("    [!] pdfminer.six 미설치 — pip install pdfminer.six")
        return ""
    try:
        return (extract_text(io.BytesIO(data)) or "").strip()
    except Exception as e:
        print(f"    pdf parse err: {e}")
        return ""


# ───────────────────────── naver ─────────────────────────
def ingest_naver(args):
    sys.path.insert(0, str(PLAY30_DIR))
    import naver_research_dl as nv  # PLAY30 재사용: fetch_html/parse_list/HEADERS/LIST_URL

    pages = _parse_pages(args)
    rows = []
    for pg in pages:
        print(f"=== naver page {pg} ===")
        rows.extend(nv.parse_list(nv.fetch_html(nv.LIST_URL, params={"page": pg})))

    def rid(r):
        return state.make_id(r.get("broker", ""), r.get("title", ""), r.get("date", ""))

    new_rows = [r for r in rows if not state.is_seen(rid(r))]
    print(f"[naver] 목록 {len(rows)}건 / 신규 {len(new_rows)}건")
    for r in rows:
        flag = "NEW " if not state.is_seen(rid(r)) else "seen"
        print(f"  [{flag}] {r.get('date',''):>10} | {r.get('broker',''):<12} | {r['title'][:48]}")
    if args.list_only:
        return

    import requests
    limit = args.limit or len(new_rows)
    done = 0
    for r in new_rows[:limit]:
        try:
            resp = requests.get(r["pdf_url"], headers=nv.HEADERS, timeout=60)
            resp.raise_for_status()
            body = _pdf_bytes_to_text(resp.content)
        except Exception as e:
            print(f"  [FAIL] download {r['title'][:40]}: {e}")
            continue
        if len(body) < 200:
            print(f"  [SKIP] 본문 빈약({len(body)}자): {r['title'][:40]}")
            continue
        rid_ = rid(r)
        meta = {"source": "naver", "title": r["title"], "broker": r.get("broker", ""),
                "date": r.get("date", ""), "url": r["pdf_url"]}
        out = _write_inbox(rid_, meta, body)
        state.mark_seen(rid_, "naver", r["title"], r.get("date", ""))
        print(f"  [OK] {out.name}  ({len(body)} chars)  {r['title'][:40]}")
        done += 1
    print(f"[naver] 신규 {done}건 inbox 적재")


# ─────────────────────── seekingalpha ───────────────────────
# 이벤트성 헤드라인(분석 아닌 사건 보도) 제외 패턴 — "인사이트만" 원칙
_EVENT_PAT = [
    "reports q", " q1 ", " q2 ", " q3 ", " q4 ", "earnings call", "to acquire",
    "declares dividend", "announces", "prices ", "completes", "to report",
    "schedules", "appoints", "names ceo", "stock split", "files for",
]


def ingest_seekingalpha(args):
    if not NEWS_ALERT_DB.exists():
        print(f"[seekingalpha] db 없음: {NEWS_ALERT_DB}")
        return
    con = sqlite3.connect(str(NEWS_ALERT_DB))
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute(
        """SELECT s.url_hash, s.url, s.title, s.fetched_at, c.body
           FROM seen_news s JOIN article_contents c ON s.url_hash = c.url_hash
           WHERE s.source = 'seekingalpha' AND length(c.body) > ?
           ORDER BY s.fetched_at DESC""",
        (args.min_body,),
    )
    rows = cur.fetchall()
    limit = args.limit or 5
    picked = []
    for row in rows:
        if state.is_seen(row["url_hash"]):
            continue
        title = (row["title"] or "").lower()
        if any(p in title for p in _EVENT_PAT):
            continue  # 이벤트 헤드라인 제외 → 분석글(thesis)만
        picked.append(row)
        if len(picked) >= limit:
            break
    print(f"[seekingalpha] 본문>{args.min_body} 후보 {len(rows)}건 / 신규 분석글 채택 {len(picked)}건")
    done = 0
    for row in picked:
        meta = {"source": "seekingalpha", "title": row["title"], "broker": "Seeking Alpha",
                "date": (row["fetched_at"] or "")[:10], "url": row["url"]}
        out = _write_inbox(row["url_hash"], meta, row["body"])
        state.mark_seen(row["url_hash"], "seekingalpha", row["title"] or "", (row["fetched_at"] or "")[:10])
        print(f"  [OK] {out.name}  ({len(row['body'])} chars)  {(row['title'] or '')[:50]}")
        done += 1
    print(f"[seekingalpha] 신규 {done}건 inbox 적재")


# ───────────────────────── inbox (골격) ─────────────────────────
def ingest_inbox(args):
    ensure_dirs()
    files = sorted(list(INBOX_PDF_DIR.glob("*.pdf")) + list(INBOX_PDF_DIR.glob("*.txt")))
    if not files:
        print(f"[inbox] {INBOX_PDF_DIR} 비어 있음 — IB 리포트 PDF/txt를 드롭하고 재실행 (골격)")
        return
    done = 0
    for f in files:
        rid_ = state.make_id(f.name)
        if state.is_seen(rid_):
            print(f"  [seen] {f.name}")
            continue
        if f.suffix.lower() == ".pdf":
            body = _pdf_bytes_to_text(f.read_bytes())
        else:
            body = f.read_text(encoding="utf-8", errors="ignore").strip()
        if len(body) < 200:
            print(f"  [SKIP] 본문 빈약: {f.name}")
            continue
        meta = {"source": "inbox", "title": f.stem, "date": "", "url": str(f)}
        out = _write_inbox(rid_, meta, body)
        state.mark_seen(rid_, "inbox", f.stem)
        print(f"  [OK] {out.name}  ({len(body)} chars)")
        done += 1
    print(f"[inbox] 신규 {done}건 inbox 적재")


# ───────────────────────── youtube (골격) ─────────────────────────
def ingest_youtube(args):
    lang = "en" if args.source == "youtube_en" else "ko"
    topic = f"analyst_research_{lang}"
    kw = ('"증권사 리서치 시장 전망 애널리스트"' if lang == "ko"
          else '"equity research analyst market outlook stock thesis"')
    match = ("전망,밸류,실적,목표주가,리포트,섹터" if lang == "ko"
             else "thesis,valuation,earnings,outlook,downgrade,upgrade")
    print(f"[youtube_{lang}] 골격 — 다음 턴 실행. PLAY33 파이프라인 (GPU Whisper 필요):")
    print(f"  $env:PLAY33_TOPIC = '{topic}'")
    print(f"  python {PLAY33_DIR}\\scripts\\01_discover.py {kw} --min-subs 50000")
    print(f"  python {PLAY33_DIR}\\scripts\\02_fetch.py --from-channels data_{topic}\\channels.jsonl -n 40 --match \"{match}\" --keep 8")
    print(f"  python {PLAY33_DIR}\\scripts\\03_pipeline.py --language {lang}")
    print(f"  → 전사된 transcripts/*.txt 를 cardify (orchestrator.md Step 2와 동일 경로)")


def _parse_pages(args):
    if getattr(args, "pages", None):
        m = re.fullmatch(r"(\d+)-(\d+)", args.pages.strip())
        if m:
            return list(range(int(m.group(1)), int(m.group(2)) + 1))
    return [getattr(args, "page", 1)]


def main():
    ap = argparse.ArgumentParser(description="PLAY43 인사이트 리포트 증분 수집")
    ap.add_argument("--source", required=True,
                    choices=["naver", "seekingalpha", "inbox", "youtube_kr", "youtube_en"])
    ap.add_argument("--list-only", action="store_true", help="naver: 목록/신규 분류만")
    ap.add_argument("--page", type=int, default=1)
    ap.add_argument("--pages", default=None, help="예: 1-3")
    ap.add_argument("--limit", type=int, default=None, help="신규 N건만 처리")
    ap.add_argument("--min-body", type=int, default=1500, help="seekingalpha 본문 최소 길이")
    args = ap.parse_args()
    ensure_dirs()
    {"naver": ingest_naver, "seekingalpha": ingest_seekingalpha, "inbox": ingest_inbox,
     "youtube_kr": ingest_youtube, "youtube_en": ingest_youtube}[args.source](args)


if __name__ == "__main__":
    main()
