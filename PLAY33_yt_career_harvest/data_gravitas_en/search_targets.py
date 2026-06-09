# data_gravitas_en/search_targets.py
"""'무시받지 않는 위엄·무게감' EN 코퍼스 큐레이션용 ytsearch 타게팅.
4원형(협상·레버리지 / 프레임·권력·이미지 / 카리스마·존재감 / 경계·도발대응)을
실존 표본(Chris Voss·William Ury·Robert Greene·Cialdini·Charisma on Command 등)
이름으로 직접 겨냥. 채널발견(01)이 아니라 표본 역추출용. 큐는 큐레이션으로 고른다."""
from __future__ import annotations
import json, sys
from pathlib import Path
from yt_dlp import YoutubeDL

for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

# (archetype, key, query)  archetype: nego/frame/charisma/boundary
QUERIES = [
    ("nego",     "voss_empathy",   "Chris Voss tactical empathy never split the difference negotiation"),
    ("nego",     "voss_calibrated","Chris Voss calibrated questions how to negotiate"),
    ("nego",     "voss_voice",     "Chris Voss late night FM DJ voice mirroring labeling"),
    ("nego",     "ury_harvard",    "William Ury getting to yes BATNA harvard negotiation"),
    ("nego",     "leverage",       "negotiation leverage how to get what you want hostage negotiator"),
    ("frame",    "greene_power",   "Robert Greene 48 laws of power interview presence"),
    ("frame",    "greene_nature",  "Robert Greene laws of human nature mastery seductive"),
    ("frame",    "cialdini",       "Robert Cialdini influence persuasion principles authority"),
    ("frame",    "frame_control",  "frame control conversation never lose frame high status"),
    ("frame",    "silence_power",  "power of silence pause speak less commanding presence"),
    ("charisma", "command_respect","how to command respect charisma on command"),
    ("charisma", "gravitas",       "how to be taken seriously gravitas body language men"),
    ("charisma", "vanessa_cues",   "Vanessa Van Edwards charisma cues body language captivate"),
    ("charisma", "vinh_voice",     "Vinh Giang voice presence speaking master your voice"),
    ("charisma", "status_signals", "high status behavior body language signals confidence"),
    ("boundary", "disrespect",     "how to respond to disrespect with class stay calm"),
    ("boundary", "comeback_calm",  "how to shut down rude people without losing composure"),
    ("boundary", "assertive",      "how to set boundaries assertiveness stop being a pushover"),
    ("boundary", "provoked",       "how to stay composed when provoked grey rock unbothered"),
    ("boundary", "intimidating",   "how to stop being walked over command authority quiet confidence"),
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
                print(f"  {e['id']}  [{fmt_dur(dur)}]  {(e.get('channel') or e.get('uploader') or '?')[:24]:24}  {e.get('title','?')[:60]}")
                rows.append({"archetype":arch,"key":key,"query":q,"video_id":e["id"],"title":e.get("title","?"),
                             "channel":e.get("channel") or e.get("uploader") or "?",
                             "duration":dur,"url":f"https://www.youtube.com/watch?v={e['id']}"})
    out=Path(__file__).resolve().parent/"search_candidates.jsonl"
    with out.open("w",encoding="utf-8") as f:
        for r in rows: f.write(json.dumps(r,ensure_ascii=False)+"\n")
    print(f"\n[OK] {len(rows)} candidates -> {out}")

if __name__=="__main__":
    main()
