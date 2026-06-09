# data_manhood/search_targets2.py  — 2차 검색 (빈/약한 표본 보강 + 보너스 아이콘)
from __future__ import annotations
import json, sys
from pathlib import Path
from yt_dlp import YoutubeDL
for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

QUERIES = [
    ("keanu",      "키아누 리브스 일화 존경 이유 인성"),
    ("ahjussi",    "영화 아저씨 원빈 분석 리뷰 명작"),
    ("yeongung",   "영웅본색 주윤발 마크 분석 명장면"),
    ("rocky",      "록키 발보아 실베스터 스탤론 명대사 인생"),
    ("braveheart", "브레이브하트 윌리엄 월레스 분석"),
    ("madongseok", "마동석 액션 스타일 분석 매력"),
]
def fmt(s):
    if not s: return "?"
    s=int(s); return f"{s//60}:{s%60:02d}"
def main():
    opts={"extract_flat":True,"quiet":True,"skip_download":True,"ignoreerrors":True}
    rows=[]
    with YoutubeDL(opts) as ydl:
        for key,q in QUERIES:
            info=ydl.extract_info(f"ytsearch6:{q}",download=False)
            ents=[e for e in ((info or {}).get("entries") or []) if e and e.get("id")]
            print(f"\n### {key}  ::  {q}")
            for e in ents[:6]:
                print(f"  {e['id']}  [{fmt(e.get('duration'))}]  {(e.get('channel') or e.get('uploader') or '?')[:18]:18}  {e.get('title','?')[:60]}")
                rows.append({"key":key,"video_id":e["id"],"title":e.get("title","?"),
                             "channel":e.get("channel") or e.get("uploader") or "?",
                             "duration":e.get("duration"),"url":f"https://www.youtube.com/watch?v={e['id']}"})
    out=Path(__file__).resolve().parent/"search_candidates2.jsonl"
    with out.open("w",encoding="utf-8") as f:
        for r in rows: f.write(json.dumps(r,ensure_ascii=False)+"\n")
    print(f"\n[OK] {len(rows)} -> {out}")
if __name__=="__main__": main()
