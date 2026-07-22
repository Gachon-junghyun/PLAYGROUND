import json, pathlib, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = pathlib.Path(__file__).resolve().parent

# 큐레이션: "어떻게 읽고 맥락·의미를 이해하는가" 방법/사고방식만. 책추천·예능·영어·수학·하울 제외.
KEEP = {
    "mnssLzB3kpY",  # 너진똑 — 요약 채널 아닙니다 (깊게 읽기 vs 요약)
    "OpbK-ol_7xs",  # 책과삶 — 김범준 교수, 바빠도 책 읽는 이유 (통합본·장편 가능)
    "h0c7EJWxtT0",  # 책과삶 — 신종호 교수, 제대로 책 읽는 방법
    "5h4PRkNnB8o",  # 책과삶 — 뇌과학자, 책 읽자마자 뇌에서 벌어지는 일
    "f3BIA2LXv7U",  # 교육대기자 — 이명주, 성적 좌우 4단계 독서법
    "rFp4HIcW6iw",  # 김교수의 세 가지 — 독서해도 인생 안 바뀌는 이유 (비판)
    "SGrRiqYIGpA",  # 메가스터디 — 정담온, 디테일 독서(국어 독해) OT
    "5EV6Rm4P04w",  # 어디든학교 — 중등까지 독서 로드맵
    "tAbCs9HdJxU",  # 어디든학교 — 열심히 읽어도 머리에 안 들어오면
    "IZPFa02WnWk",  # 교집합 — 문해력 터지는 질문 / 추론·비판 독해
    "Yv9tXs1I_-4",  # 교집합 — 이명주, 독서 교육 로드맵 A-Z
    "vPW30g4wl-8",  # 드림코치 — 1년 100권 독서 방법
    "OvNf5c0LOFU",  # 윾머벨(유대종) — 이렇게 읽어야 안 틀립니다
    "nzx0YqU8B2I",  # 연수남TV — 읽기만 해도 뇌에 복사
    "MOCJ0E-zrE0",  # 심찬우 — 문학은 이렇게 읽어주세요
    "nIoCKqCDJTo",  # 심찬우 — 생각하며 글 읽기 OT
    "-9LGUWa-ZQ8",  # 메디소드 — 어려운 글 제대로 읽는 법 (수능 헤겔)
    "VoX4pwYnMtk",  # 메디소드 — 비문학 시험 가벼워짐
    "8PTsvqB1ZPI",  # 메디소드 — 독해력 높이는 법
    "NO3k95Cc6rw",  # 메디소드 — 글 빠르게 읽기 (읽는 순서)
}

rows = [json.loads(l) for l in (HERE / "queue_all.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
kept = [r for r in rows if r["video_id"] in KEEP]
missing = KEEP - {r["video_id"] for r in kept}

out = HERE / "queue.jsonl"
with out.open("w", encoding="utf-8") as fp:
    for r in kept:
        fp.write(json.dumps(r, ensure_ascii=False) + "\n")

print(f"curated queue: {len(kept)}/{len(rows)}  -> {out.name}")
if missing:
    print("WARNING missing ids:", missing)
for r in kept:
    print(f"  [{r['channel']}] {r['title'][:70]}")
