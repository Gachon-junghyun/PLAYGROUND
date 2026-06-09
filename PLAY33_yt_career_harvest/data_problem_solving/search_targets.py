# data_problem_solving/search_targets.py
"""문제해결능력/사고력 쿼리별로 유튜브 상위 후보를 뽑아 출력 (큐레이션용).
채널 발견(01)의 최신영상 한계(문제해결 제목이 최근 업로드에 안 묻음)를 우회 —
주제의 여러 결을 직접 검색해 후보를 모은다. 큐는 큐레이션 후 build_queue로 만든다."""
from __future__ import annotations
import json, sys
from pathlib import Path
from yt_dlp import YoutubeDL

for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

QUERIES = [
    ("define",     "문제 정의 본질 파악 문제 해결"),
    ("framework",  "문제 해결 프레임워크 로직트리 MECE"),
    ("hypothesis", "가설 사고 컨설턴트 문제 해결"),
    ("mckinsey",   "맥킨지 문제 해결 방식 사고법"),
    ("logical",    "논리적 사고력 기르는 법"),
    ("metacog",    "메타인지 공부법 사고력"),
    ("workhead",   "일 잘하는 사람 문제 해결 사고방식"),
    ("decision",   "의사결정 잘하는 법 판단력"),
    ("structure",  "생각 정리 구조화 사고법"),
    ("critical",   "비판적 사고 크리티컬 씽킹"),
    ("firstprin",  "제1원리 사고 본질부터 생각하기"),
    ("steps",      "문제 해결 5단계 절차 방법"),
    ("creative",   "창의적 문제 해결 발상법"),
    ("simplify",   "복잡한 문제 단순화 분해"),
    ("polya",      "수학 문제 푸는 사고력 문제 해결 전략"),
    ("planning",   "기획력 문제 해결 기획서 잘 쓰는 법"),
    ("thinktool",  "생각의 도구 사고 프레임 똑똑하게"),
    ("rootcause",  "근본 원인 분석 왜 5번 문제 해결"),
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
                print(f"  {e['id']}  [{fmt_dur(dur)}]  {(e.get('channel') or e.get('uploader') or '?')[:16]:16}  {e.get('title','?')[:58]}")
                rows.append({"key":key,"query":q,"video_id":e["id"],"title":e.get("title","?"),
                             "channel":e.get("channel") or e.get("uploader") or "?",
                             "duration":dur,"url":f"https://www.youtube.com/watch?v={e['id']}"})
    out=Path(__file__).resolve().parent/"search_candidates.jsonl"
    with out.open("w",encoding="utf-8") as f:
        for r in rows: f.write(json.dumps(r,ensure_ascii=False)+"\n")
    print(f"\n[OK] {len(rows)} candidates -> {out}")

if __name__=="__main__":
    main()
