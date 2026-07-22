# -*- coding: utf-8 -*-
"""
PLAY49 말풍선 리포트 — 데이터 빌더 (= "AI 에이전트"의 클로드 코드 루틴 파트)

PLAY43_card_factory 가 이미 수집·증류해 둔 실제 증권 리포트 + 사고카드를 읽어
프론트(index.html)가 바로 먹는 data.js 를 만든다. 실시간 LLM API 호출 없음 —
요약 3줄은 카드팩토리가 오프라인에서 증류해 둔 카드 필드에서 뽑아 쓴다.

CARD FACTORY (PLAY43)  ──ingest+distill──▶  data/inbox/*.txt + data/cards/*.cards.jsonl
                                                        │  (이 스크립트)
                                                        ▼
                                              PLAY49/data.js  ──▶  index.html(말풍선 차트)

실행:  python build_data.py
출력:  data.js  (window.DEMO_DATA = {...})  — 더블클릭 index.html 이 <script>로 로드
표준 라이브러리만 사용.
"""
import json, glob, os, re, datetime, io, sys

HERE = os.path.dirname(os.path.abspath(__file__))
CF = os.path.normpath(os.path.join(HERE, "..", "PLAY43_card_factory", "data"))

# ── 데모 주제: 카드팩토리 리포트가 실제로 몰려 있는 '에너지/호르무즈' 국면 ──
# (리포트는 산업분석이라 단일 종목 목표가가 없다 → 모의 섹터 지수 위에 얹는다.)
THEME = "energy"
THEME_KEYS = ["호르무즈", "유가", "에너지", "유틸", "원유", "정유", "oil", "energy", "opec"]

# 모의 에너지 섹터 지수 (호르무즈 긴장 → 우상향). 주말 제외. 검증 없이 진행 — README 참고.
SERIES = [
    ("2026-05-26", 100.0), ("2026-05-27", 99.6),  ("2026-05-28", 101.1),
    ("2026-05-29", 100.9), ("2026-06-01", 102.2), ("2026-06-02", 103.4),
    ("2026-06-03", 103.0), ("2026-06-04", 104.3), ("2026-06-05", 105.1),
    ("2026-06-08", 107.2), ("2026-06-09", 109.0), ("2026-06-10", 112.1),
    ("2026-06-11", 115.4), ("2026-06-12", 117.0), ("2026-06-13", 116.2),
]

OPINION_MAP = [  # (정규식, 표시의견, tone, newsImpact)
    (r"OVERWEIGHT|비중\s*확대|strong\s*buy|적극\s*매수", "비중확대", "up", 2),
    (r"\bBUY\b|매수|outperform|상향", "매수", "up", 2),
    (r"NEUTRAL|중립|hold|marketperform|시장수익률", "중립", "flat", -1),
    (r"UNDERWEIGHT|비중\s*축소|\bSELL\b|매도|하향", "비중축소", "down", -2),
]


def norm_date(d):
    d = d.strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}$", d):
        return d
    m = re.match(r"^(\d{2})\.(\d{2})\.(\d{2})$", d)  # 26.06.11
    if m:
        return f"20{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return d


def read_header(text):
    h = {}
    for line in text.splitlines()[:12]:
        for k in ("source", "title", "broker", "date", "url"):
            if line.lower().startswith(k + ":"):
                h[k] = line.split(":", 1)[1].strip()
    return h


def first_sentence(s, limit=78):
    if not s:
        return ""
    s = re.sub(r"\s+", " ", s).strip()
    # 우선순위: → 분기,  ;  세미콜론,  '. ' 마침표
    for sep in ["→", ";", ". "]:
        i = s.find(sep)
        if 12 <= i <= limit:
            s = s[:i]
            break
    s = s.strip(" ,.;·-")
    if len(s) > limit:
        cut = s[:limit]
        sp = cut.rfind(" ")
        if sp >= limit - 18:  # 띄어쓰기 경계가 가까우면 거기서 자른다
            cut = cut[:sp]
        s = cut.rstrip(" ,.;·-") + "…"
    return s


def detect_opinion(body):
    up = body.upper()
    for rx, label, tone, impact in OPINION_MAP:
        if re.search(rx, up, re.I):
            return label, tone, impact
    return "주목", "flat", 1  # 의견 명시 없는 산업 리포트 기본값


def find_inbox(rid):
    for cand in glob.glob(os.path.join(CF, "inbox", "*.txt")):
        if rid in os.path.basename(cand):
            return cand
        head = io.open(cand, encoding="utf-8", errors="replace").read(120)
        if ("# REPORT " + rid) in head:
            return cand
    return None


def build():
    cpath = os.path.join(HERE, "curated.json")
    curated = {}
    if os.path.exists(cpath):
        raw = json.load(io.open(cpath, encoding="utf-8"))
        curated = {k: v for k, v in raw.items() if not k.startswith("_")}
    reports = []
    for cf in sorted(glob.glob(os.path.join(CF, "cards", "*.cards.jsonl"))):
        base = os.path.basename(cf).replace(".cards.jsonl", "")
        rid = base.split("_")[-1]
        inbox = find_inbox(rid)
        if not inbox:
            continue
        body = io.open(inbox, encoding="utf-8", errors="replace").read()
        h = read_header(body)
        title = h.get("title", base)
        # 테마 필터: 에너지/호르무즈 국면만 데모 차트에 얹는다
        blob = (title + " " + base).lower()
        if not any(k in blob for k in THEME_KEYS):
            continue

        cards = [json.loads(l) for l in io.open(cf, encoding="utf-8") if l.strip()]
        if not cards:
            continue
        c = cards[0]
        # 채팅 피드용 3분할: 주장(claim) / 근거(evidence) / 결론(conclusion)
        claim = first_sentence(c.get("attention_hook") or c.get("matched_thinking_pattern"), 120)
        move = first_sentence(c.get("reasoning_move") or c.get("implicit_question"), 150)
        signal = first_sentence(c.get("original_signal") or "", 120)
        evidence = []
        if move:
            evidence.append({"label": "논리", "text": move})
        if signal:
            evidence.append({"label": "시그널", "text": signal})
        conclusion = (c.get("title") or "").strip() \
            or first_sentence(c.get("matched_thinking_pattern"), 90)

        # AI 에이전트(=클로드 코드 루틴)가 직접 정리한 주장/근거/결론이 있으면 그걸 쓴다.
        # 없으면 위 자동추출(초안)을 그대로 사용 — 새 리포트가 들어와도 깨지지 않게.
        cur = curated.get(rid)
        is_curated = bool(cur)
        if cur:
            claim = cur.get("claim", claim)
            evidence = cur.get("evidence", evidence)
            conclusion = cur.get("conclusion", conclusion)

        opinion, tone, impact = detect_opinion(body)
        src = h.get("source", "naver")
        firm = h.get("broker") or ("Seeking Alpha" if src == "seekingalpha" else "증권사")
        reports.append({
            "id": rid,
            "date": norm_date(h.get("date", "")),
            "firm": firm.strip(),
            "source": src,
            "opinion": opinion,
            "tone": tone,
            "newsImpact": impact,
            "title": title.rstrip("."),
            "claim": claim,
            "evidence": evidence,
            "conclusion": conclusion,
            "nCards": len(cards),
            "curated": is_curated,
        })

    reports = [r for r in reports if r["date"]]
    reports.sort(key=lambda r: r["date"])

    dates = [d for d, _ in SERIES]
    last, prev = SERIES[-1][1], SERIES[-2][1]
    data = {
        "subject": {
            "name": "에너지 섹터 (호르무즈 국면)",
            "ticker": "모의 지수 · MOCK",
            "unit": "pt",
            "price": round(last, 1),
            "change": round((last - prev) / prev * 100, 2),
            "asof": dates[-1],
            "note": "리포트는 실제(PLAY43 카드팩토리 수집), 가격선은 데모용 모의 지수",
        },
        "series": [{"date": d, "value": v} for d, v in SERIES],
        "reports": reports,
        "meta": {
            "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "source": "PLAY43_card_factory/data (inbox + cards)",
            "theme": THEME,
            "n_reports": len(reports),
            "no_live_api": True,
        },
    }

    payload = json.dumps(data, ensure_ascii=False, indent=2)
    # 브라우저용 data.js (window.DEMO_DATA)
    js = "// AUTO-GENERATED by build_data.py — do not edit by hand.\n"
    js += "// 출처: PLAY43_card_factory (실제 증권 리포트 + 증류 사고카드). 실시간 API 미사용.\n"
    js += "window.DEMO_DATA = " + payload + ";\n"
    io.open(os.path.join(HERE, "data.js"), "w", encoding="utf-8").write(js)
    # 데스크탑 창(app.py)용 data.json
    io.open(os.path.join(HERE, "data.json"), "w", encoding="utf-8").write(payload + "\n")
    # 콘솔(cp949)에서 한글 깨질 수 있어 ASCII 요약만 출력
    print("[ok] wrote data.js  reports=%d  series=%d  theme=%s"
          % (len(reports), len(SERIES), THEME))
    for r in reports:
        print("   - %s | %s | impact=%+d | cards=%d"
              % (r["date"], r["source"], r["newsImpact"], r["nCards"]))


if __name__ == "__main__":
    if not os.path.isdir(CF):
        print("[fail] card factory data not found:", CF)
        sys.exit(1)
    build()
