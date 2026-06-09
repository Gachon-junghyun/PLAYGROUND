# data_maturity/search_targets.py
"""'어른스러움(성숙함)' 코퍼스 큐레이션용 ytsearch 타게팅.
채널 발견(01)이 아니라 성숙함의 여러 결(감정조절·책임·현실수용·관계성숙·
자기객관화·절제·관용)을 직접 검색해 후보 영상을 모은다. 큐는 큐레이션으로 고른다."""
from __future__ import annotations
import json, sys
from pathlib import Path
from yt_dlp import YoutubeDL

for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

QUERIES = [
    ("definition",   "성숙한 사람과 미성숙한 사람 차이 특징"),
    ("real_adult",   "진짜 어른 어른스러움이란 무엇인가"),
    ("emotion",      "감정조절 화 다스리는 법 심리학"),
    ("anger",        "욱하는 성격 분노 다스리기"),
    ("byeop_anger",  "법륜스님 즉문즉설 화 분노 미움"),
    ("byeop_relation","법륜스님 즉문즉설 인간관계 갈등 서운함"),
    ("resilience",   "김주환 회복탄력성 감정조절 내면소통"),
    ("acceptance",   "현실 받아들이기 수용 마음 내려놓기"),
    ("stoic",        "스토아 철학 평정심 통제할 수 없는 것"),
    ("chungco",      "충코의 철학 마음 평정심 고통"),
    ("responsibility","남탓 그만 책임지는 어른 주체성"),
    ("self_esteem",  "윤홍균 자존감 감정 휘둘리지 않기"),
    ("kimchangok",   "김창옥 관계 상처 마음"),
    ("psychiatrist", "정신과의사 마음 그릇 성숙 감정"),
    ("metacog",      "자기객관화 미성숙 알아채기 메타인지"),
    ("restraint",    "절제 인내 만족지연 충동 다스리기"),
    ("unfair",       "억울할 때 비난받을 때 마음 대처법"),
    ("listen",       "타인 존중 경청 성숙한 대화 태도"),
    ("grit_calm",    "흔들리지 않는 단단한 멘탈 평정심"),
    ("forgive",      "용서 너그러움 미워하지 않기 마음"),
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
    out=Path(__file__).resolve().parent/"search_candidates.jsonl"
    with out.open("w",encoding="utf-8") as f:
        for r in rows: f.write(json.dumps(r,ensure_ascii=False)+"\n")
    print(f"\n[OK] {len(rows)} candidates -> {out}")

if __name__=="__main__":
    main()
