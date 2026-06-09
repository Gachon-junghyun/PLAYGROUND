# data_maturity/search_targets2.py
"""보충 수확: 1차 코퍼스가 '마음 다스리기'에 쏠려 비어버린 축
— 책임·주체성·실행·자립(행동하는 어른) — 을 타게팅 검색.
스트레스테스트가 9개 상황 전부에서 지적한 '행동 절반'의 공백을 코퍼스로 메우려는 것."""
from __future__ import annotations
import json, sys
from pathlib import Path
from yt_dlp import YoutubeDL

for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

QUERIES = [
    ("responsibility", "책임감 있는 사람 특징 자기 삶을 책임진다"),
    ("ownership",      "주체적인 삶 내 인생의 주인으로 사는 법"),
    ("no_excuse",     "변명하지 않는 사람 핑계 대지 않기"),
    ("keep_promise",  "약속을 지키는 사람 신뢰받는 사람 일관성"),
    ("decision",      "결단력 결정 잘하는 법 우유부단 극복"),
    ("execution",     "미루지 않고 실행하는 사람 실행력 행동력"),
    ("self_reliance", "경제적 자립 독립 어른 홀로서기"),
    ("consistency",   "꾸준함 성실함 루틴 자기관리 자기규율"),
    ("grit_endure",   "묵묵히 견디며 책임 다하는 어른 가장"),
    ("professional",  "프로페셔널 직업의식 일에 대한 책임감"),
    ("adversity",     "역경 책임지고 헤쳐나가는 사람 위기 대처"),
    ("integrity",     "신뢰 정직 말과 행동이 일치하는 사람"),
]

def fmt_dur(s):
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
                dur=e.get("duration")
                print(f"  {e['id']}  [{fmt_dur(dur)}]  {(e.get('channel') or e.get('uploader') or '?')[:20]:20}  {e.get('title','?')[:55]}")
                rows.append({"key":key,"query":q,"video_id":e["id"],"title":e.get("title","?"),
                             "channel":e.get("channel") or e.get("uploader") or "?",
                             "duration":dur,"url":f"https://www.youtube.com/watch?v={e['id']}"})
    out=Path(__file__).resolve().parent/"search_candidates2.jsonl"
    with out.open("w",encoding="utf-8") as f:
        for r in rows: f.write(json.dumps(r,ensure_ascii=False)+"\n")
    print(f"\n[OK] {len(rows)} candidates -> {out}")

if __name__=="__main__":
    main()
