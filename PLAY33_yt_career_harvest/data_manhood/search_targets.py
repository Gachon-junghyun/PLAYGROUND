# data_manhood/search_targets.py
"""지정한 '남성성 표본' 쿼리별로 유튜브 상위 후보를 뽑아 출력 (큐레이션용).
채널 발견(01)이 아니라, 내가 찍은 인물/캐릭터를 직접 검색해 후보 영상을 모은다.
큐는 직접 고른 video_id 로 build_queue 단계에서 만든다."""
from __future__ import annotations
import json, sys
from pathlib import Path
from yt_dlp import YoutubeDL

for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

QUERIES = [
    ("tom_cruise",   "톰 크루즈 직접 스턴트 프로의식"),
    ("tom_cruise2",  "톰 크루즈 노력 일화 미션임파서블"),
    ("tom_hardy",    "톰 하디 연기 베놈 워리어"),
    ("keanu",        "키아누 리브스 인성 일화 겸손"),
    ("john_wick",    "존 윅 캐릭터 분석 매력"),
    ("fight_club",   "파이트 클럽 타일러 더든 남성성 분석"),
    ("godfather",    "대부 비토 콜레오네 리더십 분석"),
    ("gladiator",    "글래디에이터 막시무스 명장면 분석"),
    ("dark_knight",  "다크나이트 배트맨 조커 분석"),
    ("wolverine",    "휴 잭맨 울버린 로건 분석"),
    ("no_country",   "노인을 위한 나라는 없다 안톤 시거 분석"),
    ("bond",         "제임스 본드 007 매력 분석"),
    ("madmax",       "매드맥스 분노의 도로 명장면 분석"),
    ("sinsegae",     "신세계 정청 황정민 명장면 분석"),
    ("bittersweet",  "달콤한 인생 이병헌 명장면 분석"),
    ("ahjussi",      "아저씨 원빈 차태식 명장면"),
    ("madongseok",   "마동석 범죄도시 카리스마"),
    ("interstellar", "인터스텔라 쿠퍼 아버지 부성애"),
]

def fmt_dur(s):
    if not s: return "?"
    s=int(s); return f"{s//60}:{s%60:02d}"

def main():
    opts={"extract_flat":True,"quiet":True,"skip_download":True,"ignoreerrors":True}
    rows=[]
    with YoutubeDL(opts) as ydl:
        for key,q in QUERIES:
            info=ydl.extract_info(f"ytsearch5:{q}",download=False)
            ents=[e for e in ((info or {}).get("entries") or []) if e and e.get("id")]
            print(f"\n### {key}  ::  {q}")
            for e in ents[:5]:
                dur=e.get("duration")
                print(f"  {e['id']}  [{fmt_dur(dur)}]  {(e.get('channel') or e.get('uploader') or '?')[:18]:18}  {e.get('title','?')[:60]}")
                rows.append({"key":key,"query":q,"video_id":e["id"],"title":e.get("title","?"),
                             "channel":e.get("channel") or e.get("uploader") or "?",
                             "duration":dur,"url":f"https://www.youtube.com/watch?v={e['id']}"})
    out=Path(__file__).resolve().parent/"search_candidates.jsonl"
    with out.open("w",encoding="utf-8") as f:
        for r in rows: f.write(json.dumps(r,ensure_ascii=False)+"\n")
    print(f"\n[OK] {len(rows)} candidates -> {out}")

if __name__=="__main__":
    main()
