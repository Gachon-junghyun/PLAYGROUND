"""Hindsight 서버 — FastAPI 앱 (content interning + segment 모델, LLM 없음).

화면 텍스트를 받아 쌓되, 같은 내용은 한 번만 저장(contents)하고 '언제 봤나'만
세그먼트로 남긴다. 지속(계속 떠 있음)은 한 세그먼트에 count 로 접히고, 갭을 넘긴
재방문은 새 세그먼트가 된다. 앱/주제/시간/재방문 태그를 붙여 돌려준다.
요약·질의응답 같은 '생각'은 점심/저녁에 접근하는 Claude 루틴이 한다.

엔드포인트:
  POST /captures      배치 수신·멱등 저장(+ 지속 접기)
  GET  /timeline      윈도우 세그먼트를 시간순 + 앱/주제/시간/재방문/dwell 태그
  GET  /breakdown     윈도우 집계: 앱별·주제별·시간대별 + 재방문 비율
  GET  /search        키워드(LIKE) 검색 + 앱/주제/시간 필터 + 등장 정보
  GET  /history       특정 내용이 과거 언제·얼마나 보였는지(그래프 노드 이력)
  POST /reload-rules  rules.json 무중단 재적용
  GET  /health        카운트(중복 제거 전후)·기간·버킷/주제 목록
"""
import asyncio
import time
from datetime import datetime, timezone

from fastapi import FastAPI, Header, HTTPException, Query, Request

import config
import db
import tagging

app = FastAPI(title="Hindsight Server (interned segments)")


@app.on_event("startup")
def _startup():
    db.init_db()
    tagging.load_rules()
    print("[hindsight] up. apps=%s topics=%s" % (tagging.app_names(), tagging.topic_names()))


# --------------------------------------------------------------------------- #
# 인증 / 윈도우
# --------------------------------------------------------------------------- #
def check_auth(authorization):
    if not config.TOKEN:
        raise HTTPException(503, "server token not configured: set HINDSIGHT_TOKEN")
    if authorization != f"Bearer {config.TOKEN}":
        raise HTTPException(401, "invalid or missing bearer token")


def _now():
    return int(time.time())


def _day_bounds(date_str):
    d = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    start = int(d.timestamp()) - config.TZ_OFFSET_HOURS * 3600
    return start, start + 86400


def _resolve_window(date, from_, to):
    if date:
        try:
            return _day_bounds(date)
        except ValueError:
            raise HTTPException(400, "date must be YYYY-MM-DD")
    if from_ is not None or to is not None:
        return (from_ if from_ is not None else 0, to if to is not None else _now() + 1)
    return _day_bounds(tagging.local_dt(_now()).strftime("%Y-%m-%d"))


# --------------------------------------------------------------------------- #
# 세그먼트 태깅
# --------------------------------------------------------------------------- #
def _tag_segment(r, window_start=None, recall_map=None):
    bucket, topic = tagging.classify_capture(r["front_app"], r["text"])
    obj = {
        "ts": r["first_ts"],
        "first": tagging.local_dt(r["first_ts"]).strftime("%Y-%m-%d %H:%M"),
        "last": tagging.local_dt(r["last_ts"]).strftime("%H:%M"),
        "duration_sec": max(0, r["last_ts"] - r["first_ts"]),  # 화면에 떠 있던 길이
        "count": r["count"],                                   # 관측 횟수(dwell)
        "period": tagging.period_of(r["first_ts"]),
        "app": r["front_app"],
        "bucket": bucket,
        "topic": topic,
        "text": r["text"],
        "x": r["x"],
        "y": r["y"],
    }
    if recall_map is not None:
        rc = recall_map.get(r["content_id"])
        if rc:
            obj["recall"] = {
                "first_seen": rc["fs"],
                "times_seen": rc["n_seg"],     # 갭으로 나뉜 등장 이벤트 수
                "total_count": rc["total"],    # 누적 관측(전체 dwell)
                "revisit": rc["n_seg"] > 1 or (window_start is not None and rc["fs"] < window_start),
            }
    return obj


# --------------------------------------------------------------------------- #
# 엔드포인트
# --------------------------------------------------------------------------- #
@app.post("/captures")
async def post_captures(request: Request, authorization: str = Header(None)):
    check_auth(authorization)
    body = await request.json()
    if not isinstance(body, list):
        raise HTTPException(400, "body must be a JSON array of captures")
    return await asyncio.to_thread(db.insert_capture_batch, body)


@app.get("/timeline")
async def get_timeline(
    date: str = Query(None),
    from_: int = Query(None, alias="from"),
    to: int = Query(None, alias="to"),
    app_f: str = Query(None, alias="app"),
    topic: str = Query(None),
    limit: int = Query(config.TIMELINE_MAX_LINES),
    authorization: str = Header(None),
):
    check_auth(authorization)
    start, end = _resolve_window(date, from_, to)
    rows = await asyncio.to_thread(db.fetch_range, start, end, config.TIMELINE_MAX_LINES)
    recall = await asyncio.to_thread(db.content_recall, [r["content_id"] for r in rows])

    out, blob, chars = [], [], 0
    for r in rows:
        obj = _tag_segment(r, start, recall)
        if app_f and obj["bucket"] != app_f:
            continue
        if topic and obj["topic"] != topic:
            continue
        out.append(obj)
        if chars < config.TEXT_BLOB_MAX_CHARS:
            dwell = f"×{obj['count']}" if obj["count"] > 1 else ""
            mark = "↻" if obj.get("recall", {}).get("revisit") else " "
            piece = f"{obj['first'][11:]} [{obj['bucket']}/{obj['topic']}]{mark} {r['text']} {dwell}".rstrip()
            blob.append(piece)
            chars += len(piece)
        if len(out) >= limit:
            break
    return {
        "from": start, "to": end, "count": len(out),
        "truncated": len(rows) >= config.TIMELINE_MAX_LINES,
        "text": "\n".join(blob), "segments": out,
    }


@app.get("/breakdown")
async def get_breakdown(
    date: str = Query(None),
    from_: int = Query(None, alias="from"),
    to: int = Query(None, alias="to"),
    authorization: str = Header(None),
):
    check_auth(authorization)
    start, end = _resolve_window(date, from_, to)
    rows = await asyncio.to_thread(db.fetch_range, start, end, config.BREAKDOWN_MAX_LINES)
    recall = await asyncio.to_thread(db.content_recall, [r["content_id"] for r in rows])

    by_app, by_topic, by_period = {}, {}, {}
    revisit = observations = 0
    for r in rows:
        bucket, tp = tagging.classify_capture(r["front_app"], r["text"])
        by_app[bucket] = by_app.get(bucket, 0) + 1
        by_topic[tp] = by_topic.get(tp, 0) + 1
        p = tagging.period_of(r["first_ts"])
        by_period[p] = by_period.get(p, 0) + 1
        observations += r["count"]
        rc = recall.get(r["content_id"])
        if rc and rc["fs"] < start:
            revisit += 1
    total = len(rows)  # 세그먼트(고유 등장) 수 — 중복 제거된 '활동 건수'
    return {
        "from": start, "to": end,
        "segments": total,            # 중복 제거된 등장 수
        "observations": observations,  # 원시 관측 합(접기 전 규모)
        "truncated": total >= config.BREAKDOWN_MAX_LINES,
        "by_app": by_app, "by_topic": by_topic, "by_period": by_period,
        "revisit_segments": revisit,
        "revisit_ratio": round(revisit / total, 3) if total else 0.0,
    }


@app.get("/search")
async def get_search(
    q: str = Query(...),
    limit: int = Query(config.SEARCH_DEFAULT_LIMIT),
    from_: int = Query(None, alias="from"),
    to: int = Query(None, alias="to"),
    app_f: str = Query(None, alias="app"),
    topic: str = Query(None),
    authorization: str = Header(None),
):
    check_auth(authorization)
    rows = await asyncio.to_thread(db.search_segments, q, from_, to, max(limit * 4, 200))
    recall = await asyncio.to_thread(db.content_recall, [r["content_id"] for r in rows])
    out = []
    for r in rows:
        obj = _tag_segment(r, None, recall)
        if app_f and obj["bucket"] != app_f:
            continue
        if topic and obj["topic"] != topic:
            continue
        out.append(obj)
        if len(out) >= limit:
            break
    return {"results": out}


@app.get("/history")
async def get_history(
    q: str = Query(...),
    limit: int = Query(30),
    authorization: str = Header(None),
):
    """q 매칭 내용이 과거 언제·얼마나 보였는지. 같은 content 의 세그먼트 = 등장 이력."""
    check_auth(authorization)
    contents = await asyncio.to_thread(db.search_contents, q, limit)
    ids = [c["id"] for c in contents]
    segs = await asyncio.to_thread(db.segments_for_contents, ids)
    nodes = []
    for c in contents:
        events = segs.get(c["id"], [])
        if not events:
            continue
        nodes.append({
            "text": c["text"],
            "times_seen": len(events),                       # 등장 이벤트 수
            "total_count": sum(e[2] for e in events),        # 누적 관측(dwell)
            "first_seen": tagging.local_dt(events[0][0]).strftime("%Y-%m-%d %H:%M"),
            "last_seen": tagging.local_dt(events[-1][1]).strftime("%Y-%m-%d %H:%M"),
            "occurrences": [
                {"first": tagging.local_dt(fs).strftime("%Y-%m-%d %H:%M"),
                 "last": tagging.local_dt(ls).strftime("%H:%M"),
                 "count": cnt, "period": tagging.period_of(fs),
                 "app": tagging.app_bucket(ap, "")}
                for fs, ls, cnt, ap in events
            ],
        })
    nodes.sort(key=lambda x: x["total_count"], reverse=True)
    return {"nodes": nodes}


@app.post("/reload-rules")
async def post_reload_rules(authorization: str = Header(None)):
    check_auth(authorization)
    try:
        tagging.load_rules()
    except Exception as e:
        raise HTTPException(400, f"rules.json load failed: {type(e).__name__}: {e}")
    return {"ok": True, "apps": tagging.app_names(), "topics": tagging.topic_names()}


@app.get("/health")
async def get_health(authorization: str = Header(None)):
    check_auth(authorization)
    s = await asyncio.to_thread(db.stats)
    dedup = round(1 - s["contents"] / s["observations"], 3) if s["observations"] else 0.0
    return {
        "status": "ok",
        "captures": s["captures"],
        "contents": s["contents"],          # 고유 내용 수(interning 후)
        "segments": s["segments"],          # 등장 이벤트 수
        "observations": s["observations"],  # 접기 전 원시 관측 수
        "text_dedup_ratio": dedup,          # 텍스트 중복 절감률
        "span": {"from": s["ts_min"], "to": s["ts_max"]},
        "apps": tagging.app_names(),
        "topics": tagging.topic_names(),
        "db": config.DB_PATH,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=config.HOST, port=config.PORT)
