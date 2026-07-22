# data_yooseyoon/build_queue.py
"""메인이 search_candidates에서 직접 고른 '유세윤이 주인공'인 영상만 queue.jsonl 로.
노이즈 제거: 탁재훈/장동민 단독, 문세윤(≠유세윤), 유재석 유퀴즈, 피식대학, 팬 패러디 컷."""
from __future__ import annotations
import json, sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

# (video_id, facet, channel, title)  — 짧은 것부터, 60분 옹달샘은 맨 뒤(끊겨도 skip-done 이어받기)
CURATED = [
    # ── 콩트 / 캐릭터 / 얼굴개그 (구성된 개그를 짜는 법) ──
    ("o6FuBVNF00I", "skit_character", "JTBC Entertainment", "우회개그 '내가 공자라니' 장르만 코미디"),
    ("sW4uuatinZo", "skit_character", "JTBC Entertainment", "분노 가득한 유세윤에게 혼나는 윤시윤"),
    ("_WwL8Y8jgG4", "skit_character", "tvN D ENT",          "유세윤 얼굴로 하드캐리 미친 재능 모음 (코빅)"),
    ("W-CmRlBYFtM", "skit_character", "디글 클래식",          "사람처럼 싸우는 유세윤 X 장동민 (코빅)"),
    ("aIwdF4pOzNw", "skit_character", "코미디빅리그",          "용진호개그보충대 유세윤x유병재x조세호"),
    # ── UV 음악개그 (개그 작법: 컨셉·가사) ──
    ("RHc5_8D-GdQ", "uv_music", "소니뮤직코리아",  "MV 유세윤 - 금지된 경호 (feat 권혁수)"),
    ("j8c_QfvP3ag", "uv_music", "DonghaLover",     "유희열의 스케치북 UV (토크+무대)"),
    ("JdfiZzfwMIQ", "uv_music", "df 디에프",        "UV 킬링벌스 라이브 (쿨하지못해/집행유애/이태원프리덤)"),
    # ── 토크 입담 / 실시간 애드립 (치는 방식·타이밍·양) ──
    ("xeF0q3x_uM4", "talk_adlib", "강유미 yumi kang", "강유미 X 유세윤 만남 토크"),
    ("0LBmpkscG_Q", "talk_adlib", "엠뚜루마뚜루",     "8년만의 라스 복귀 유세윤 모음.zip"),
    ("XucmCt5pFbk", "talk_adlib", "KBS 깔깔티비",     "옹달샘 비운의 캐릭터 유세윤&장동민&유상무 3편"),
    ("Takzf2LwRFc", "talk_adlib", "KBS 깔깔티비",     "아버님 멱살+핫도그 던진 세윤 컬투&옹달샘 2편"),
    ("Z836wA011z8", "talk_adlib", "JTBC Voyage",     "옹달샘 레전드 토크 유세윤·장동민·유상무 (60분)"),
]

def main():
    rows=[{"video_id":vid,"title":title,"channel":ch,"facet":facet,
           "url":f"https://www.youtube.com/watch?v={vid}"}
          for vid,facet,ch,title in CURATED]
    out=Path(__file__).resolve().parent/"queue.jsonl"
    with out.open("w",encoding="utf-8") as f:
        for r in rows: f.write(json.dumps(r,ensure_ascii=False)+"\n")
    print(f"[OK] {len(rows)} videos -> {out}")
    from collections import Counter
    for facet,n in Counter(r["facet"] for r in rows).items():
        print(f"  {facet:16} {n}")

if __name__=="__main__":
    main()
