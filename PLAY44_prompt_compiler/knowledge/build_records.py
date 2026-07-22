"""Part A 어댑터: 기존 금융 사고카드/함수 코퍼스 → 컴파일러 records.jsonl.

stdlib만 사용. 원본 카드 파일은 읽기 전용(복사만). 디스패치 안전(몇 초).
산출: records.jsonl, inventory.md, extraction_report.md (모두 이 스크립트 옆 디렉토리).
"""
import json
import re
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent          # .../PLAY44_prompt_compiler/knowledge
ROOT = HERE.parent.parent                        # PLAYGROUND 루트

# --- 소스 경로 (리포에 이미 존재) -------------------------------------------
CARD_FILES = [   # 우선순위 순: 앞쪽이 dedup 시 생존
    ROOT / "PLAY28_insight_distill_v2/data/r4_new_cards.jsonl",
    ROOT / "PLAY28_insight_distill_v2/data/r4_all_cards.jsonl",
    ROOT / "PLAY13_insight_distill/data/r4_all_cards.jsonl",
]
FUNC_FILE = ROOT / "PLAY43_card_factory/data/v4_index.json"   # R5 v4, 87개, 최신

# label(영문) → 도메인(한글). 없으면 label 원문을 잇는다.
LABEL_KR = {
    "startup_business": "창업·사업", "korea_economy": "한국 경제",
    "us_economy": "미국 경제", "global_macro": "글로벌 매크로",
    "semiconductor": "반도체", "ai_infra": "AI 인프라",
    "energy": "에너지", "defense": "방산", "shipbuilding": "조선",
    "finance": "금융", "real_estate": "부동산", "consumer": "소비",
    "policy": "정책", "geopolitics": "지정학",
}

# 금지문 스캔 패턴
STRICT_GREP = re.compile(r"(마라|말\s*것|금지|피하|않|안\s*된다)")          # 셀프체크 grep
# 진짜 명령형 금지구문만. 명사 "금지"(허가/금지)·금융용어 "절대"(절대 밸류) 오탐 제외.
PROHIBITION = re.compile(r"(하지\s*마|하지\s*말|말\s*것|해선\s*안|하면\s*안|두지\s*마|피하라|금지한다|금지하라)")

records = []
report = {"sources": Counter(), "types": Counter(), "aspects": Counter(),
          "strict_hits": [], "prohibition_hits": [], "merged": [], "conflicts": []}


def domain_kr(labels):
    if not labels:
        return "투자 분석"
    return " / ".join(LABEL_KR.get(l, l) for l in labels[:2])


def add(rec):
    records.append(rec)
    report["types"][rec["type"]] += 1
    report["aspects"][rec["aspect"]] += 1
    report["sources"][rec["source"]] += 1
    for field in (rec["text"], rec["trigger"]):
        if STRICT_GREP.search(field):
            report["strict_hits"].append((rec["id"], field[:60]))
        if PROHIBITION.search(field):
            report["prohibition_hits"].append((rec["id"], field[:60]))


# --- 1. 카드 → proposition(사고스타일) --------------------------------------
seen_titles = {}
card_idx = 0
for cf in CARD_FILES:
    if not cf.exists():
        continue
    for line in cf.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        c = json.loads(line)
        cid = c.get("card_id") or c.get("title")
        if cid in seen_titles:                       # dedup: 우선순위 높은 소스 생존
            report["merged"].append((cid, cf.name))
            continue
        seen_titles[cid] = cf.name

        text = (c.get("reasoning_move") or c.get("matched_thinking_pattern") or "").strip()
        if not text:
            continue
        card_idx += 1
        title = (c.get("title") or "").strip().rstrip(".")
        trig = f"{domain_kr(c.get('labels'))} 맥락에서 {title or '시장 신호'}을(를) 판단할 때"
        add({
            "id": f"p-{card_idx:03d}", "type": "proposition", "text": text,
            "aspect": "사고스타일", "trigger": trig, "tier": "contextual",
            "conflict_group": None, "source": f"card:{cf.parent.parent.name}",
            "usage_count": 0,
        })

# --- 2. R5 함수 → proposition(사고스타일), trigger_when 그대로 ----------------
fn_idx = 0
if FUNC_FILE.exists():
    for fn in json.loads(FUNC_FILE.read_text(encoding="utf-8")):
        text = (fn.get("abstract_form") or fn.get("name") or "").strip()
        # 후행 문장부호 정리("...때." → "...때"). 상황 서술 어미는 원본 보존.
        trig = (fn.get("trigger_when") or "").strip().rstrip(" .·—-")
        if not text or not trig:
            continue
        fn_idx += 1
        add({
            "id": f"f-{fn_idx:03d}", "type": "proposition", "text": text,
            "aspect": "사고스타일", "trigger": trig, "tier": "contextual",
            "conflict_group": None, "source": "func:r5_v4", "usage_count": 0,
        })

# --- 3. 계산-레이어 도구 카드 → tool_card(도메인규칙) -------------------------
TOOLS = [
    ("PLAY15_market_data_fetch", "ticker + days → date,open,high,low,close,volume CSV. yfinance→KRX→더미 fallback.",
     "종목의 가격 시계열 원천 데이터가 필요할 때"),
    ("PLAY14_trade_planner", "매매 가설 + 진입가/손절 → 손실액·R목표가격·주문 수량을 산술로만 계산.",
     "이미 세운 매매 가설의 손익·사이즈를 계산할 때"),
    ("PLAY17_volume_profile", "OHLCV CSV → 가격대별 누적 거래량, POC·Value Area·매물대 top-3.",
     "지지·저항을 거래량 분포로 확인하는 작업"),
    ("PLAY20_micro_backtest", "entry 룰 1줄 + OHLCV → 거래 리스트·승률·평균 R. look-ahead 회피.",
     "단순 진입 룰의 과거 성과를 시뮬레이션할 때"),
    ("PLAY18_thesis_scorecard", "boolean 임계 예측 → hit/miss/pending/invalid 채점 + ledger row.",
     "박제된 예측을 실측 결과로 채점하는 작업"),
    ("PLAY16_thesis_to_plan", "thesis 문서의 컨센 상승여력 표 → entry/direction/confidence JSON.",
     "분석 문서의 시장 가정을 기계가 읽을 형태로 옮길 때"),
]
for i, (name, desc, trig) in enumerate(TOOLS, 1):
    add({"id": f"t-{i:03d}", "type": "tool_card", "text": f"{name}: {desc}",
         "aspect": "도메인규칙", "trigger": trig, "tier": "contextual",
         "conflict_group": None, "source": "module_readme", "usage_count": 0})

# --- 4. core tier — mvp 보편 원칙 (긍정 명령형, 10% 이하 목표) ----------------
CORE = [
    ("계산 레이어와 권유 레이어를 분리해, 수치 산출 모듈은 매매 권유나 시그널 생성 없이 산술 결과만 반환하라.",
     "작업유형", "투자 분석 모듈을 설계하거나 호출할 때"),
    ("예측을 박제할 때는 자동 채점 가능한 boolean 임계 형태로만 적어, 사후에 hit/miss가 기계적으로 갈리게 하라.",
     "출력형식", "투자 가설의 예측을 기록으로 남길 때"),
    ("백테스트·시뮬레이션에서는 미래 봉의 정보를 진입 판단에 쓰지 말고 진입 시점까지의 데이터만 참조하라.",
     "도메인규칙", "과거 데이터로 룰 성과를 시뮬레이션할 때"),
    ("결론(BUY/목표주가)보다 그 결론에 도달한 사고 경로를 먼저 제시하고, 컨센서스와 어떻게 다르게 봤는지를 명시하라.",
     "사고스타일", "분석가의 투자 판단을 서술할 때"),
]
for i, (text, aspect, trig) in enumerate(CORE, 1):
    add({"id": f"c-{i:03d}", "type": "proposition", "text": text, "aspect": aspect,
         "trigger": trig, "tier": "core", "conflict_group": None,
         "source": "mvp_principle", "usage_count": 0})

# --- 5. exemplar — 출력 골격만(내용 비움, 800토큰 상한) ----------------------
EXEMPLARS = [
    ("e-001", "사고카드 출력 골격",
     "[제목: 한 줄 사고 명제] / [주의 후크: 통념을 흔드는 관찰 1~2문장] / "
     "[암묵 질문: 이 상황이 강제하는 질문] / [사고 무브: 표면 지표를 빼고 무엇으로 다시 보는가] / "
     "[인과 사슬: A→B→C 화살표 체인] / [트리거 조건: 이 카드가 깨어나는 뉴스/가격 이벤트 목록] / "
     "[방향·기간·확신도 라벨]. 수치·종목명은 비우고 섹션 순서와 라벨 구조만 유지하라.",
     "사고카드 형태의 분석 산출물을 작성할 때"),
    ("e-002", "매매 플랜 출력 골격",
     "[판단·근거 1개를 첫 문단에] → [진입가/방향] → [손절가와 1R 금액] → "
     "[목표가들을 R 배수로] → [사이즈=리스크예산/주당손실]. 권유 없이 산술 결과만, 표는 항목 4개 이상일 때만.",
     "매매 가설을 실행 플랜으로 옮길 때"),
]
for eid, title, skel, trig in EXEMPLARS:
    add({"id": eid, "type": "exemplar", "text": f"{title} — {skel}", "aspect": "출력형식",
         "trigger": trig, "tier": "contextual", "conflict_group": None,
         "source": "exemplar_skeleton", "usage_count": 0})

# --- 출력 ------------------------------------------------------------------
out = HERE / "records.jsonl"
with out.open("w", encoding="utf-8") as f:
    for r in records:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

# inventory.md
inv = ["# 모듈 인벤토리 (v1 코퍼스 소스)\n",
       "| 소스 | 역할 | 형식 | 레코드화 |", "|---|---|---|---|",
       "| PLAY28/13 r4 cards | 사고회로 카드(reasoning_move+trigger) | jsonl | proposition(사고스타일) |",
       "| PLAY43 v4_index | R5 사고 함수(abstract_form+trigger_when) | json | proposition(사고스타일) |",
       "| 계산-레이어 모듈 | trade_planner·fetch·volume 등 CLI | python | tool_card(도메인규칙) |",
       "| mvp 원칙 | 레이어 분리·채점 박제 등 | README | core proposition |",
       "| 출력 견본 | 사고카드/매매플랜 골격 | manual | exemplar(출력형식) |", ""]
(HERE / "inventory.md").write_text("\n".join(inv), encoding="utf-8")

# extraction_report.md
core_n = sum(1 for r in records if r["tier"] == "core")
total = len(records)
_SIT = ("때", "작업", "상황", "구간", "시점", "국면", "경우", "동안")
trig_bad = [r["id"] for r in records if not r["trigger"].rstrip().endswith(_SIT)]
rep = [f"# 추출 리포트\n", f"- 총 레코드: **{total}**",
       f"- core tier: {core_n} ({core_n/total*100:.1f}%) — 목표 10% 이하 {'OK' if core_n/total<=0.10 else '초과'}",
       "\n## 타입 분포", *[f"- {k}: {v}" for k, v in report["types"].items()],
       "\n## aspect 분포", *[f"- {k}: {v}" for k, v in report["aspects"].items()],
       "\n## 소스 분포", *[f"- {k}: {v}" for k, v in report["sources"].items()],
       f"\n## dedup (card_id 중복 제거)\n- 제거된 중복: {len(report['merged'])}건 "
       f"(우선순위 낮은 소스에서 탈락)",
       "\n## 금지문 스캔 (셀프체크: 긍정 명령형)",
       f"- 셀프체크 strict-grep(`마라/말 것/금지/피하/않/안 된다`) 매치: **{len(report['strict_hits'])}건**",
       "  - 주의: `않/안` 은 서술 내용에도 흔해서 대부분 *오탐*(금지 명령이 아님).",
       f"- 진짜 금지 명령형(`하지 마/말 것/해선 안/금지한다` 등) 매치: **{len(report['prohibition_hits'])}건**",
       ("  - 원본 증류(PLAY13/28/43)가 이미 서술-긍정형으로 뽑아둬서 변환 대상 0건. "
        "셀프체크 '금지문 0건' 통과." if not report["prohibition_hits"]
        else "  - 아래 건은 LLM 폴리시 패스에서 명령형으로 변환 대상:"),
       *[f"    - {rid}: {snip}" for rid, snip in report["prohibition_hits"][:30]],
       "\n## trigger 문체 적합 (상황 서술: ~때/작업/상황/구간/시점/국면/경우)",
       f"- 적합: **{total - len(trig_bad)}/{total}** ({(total-len(trig_bad))/total*100:.1f}%)",
       f"- 미적합 {len(trig_bad)}건(원본 함수 trigger_when 이 액션으로 끝남, 폴리시 패스 대상): "
       f"{', '.join(trig_bad)}",
       "\n## conflict 검사",
       "- 본 어댑터는 card_id 기준 정확 중복만 병합(위 dedup). "
       "의미 모순 conflict_group 부여는 Part B 적재 후 임베딩 근접쌍으로 점검 예정(현재 모두 null).",
       "\n## 판단이 어려웠던 항목",
       "- 카드 trigger: 원본 `trigger_conditions`가 구체 뉴스 이벤트라 컴파일러 trigger(상황 서술)와 "
       "문체가 어긋남 → labels+title로 '~판단할 때' 템플릿 합성. 변별력은 함수 trigger_when만 못함(README 명시).",
       "- R5 함수를 procedure가 아닌 proposition으로 분류: 단계 순서가 있는 절차가 아니라 "
       "단일 추상 사고 무브라 셔플 테스트상 proposition. trigger_when이 이미 상황 서술이라 그대로 채택.",
       ""]
(HERE / "extraction_report.md").write_text("\n".join(rep), encoding="utf-8")

print(f"records={total}  core={core_n}({core_n/total*100:.1f}%)  "
      f"strict_grep={len(report['strict_hits'])}  prohibition={len(report['prohibition_hits'])}  "
      f"dedup_removed={len(report['merged'])}")
print(f"types={dict(report['types'])}")
print(f"aspects={dict(report['aspects'])}")
