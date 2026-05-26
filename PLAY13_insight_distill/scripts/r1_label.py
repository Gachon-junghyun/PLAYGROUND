# FILE: PLAY13_insight_distill/scripts/r1_label.py
"""R1 토픽 라벨링 — s1_clean.jsonl 의 958건 명제에 라벨 1~2개 부여."""
from __future__ import annotations
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(r"C:\Users\fivep\OneDrive\Desktop\PLAYGROUND\PLAY13_insight_distill")
SRC = ROOT / "data" / "s1_clean.jsonl"
OUT = ROOT / "data" / "r1_topics.jsonl"

# ---- 키워드 사전 (proposition + raw_quote 통합 텍스트에서 검색) ----
# 우선순위: 더 구체적인 라벨이 먼저, 일반 라벨은 뒤
KW = {
    # 매크로
    "fed_policy": [
        "연준", "fomc", "FOMC", "파월", "케빈 워시", "워시", "금리 인하", "금리 인상",
        "기준금리", "통화정책", "점도표", "연방준비", "rate cut", "연방공개시장",
        "카시카리", "로건 총재", "총재", "금리 동결", "완화적 기조",
        "채권금리", "국채 금리", "국채금리", "10년물", "장단기 금리", "제로 금리", "제로금리",
    ],
    "inflation_data": [
        "cpi", "CPI", "pce", "PCE", "ppi", "PPI", "물가 지표", "물가지표",
        "인플레", "물가 상승", "근원물가", "consumer price",
    ],
    "employment_data": [
        "고용보고서", "비농업", "실업률", "민간 고용", "고용 시장", "고용시장",
        "고용 지표", "노동시장", "adp", "ADP", "신규 실업", "일자리",
    ],
    "oil_geopolitics": [
        "이란", "호르무즈", "호르무제", "호르메이", "호르무지", "호르무지에어",
        "이스라엘", "레바논", "헤즈볼라",
        "중동", "원유 수출", "원유수출", "유가", "원유 가격", "원유가격",
        "원유 재고", "원유재고", "EIA", "eia",
        "브렌트유", "브랜트유", "wti", "WTI", "휴전", "종전", "전쟁 물자",
        "핵 프로그램", "핵프로그램", "우라늄", "봉쇄", "항구", "지정학적 긴장",
        "웰스파구",
    ],
    "china_macro": [
        "중국 경제", "위안화", "중국 정부", "중국 방문", "중국 외교",
        "왕위", "미·중", "미중", "중국 제조", "중국의 전기", "중국 기업",
    ],
    "emerging_markets": [
        "인도 주식", "인도 시장", "인도공대", "인도의", "인도 경제", "인도에서",
        "인도는", "인도가", "인도를", "인도인", "인도 출신", "인도 정부", "인도 지방",
        "인도 아대륙", "신흥국", "msci", "MSCI", "ERP", "erp 지표", "인도 IT",
        "브릭스", "포스코", "posco", "Posco", "월마트", "walmart", "Walmart",
        "중앙 정부", "산업 자본주의", "이념적 대립", "동서 양 진영",
    ],
    "us_equity_market": [
        "s&p500", "S&P500", "snp", "SNP", "나스닥", "다우", "다우지수",
        "주요 지수", "주요지수", "3대 지수", "미국 증시", "미 증시",
        "증시 상승", "증시 하락", "증시 마감", "지수 상승", "지수 하락",
        "증시는", "증시가", "지수가",
    ],
    "korea_economy": [
        "코스피", "kospi", "KOSPI", "한국 증시", "한국증시", "원달러",
        "한국 경제", "한국경제", "한국은행", "한국 정부",
    ],
    # 산업
    "ai_tech": [
        "ai ", "AI ", "ai가", "AI가", "ai의", "AI의", "ai를", "AI를", "ai 투자", "AI 投資",
        "ai 모델", "AI 모델", "인공지능", "클로드", "claude", "chatgpt", "gpt", "GPT",
        "엔트로픽", "anthropic", "오픈ai", "openai", "llm", "LLM", "ai 인프라",
        "ai 관련", "ai 열기", "ar 기술", "AR 기술", "컴퓨팅 자원", "컴퓨팅 파워",
        "시스템 자원", "시스템 성능", "성능 저하",
    ],
    "semiconductor_cycle": [
        "반도체", "메모리", "파운드리", "엔비디아", "nvidia", "amd", "AMD",
        "마이크론", "샌디스크", "인텔", "intel", "tsmc", "TSMC",
        "sk하이닉스", "SK하이닉스", "삼성전자", "asml",
    ],
    "big_tech_earnings": [
        "빅테크", "애플", "apple", "마이크로소프트", "microsoft", "MS ",
        "구글", "google", "메타", "meta", "아마존", "amazon", "테슬라", "tesla",
        "캐펙스", "capex", "클라우드", "ge 버노바", "GE 버노바",
    ],
    "game_industry": [
        "게임", "닌텐도", "nintendo", "콘솔", "넥슨", "nexon", "엔씨", "엔씨소프트",
        "크래프톤", "스위치", "패키지", "rpg", "RPG", "오픈월드", "몬스터",
        "유비식", "케어이닉스", "케리이닉스", "케이리이닉스", "엔터테인",
    ],
    "consumer_electronics": [
        "가전", "청소기", "다이슨", "샤오미", "냉장고", "세탁기",
        "전자제품", "전기제품", "lg전자", "LG전자", "삼성 가전", "니치 마켓", "니치마켓",
        "이동형 TV", "이동형TV", "tv 시장", "TV 시장", "하드웨어 기술", "중국 하드웨어",
        "lg ", "LG ", "lg의", "LG의", "lg는", "LG는",
    ],
    "entertainment_content": [
        "디즈니", "disney", "콘텐츠", "영화", "드라마", "엔터", "ott", "OTT",
        "넷플릭스", "netflix", "작품성", "소설", "독자",
    ],
    "energy_commodities": [
        "가솔린", "원자재", "에너지 공급", "에너지공급", "에너지 가격", "유류",
        "정유", "석탄", "천연가스", "lng", "LNG",
    ],
    # 기업·종목
    "corporate_earnings": [
        "실적 발표", "실적발표", "어닝", "earnings", "eps", "EPS", "분기 실적",
        "분기실적", "가이던스", "예상치 상회", "예상치 하회", "기업 실적", "기업실적",
        "영업이익", "순이익", "매출액", "매출",
    ],
    "single_stock_move": [
        "주가 상승", "주가 하락", "주가는", "주가가", "급등", "급락",
        "13% 상승", "% 상승", "% 하락", "랠리", "주식이 상승", "종목",
    ],
    "startup_business": [
        "스타트업", "창업", "사업 모델", "사업모델", "회사 운영", "고객",
        "고객 서비스", "고객서비스", "비즈니스", "직접 재배", "상조",
        "휴대폰 구매", "마케팅 전략", "회사를", "회사가", "대표님", "발화자는 직접",
        "민원", "원빈", "아정당", "본인이", "본인은", "본인의",
    ],
    "brand_strategy": [
        "브랜드", "마케팅", "시장 점유율", "시장점유율", "소비자", "트렌드",
        "포지셔닝", "상품 카테고리", "리치마켓", "리치 마켓", "출시",
        "디자인", "디테일", "제품의", "제품을", "제품이", "제품 개발",
        "스탠바이 미", "아이리버", "고드밀러", "DJI", "dji", "와일드쌤",
        "테크 리뷰", "얼리어덥터", "휴머노이드", "로봇 기술", "드론",
        "영업 이익률", "이익률", "가이드북", "맛집", "음향기기",
    ],
    # 일반론·메타
    "market_sentiment": [
        "시장 분위기", "시장분위기", "시장의 분위기", "투자 심리", "투자심리",
        "낙관", "비관", "위험자산", "위험 자산", "리스크온", "리스크오프",
        "market sentiment", "심리는", "심리가", "분위기로", "분위기가",
    ],
    "investment_strategy": [
        "투자 전략", "투자전략", "자산 배분", "자산배분", "장기 투자", "장기투자",
        "포트폴리오", "분산", "매크로 vs", "투자 철학", "투자철학", "투자자들",
    ],
    "risk_factors": [
        "리스크", "위험", "불확실성", "거품", "버블", "하방", "변동성",
        "충격", "우려", "경고", "함정",
    ],
    "geopolitics_general": [
        "트럼프", "trump", "외교", "관세", "tariff", "무역 협상", "무역협상",
        "러시아", "푸틴", "우크라", "북한", "정치인", "협상이", "협상은", "협상을",
        "정상회담", "외교 보장", "양해의",
    ],
    "analyst_view": [
        "애널리스트", "analyst", "전문가", "캠피셔", "전망", "리포트",
        "분석가", "투자은행", "스트래티지스트", "골드만", "모건스탠리",
    ],
    "personal_anecdote": [
        "여행", "호텔", "출장", "어릴 적", "어렸을", "패밀리를", "발화자가 자신의",
        "본인의 경험", "일상", "건강 상태", "건강상태",
        "코끼리", "강아지", "결혼", "왕족", "천민", "아버지는", "딸에게",
        "도로의 질", "약은 효과", "현지에서", "한국인은", "왕들의 권력", "사람들에게 두려움",
        "한국에서 판매",
    ],
}

# 우선순위 순서 (구체 → 일반). 같은 텍스트가 여러 라벨에 매치되면 이 순서대로 상위 2개 선택.
PRIORITY = [
    "fed_policy", "inflation_data", "employment_data", "oil_geopolitics",
    "semiconductor_cycle", "ai_tech", "big_tech_earnings",
    "game_industry", "consumer_electronics", "entertainment_content",
    "energy_commodities",
    "china_macro", "emerging_markets", "korea_economy",
    "corporate_earnings", "single_stock_move",
    "startup_business", "brand_strategy",
    "us_equity_market",
    "market_sentiment", "risk_factors", "investment_strategy",
    "geopolitics_general", "analyst_view", "personal_anecdote",
]


def score_text(text: str) -> dict[str, int]:
    """텍스트에서 라벨별 키워드 매치 수를 계산."""
    text_low = text.lower()
    scores: dict[str, int] = {}
    for label, kws in KW.items():
        c = 0
        for kw in kws:
            # 영문 키워드는 소문자로 통일 비교
            needle = kw.lower()
            if needle in text_low:
                c += 1
        if c > 0:
            scores[label] = c
    return scores


def assign_labels(rec: dict) -> list[str]:
    """한 명제에 라벨 1~2개 부여."""
    prop = rec.get("proposition") or ""
    raw = rec.get("raw_quote") or ""
    text = prop + " || " + raw

    scores = score_text(text)

    # 1개도 안 잡히면 기존 topics를 보조로 활용
    if not scores:
        orig = " ".join(rec.get("topics", []) or [])
        if orig:
            scores = score_text(orig)

    if not scores:
        # 화자 기반 폴백 — 채널 성격에 따라 약하게라도 매칭
        sp = rec.get("speaker", "")
        # 매우 짧고 의미 없는 문장 → noise
        if len(prop) < 8:
            return ["noise"]
        # 일반 키워드로 1차 폴백
        if any(x in text for x in ["증시", "주가", "지수", "랠리", "상승 마감", "하락 마감"]):
            return ["us_equity_market"]
        if any(x in text for x in ["채권", "금리", "수익률"]):
            return ["fed_policy"]
        if any(x in text for x in ["회사", "사업", "고객", "대표님", "본인", "민원",
                                   "발화자는 직접", "원빈", "삼성전자", "sk아이템"]):
            return ["startup_business"]
        if any(x in text for x in ["게임", "닌텐도", "콘솔", "rpg", "RPG"]):
            return ["game_industry"]
        if any(x in text for x in ["제품", "디자인", "이익률", "출시", "스탠바이",
                                   "휴머노이드", "로봇"]):
            return ["brand_strategy"]
        if any(x in text for x in ["가전", "tv", "TV", "청소기", "냉장고"]):
            return ["consumer_electronics"]
        # 화자별 기본값 (매우 약한 매칭일 때)
        if sp == "머니코믹스":
            # 머니코믹스는 인도·사회·창업 일화가 많음
            if any(x in text for x in ["미국", "한국", "중국", "정부", "권력", "체제"]):
                return ["geopolitics_general"]
            return ["personal_anecdote"]
        if sp == "머니그라피":
            # 머니그라피는 가전·소비재·게임 트렌드 잡담
            if any(x in text for x in ["산업", "성장세", "성장", "한국 브랜드", "한국브랜드"]):
                return ["market_sentiment"]
            return ["brand_strategy"]
        if sp == "김단테 월가아재":
            return ["market_sentiment"]
        if sp == "오선의 미국 증시 라이프":
            return ["us_equity_market"]
        return ["noise"]

    # 우선순위 정렬: 점수 내림차순, 동점이면 PRIORITY 순서 가까운 것 우선
    pri_idx = {l: i for i, l in enumerate(PRIORITY)}

    def sort_key(item):
        label, sc = item
        return (-sc, pri_idx.get(label, 999))

    ordered = sorted(scores.items(), key=sort_key)
    top = [lbl for lbl, _ in ordered[:2]]

    # 라벨 2개 중 하나가 너무 일반적이고(예: us_equity_market) 다른 게 더 구체적이면
    # 일반 라벨은 1순위에서 밀어내기 — 이미 PRIORITY가 처리
    # 단, 점수가 1점뿐인 매우 약한 매치는 2번째 라벨로 부여하지 않음
    if len(top) == 2 and ordered[1][1] == 1 and ordered[0][1] >= 2:
        # 약한 두 번째 라벨도 그대로 부여하는 게 그룹화에 도움 → 유지
        pass

    return top


def main() -> None:
    written = 0
    label_counter: Counter[str] = Counter()
    speaker_label: dict[str, Counter[str]] = {}
    noise_n = 0

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with SRC.open("r", encoding="utf-8") as f_in, OUT.open("w", encoding="utf-8") as f_out:
        for line in f_in:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            vid = rec.get("video_id", "")
            ci = rec.get("chunk_idx", 0)
            si = rec.get("sentence_idx_in_chunk", 0)
            rec_id = f"{vid}:{ci}:{si}"
            labels = assign_labels(rec)
            for lb in labels:
                label_counter[lb] += 1
            if labels == ["noise"]:
                noise_n += 1
            sp = rec.get("speaker", "?")
            speaker_label.setdefault(sp, Counter()).update(labels)
            f_out.write(json.dumps({"id": rec_id, "labels": labels}, ensure_ascii=False) + "\n")
            written += 1

    print(f"WROTE {written} lines -> {OUT}")
    print(f"NOISE: {noise_n}/{written}")
    print("\nTop 15 labels:")
    for lb, c in label_counter.most_common(15):
        print(f"  {lb}: {c}")
    print("\nPer speaker top 5:")
    for sp, ctr in speaker_label.items():
        top5 = ", ".join(f"{l}={c}" for l, c in ctr.most_common(5))
        print(f"  [{sp}] {top5}")


if __name__ == "__main__":
    main()
