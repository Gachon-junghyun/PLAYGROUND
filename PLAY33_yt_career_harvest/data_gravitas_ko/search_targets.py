# data_gravitas_ko/search_targets.py
"""'무시받지 않는 위엄·무게감' KO 코퍼스 큐레이션용 ytsearch 타게팅.
4원형(협상·레버리지 / 프레임·권력·이미지 / 카리스마·존재감 / 경계·도발대응)을
한국 화법·협상·이미지·자존감 코치 각도로 직접 겨냥. 채널발견(01) 아니라 표본 역추출용.
인접 회전(data_hogu_ko 호구탈출·data_manhood 존재감)과 겹칠 수 있음 — 각도(위엄·협상·프레임) 다름.
큐는 큐레이션으로 고른다."""
from __future__ import annotations
import json, sys
from pathlib import Path
from yt_dlp import YoutubeDL

for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

# (archetype, key, query)  archetype: nego/frame/charisma/boundary
QUERIES = [
    ("nego",     "nego_skill",   "협상 잘하는 법 상대를 움직이는 협상의 기술"),
    ("nego",     "nego_biz",     "비즈니스 협상 전략 이기는 협상법 강의"),
    ("nego",     "nego_voss",    "협상의 신 크리스 보스 설득 협상 심리"),
    ("nego",     "leverage_ko",  "원하는 것을 얻어내는 대화 협상 주도권"),
    ("frame",    "power_law",    "권력의 법칙 로버트 그린 핵심 정리"),
    ("frame",    "persuasion",   "설득의 심리학 치알디니 사람 움직이는 법"),
    ("frame",    "frame_grab",   "프레임 장악 대화 주도권 가져오는 법"),
    ("frame",    "image_make",   "이미지메이킹 첫인상 신뢰감 무게감 주는 법"),
    ("frame",    "silence_ko",   "침묵의 힘 말 적게 하는 사람 무게"),
    ("charisma", "weiom",        "위엄 있는 사람 무게감 진중함 특징"),
    ("charisma", "charisma_ko",  "카리스마 있는 사람 존재감 비결"),
    ("charisma", "voice_weight", "신뢰가는 목소리 무게감 있는 말투 스피치"),
    ("charisma", "nonverbal",    "눈빛 자세 비언어 첫인상 카리스마"),
    ("charisma", "gravitas_talk","가볍지 않게 말하는 법 말에 무게 있는 사람"),
    ("boundary", "not_ignored",  "무시당하지 않는 법 만만하게 보이지 않는 사람"),
    ("boundary", "rude_cope",    "무례한 사람 대처법 받아치는 법 품위 있게"),
    ("boundary", "provoke_calm", "도발에 흔들리지 않는 법 화 안 내고 대응하는 법"),
    ("boundary", "boundary_ko",  "선 넘는 사람 선긋기 단호하게 말하는 법"),
    ("boundary", "respect_self", "함부로 못 대하게 하는 법 존중받는 사람 태도"),
    ("boundary", "composure",    "평정심 흔들리지 않는 멘탈 단단한 사람"),
]

def fmt_dur(s):
    if not s: return "?"
    s=int(s); return f"{s//60}:{s%60:02d}"

def main():
    opts={"extract_flat":True,"quiet":True,"skip_download":True,"ignoreerrors":True}
    rows=[]
    with YoutubeDL(opts) as ydl:
        for arch,key,q in QUERIES:
            info=ydl.extract_info(f"ytsearch7:{q}",download=False)
            ents=[e for e in ((info or {}).get("entries") or []) if e and e.get("id")]
            print(f"\n### [{arch}] {key}  ::  {q}")
            for e in ents[:7]:
                dur=e.get("duration")
                print(f"  {e['id']}  [{fmt_dur(dur)}]  {(e.get('channel') or e.get('uploader') or '?')[:20]:20}  {e.get('title','?')[:55]}")
                rows.append({"archetype":arch,"key":key,"query":q,"video_id":e["id"],"title":e.get("title","?"),
                             "channel":e.get("channel") or e.get("uploader") or "?",
                             "duration":dur,"url":f"https://www.youtube.com/watch?v={e['id']}"})
    out=Path(__file__).resolve().parent/"search_candidates.jsonl"
    with out.open("w",encoding="utf-8") as f:
        for r in rows: f.write(json.dumps(r,ensure_ascii=False)+"\n")
    print(f"\n[OK] {len(rows)} candidates -> {out}")

if __name__=="__main__":
    main()
