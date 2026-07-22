# data_yooseyoon/search_targets.py
"""유세윤 코미디의 여러 결을 직접 ytsearch로 겨냥해 후보 영상을 수집 (큐레이션용).
채널 발견(01)이 아니라 '유세윤'이라는 특정 인물을 facet별로 검색해 후보를 모은다.
큐는 메인이 직접 고른 video_id 로 build_queue 단계에서 만든다."""
from __future__ import annotations
import json, sys
from pathlib import Path
from yt_dlp import YoutubeDL

for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

# facet: 그가 웃기는 '결'을 골고루 — 애드립/순발력, UV 음악개그, 콩트/캐릭터,
# 토크 입담, 자학·능청, 코미디 철학 인터뷰(사고방식 골드), 최근 유튜브.
QUERIES = [
    ("muhandojeon",  "유세윤 무한도전 레전드 웃긴장면"),
    ("radiostar",    "유세윤 라디오스타 애드립 입담"),
    ("uv_stage",     "UV 유세윤 뮤지 노래 무대 라이브"),
    ("uv_video",     "UV 비됴 유세윤 뮤직비디오 패러디"),
    ("gagcon",       "유세윤 개그콘서트 콩트 레전드"),
    ("adlib",        "유세윤 즉흥 애드립 드립 모음"),
    ("comedy_phil",  "유세윤 인터뷰 개그 코미디 철학 웃기는법"),
    ("talkshow",     "유세윤 토크쇼 입담 썰 라디오"),
    ("witty",        "유세윤 받아치기 순발력 센스 드립"),
    ("sketchbook",   "유세윤 유희열의 스케치북 UV 무대"),
    ("character",    "유세윤 큐그라더 캐릭터 성대모사"),
    ("recent_yt",    "유세윤 유튜브 채널 최근 예능"),
    ("kkagang",      "유세윤 쿨까당 토크 웃긴"),
    ("lagginam",     "유세윤 라끼남 나영석 케미"),
    ("selfdep",      "유세윤 자학 능청 디스 개그"),
    ("yooquiz",      "유세윤 유 퀴즈 온 더 블럭"),
    ("variety_cut",  "유세윤 예능 레전드 웃긴 모음"),
    ("standup",      "유세윤 스탠드업 코미디 만담"),
]

def fmt_dur(s):
    if not s: return "?"
    s=int(s); return f"{s//60}:{s%60:02d}"

def main():
    opts={"extract_flat":True,"quiet":True,"skip_download":True,"ignoreerrors":True}
    rows=[]
    with YoutubeDL(opts) as ydl:
        for key,q in QUERIES:
            try:
                info=ydl.extract_info(f"ytsearch5:{q}",download=False)
            except Exception as e:
                print(f"\n### {key}  ::  {q}  -> ERR {e!r}", flush=True); continue
            ents=[e for e in ((info or {}).get("entries") or []) if e and e.get("id")]
            print(f"\n### {key}  ::  {q}", flush=True)
            for e in ents[:5]:
                dur=e.get("duration")
                ch=(e.get("channel") or e.get("uploader") or "?")
                print(f"  {e['id']}  [{fmt_dur(dur):>6}]  {ch[:20]:20}  {e.get('title','?')[:55]}", flush=True)
                rows.append({"key":key,"query":q,"video_id":e["id"],"title":e.get("title","?"),
                             "channel":ch,"duration":dur,
                             "url":f"https://www.youtube.com/watch?v={e['id']}"})
    out=Path(__file__).resolve().parent/"search_candidates.jsonl"
    with out.open("w",encoding="utf-8") as f:
        for r in rows: f.write(json.dumps(r,ensure_ascii=False)+"\n")
    print(f"\n[OK] {len(rows)} candidates -> {out}", flush=True)
    print("DONE", flush=True)

if __name__=="__main__":
    main()
