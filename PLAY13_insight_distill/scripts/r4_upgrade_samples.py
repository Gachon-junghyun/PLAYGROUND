"""R4 시범 업그레이드 — E010, E029 두 장을 애널리스트 페르소나로 high 등급 보강.

신규 필드: consensus_gap, bull_case, bear_case, monitoring_signals, analyst_view, cross_reference_cards.
기존 4 핵심 필드의 raw_quote는 유지, 그 위에 검증 가능 시계열·반증 시나리오 레이어 추가.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
A2 = ROOT / "data" / "r4_cards" / "A2_moneygraphy_mid4.jsonl"
A4B = ROOT / "data" / "r4_cards" / "A4b_moneycomics_bot8.jsonl"


E010 = {
  "card_id": "E010",
  "title": "전문툴 vs 쉬운툴 시장 역전",
  "labels": ["ai_tech", "startup_business", "brand_strategy"],
  "source_origin": "channel_interpretation",
  "source_quality": "medium",
  "framework_used": "platform_shift",
  "matched_thinking_pattern": "전문툴의 '에고와 레거시' 때문에 가장 쉬운 툴이 신규 유입 시장을 먼저 먹는 경로를 추적하는 사고",
  "attention_hook": "프리미어가 부루가 될 수 있느냐? 워드가 노션이 될 수 있느냐? 거의 안 된다. 사용자가 너무 많고 자기 에고를 못 내려놔서. 그러면 새로 시작하는 사람은 무조건 쉬운 쪽으로 간다는 게 정해진 결론이다.",
  "implicit_question": "전문툴이 RPO 두 자리 성장으로 *현금흐름*은 멀쩡한 동안, 신규 유료 결제 코호트의 *연령 분포 시프트*가 헤비 유저 자연감소를 어느 분기에 추월해 멀티플을 먼저 깎는가? 매출 컷 시점보다 *몇 분기 앞*인가?",
  "reasoning_move": "1차 해석 '프리미어/포토샵 점유율 90%+ = 락인'을 거부. (1) 헤비 유저는 '레거시·에고·전환비용'으로 못 갈아탐을 인정. (2) 신규 유튜버·디자이너 코호트는 부루·캡컷·캔바로 *입문*, 헤비 되어도 그대로 유지. (3) 따라서 *신규 유료 코호트 연령 분포*가 진짜 함수. (4) 어도비식 SaaS는 매출 가이던스가 OK여도 *코호트 자연감소가 RPO 성장률을 추월하는 분기*부터 멀티플 디레이팅, 이라는 신문회사 디버전스 패턴(E040 김단테 카드 cross-ref)으로 점프.",
  "consensus_gap": "시장 컨센서스: 어도비 RPO 25%+ 성장 + 엔터프라이즈 락인 + Firefly 자체 AI 통합으로 멀티플 유지. 화자 시각: 신규 유입 단절은 *재무제표에 나타나기 전에 멀티플로 먼저 처벌*되는 신문회사형 디버전스. 핵심 차이는 *시점*: 시장은 매출 가이던스 컷 시점, 화자는 *입문 점유 컷 시점*을 기준으로 본다 (보통 2~4분기 선행).",
  "bull_case": "어도비 디레이팅 지연 — 학생·교육 라이선스 점유 유지, Firefly·Acrobat AI 통합으로 신규 유료 결제자 평균 연령 안정. AI 네이티브 툴(부루·캡컷)이 *전문 워크플로우 커버리지 부족*으로 헤비 유저 진입 실패. 어도비 RPO 25%+ 4분기 연속 + Creative Subscription ARPU 상승 시 디레이팅 시나리오 무력.",
  "bear_case": "캡컷·캔바·부루의 한국·동남아 1020 MAU가 어도비 학생 라이선스 신규 등록보다 빠르게 점프. 어도비 어닝 콜에서 'creative subscriptions 신규 결제자 평균 연령' 언급이 처음 등장하는 분기. RPO 가이던스 한 분기 컷 + 신규 결제 -10%YoY 동반 시 컨센서스가 코호트 자연감소를 인정, 분기 1번부터 멀티플 디레이팅 본격화.",
  "monitoring_signals": [
    "어도비 분기 RPO·Creative Subscription 신규 결제자 가이던스 (Bear 트리거: 두 분기 연속 컨센 미스)",
    "캡컷·캔바·부루 글로벌 MAU·결제 전환율 시계열 (Bear 트리거: 어도비 신규 결제와 시계열 디버전스 6개월+ 지속)",
    "어도비 학생·교육 라이선스 신규 등록 추이 (Bear 트리거: 신규 등록 1년 누적 -10%+)",
    "어닝콜 'creative subscriptions 신규 결제자 평균 연령' 언급 빈도 (선행 지표 — 첫 언급이 진짜 신호)",
    "Reddit/X에서 'Premiere → CapCut/Vrew 마이그레이션' 키워드·해시태그 빈도 (감성 지표)"
  ],
  "analyst_view": "엔터프라이즈 SaaS 디버전스 카드 — *매수/매도 신호가 아니라* 어도비·세일즈포스·오토데스크·아토라시안 같은 *전문 워크플로우 SaaS*의 신규 유료 결제 코호트 연령 분포를 분기마다 추적하는 시그널 카드. 신문회사 디버전스 패턴(E040 cross-ref)과 결합해 'SaaS 섹터 디레이팅의 *재무제표 선행 신호*가 어디서 나오는가' 가설 검증용. 헤비 유저 락인 자체는 의심하지 않음 — 의심하는 건 *신규 유입 분배의 시점*.",
  "original_signal": "남세동 발언: '워드가 노션 될 수 있느냐, 파워포인트가 캔바 될 수 있느냐 — 잘 안 된다'; 부루 vs 프리미어 비교; 캡컷·캔바를 영상 편집 경쟁자로 인식; AI 시대의 '바이브 편집' 비전",
  "trigger_conditions": [
    "캡컷·캔바·부루 등 쉬운 영상툴 MAU 증가율 발표",
    "어도비 신규 가입자 증가율 둔화 공시",
    "AI 네이티브 편집 툴(런웨이·캡컷 AI) 신규 기능 출시",
    "프리미어→부루/캡컷 마이그레이션 사례 SNS 확산",
    "어도비/오토데스크/아토라시안 어닝콜에서 '신규 결제자 연령' 언급 시작",
    "어도비 학생·교육 라이선스 점유율 변화 발표"
  ],
  "causal_chain": "[전문툴이 충성 헤비 유저에 매몰돼 UX·과금모델 못 바꿈] → [신규 유저는 쉬운 AI 네이티브 툴(부루·캡컷·캔바)로 입문 후 헤비 되어도 유지] → [25세 이하 신규 유료 결제 비중 시계열 감소] → [헤비 유저 코호트 자연 감소가 RPO 성장률을 추월하는 분기 도래] → [매출 가이던스 컷보다 2~4분기 앞서 멀티플 디레이팅 (신문회사 패턴)]",
  "expected_direction": "bearish_long_conditional — 시점 함수는 신규 결제 코호트 연령 시계열에 의존",
  "time_horizon": "long",
  "confidence": "medium-high — 단일 화자 핵심 발언이나 어도비 RPO·CapCut/Canva MAU·신문회사 디버전스 사례로 다층 검증 가능",
  "evidence_type": "expert_interpretation_with_quant_proxy",
  "abstraction_level": "medium",
  "technical_depth": "medium",
  "quant_support": "multi_numbers",
  "speaker_views": {
    "남세동": "워드가 노션이 되고 파워포인트가 캔바가 되는 일은 안 일어난다. 전문툴은 사용자가 너무 많아서 못 바꾸고, 그래서 새 입문자가 다 쉬운 툴로 간다."
  },
  "source_videos": [
    {
      "video_id": "6zXcw8lf_zo",
      "channel": "머니그라피",
      "quote": "워드가 노션이 될 수 있느냐 파워포인트가 캠버가 될 수 있느냐... 잘 안 되는 것 같아요. 레거시가 너무 강하고 본인의 에고도 중요하지만 사용자가 너무 많고 조금이라도 바꾸면 안 되는 거예요. 바로 갈아탑니다."
    }
  ],
  "source_references": ["6zXcw8lf_zo:6:594", "6zXcw8lf_zo:6:601", "6zXcw8lf_zo:7:917"],
  "cross_reference_cards": ["E040"],
  "search_blurb": "Vrew 부루 CapCut Canva Adobe Premiere 어도비 노션 워드 platform shift 신규 유저 입문 툴 AI 바이브 편집 락인 레거시 에고 RPO 신규 결제 코호트 연령 분포 멀티플 디레이팅 신문회사 디버전스 코호트 자연감소 어닝 비트",
  "insight_quality": {
    "score_0_to_10": 8,
    "grade": "high",
    "score_reasons": [
      "신규 유저 입문 함수로 점프 명확",
      "헤비 유저·신규 유저 코호트 분리 + *시점* 함수까지 분해",
      "신문회사 디버전스 패턴(E040)과 cross-reference로 일반화",
      "monitoring signal 5개 시계열 검증 가능",
      "bull/bear case 둘 다 명시 + consensus_gap 1~2문장"
    ],
    "quality_test": "platform_shift로 가치 포획 위치가 '프로 워크플로우'에서 '쉬운 입문 경험'으로 옮겨가는 경로 + *재무제표 선행 신호 시점*까지 추적",
    "missing_to_upgrade": [
      "어도비 25세 이하 결제 비중 시계열 (공시 없으면 13F·앱 트래킹 데이터로 proxy)",
      "캡컷·캔바·부루의 한국·동남아 1020 MAU 공식 데이터"
    ]
  },
  "storage_guidance": {
    "keep_as_fact": [
      "부루/캡컷/캔바가 글로벌 영상 편집 시장에서 어도비 프리미어와 경쟁한다는 업계 인식",
      "남세동 '워드가 노션 되지 않는다' 발언"
    ],
    "keep_as_inference": [
      "matched_thinking_pattern", "reasoning_move", "consensus_gap",
      "전문툴 장기 디레이팅 시나리오", "신문회사 패턴 적용 가능성"
    ],
    "must_not_store_as_fact": [
      "어도비 프리미어 폐기 시점 단정",
      "디레이팅 시작 분기 단정"
    ]
  }
}


E029 = {
  "card_id": "E029",
  "title": "AI 암묵지 추출 → 매니저 대체",
  "labels": ["ai_tech", "investment_strategy", "risk_factors"],
  "source_origin": "channel_interpretation",
  "source_quality": "medium",
  "framework_used": "platform_shift",
  "matched_thinking_pattern": "AI가 새 도구로 *추가*되는 게 아니라, 사람의 일하는 방식 자체가 *데이터화 → 추출 → 복제* 파이프라인으로 갈아치워진다고 보는 사고",
  "attention_hook": "카카오페이증권 PM이 '두 분의 암묵지를 추출해서 일을 시켜보자'고 자연스럽게 말함. 화자가 의아해한 건 *왜 이게 이미 미국 빅테크·헤지펀드·컨설팅에서 실제 대체로 이어지고 있는가* — Anthropic 매출 월 2배, 빅테크 화이트칼라 감원 누적, 그런데 한국 증권사 RA·PM은 정상 채용 공시.",
  "implicit_question": "AI agent가 *의사결정 책임*까지는 못 지고 *KPI/감사 책임*은 사람에게 묶여 있다면, 화이트칼라 대체는 (a) 매니저 직위 유지·하위 작업 자동화로 *인당 P&L* 점프하는 경로와 (b) 매니저 자체 감원으로 *headcount 컷* 경로 둘 중 어느 쪽이 한국 금융권에서 먼저 발화하는가? Anthropic API 매출 가속도와 한국 증권사 RA 신규 채용 시계열의 *디버전스 시작 시점*이 그 답을 어디서 보여주는가?",
  "reasoning_move": "헤드라인 'AI는 보조 도구 = 일자리 안전'을 거부. (1) 'AI랑 같이 일하라'는 지시 자체가 *추출 후 대체* 파이프라인의 1단계 (소울 추출 → 모델 주입). (2) 미국 빅테크의 화이트칼라 감원(메타·세일즈포스·MS의 백오피스 컷) + 헤지펀드의 AI agent P&L 실험이 *동시 누적*. (3) 한국은 *KPI/감사·라이선스* 규제가 매니저 직위 보호하므로 *headcount 컷*보다 *인당 P&L 점프*가 먼저, 그러나 시점은 한국 증권사 *RA 신규 채용 -20%+ 시계열*에서 잡힘. (4) 따라서 광고 콘텐츠의 일화를 *세계 화이트칼라 채용·Anthropic 매출·한국 RA 채용 시계열 3축*으로 다층화.",
  "consensus_gap": "시장 컨센서스: AI agent는 보조 도구, 화이트칼라 대체는 *5~10년 후* 이슈. 자본시장 가격 = OpenAI/Anthropic 매출 성장에만 반응, 한국 금융권 인력 비용 절감은 미반영. 화자 시각: *이미 1단계가 시작됐고* (소울 추출 프로젝트가 광고에 등장할 정도), 한국에서는 KPI/감사 규제로 *direct 감원이 아니라 신규 채용 동결+인당 P&L 점프*로 먼저 발현. 핵심 차이는 *형태*와 *시점*: 감원이 아니라 채용 동결, 5년 후가 아니라 2026~2027.",
  "bull_case": "화이트칼라 대체 지연 — Anthropic·OpenAI API 매출이 광고·소비자 SaaS 중심으로만 가속, 엔터프라이즈 도입은 컴플라이언스·감사 책임 한계로 2027년+ 지연. 한국 증권사는 RA·PM 직위가 *라이선스 요건*에 묶여 headcount 유지. 미국 빅테크 감원도 AI 때문이 아니라 매크로 사이클로 분류돼 카드 시나리오 일부 무효.",
  "bear_case": "Anthropic API 매출 6개월 연속 MoM 50%+ + 미국 헤지펀드의 AI agent P&L 공식 보고(13F·연간 letter 등장) + 한국 증권사 RA 신규 채용 공시 -20%YoY + 카카오페이증권·미래에셋·삼성 같은 대형사가 '리서치 AI 도입' 공식화 → 한국 화이트칼라 대체 사이클 1단계 진입. 증권주 인력 비용 절감 시나리오 가격에 반영 시작.",
  "monitoring_signals": [
    "Anthropic·OpenAI 엔터프라이즈 API 매출 MoM (Bear: 50%+ 6개월 연속)",
    "한국 증권사(KB·미래에셋·삼성·NH 등) RA·PM 신규 채용 공시 시계열 (Bear: -20%YoY 두 분기 연속)",
    "미국 빅테크 화이트칼라 감원 발표 누적 (Bear: 분기 5,000+ 명 누적 + AI 명시)",
    "헤지펀드 13F·연간 letter에서 'AI agent P&L' 언급 빈도 (Bear: 분기 10건 돌파)",
    "한국 증권사 어닝 콜에서 '리서치 AI 도입·생산성' 멘트 빈도 (선행 지표)"
  ],
  "analyst_view": "화이트칼라 헤드카운트·인당 P&L 카드 — *매수/매도 신호가 아니라* 한국 금융·컨설팅·법률 화이트칼라의 *신규 채용 시계열*과 *Anthropic·OpenAI 엔터프라이즈 매출*의 디버전스를 추적하는 시그널 카드. 광고 콘텐츠 출처라 일화 자체는 디스카운트하되 '소울 추출'이라는 *프로젝트 명칭이 광고에 자연 등장할 정도*라는 점에서 산업 침투 신호로 활용. 신문회사 디버전스(E040)·AI 토큰 권력(E025)과 cross-ref 시 *가치 포획 위치가 사람 → 추출 모델*로 이동하는 평행 사례 누적.",
  "original_signal": "카카오페이증권 AI 서비스센터의 '소울 추출' 프로젝트 데모; 슈카/니니의 성격·말투를 파일로 추출해 종목 분석 AI에 주입; Anthropic 매출 한 달에 두 배씩 증가; 미국 빅테크·헤지펀드·컨설팅에서 매니저 대체 사례 발생 중",
  "trigger_conditions": [
    "AI agent의 매출/사용량이 월 단위 두 배 증가 보도",
    "증권사·컨설팅·헤지펀드에서 AI 도입 후 매니저 감원 케이스",
    "기업 사내에서 'AI와 같이 일하라'는 지시 + 일하는 방식 추출 프로젝트 시작",
    "Anthropic·OpenAI의 엔터프라이즈 매출 가속화",
    "한국 증권사 어닝 콜에서 '리서치 AI·인당 P&L 점프' 멘트 시작",
    "헤지펀드 letter에서 'AI agent P&L' 명시"
  ],
  "causal_chain": "[AI와 같이 일하라는 지시 + 소울 추출 프로젝트] → [일하는 방식이 데이터·파일로 추출됨] → [추출 모델이 매니저의 1차 의사결정·리서치 작업 커버] → [한국은 KPI/감사 규제로 *신규 채용 동결+인당 P&L 점프* 형태로 1단계 발현, 미국은 *직접 감원*] → [Anthropic API 매출 가속도 vs 한국 RA 채용 시계열 디버전스에서 진입 시점 확인 가능]",
  "expected_direction": "bearish_long_conditional — 한국은 채용 동결로 먼저 발현, 시점은 Anthropic 매출·RA 채용 디버전스에 의존",
  "time_horizon": "mid_to_long",
  "confidence": "medium — 광고 영상 단일 화자이나 Anthropic 매출 가속·미국 빅테크 화이트칼라 감원·한국 증권사 RA 채용 시계열로 다층 검증 가능, 광고 콘텐츠 1차 디스카운트 유지",
  "evidence_type": "expert_interpretation_with_quant_proxy",
  "abstraction_level": "medium",
  "technical_depth": "medium",
  "quant_support": "multi_numbers",
  "speaker_views": {
    "카카오페이증권 PM (월터)": "AI랑 같이 일하라고 해놓고 그 사람의 일하는 방식을 추출한 다음 대체하는 일이 미국에서 실제로 벌어지고 있다. 엔트로픽 매출이 월 두 배씩 늘고 있다.",
    "슈카": "지금 증권사 다녔으면 짤렸을 수도 있겠다."
  },
  "source_videos": [
    {
      "video_id": "FhePWOAClXg",
      "channel": "머니코믹스",
      "quote": "AI랑 같이 일하라고 해놓고 그 사람의 일하는 방식이라고 추출을 한 다음에 그분들을 대체하는 일이 실제로 생기고 있거든요. … 엔트로픽의 매출이 한 달에 두 배씩 늘고 있더라고요."
    }
  ],
  "source_references": ["FhePWOAClXg:0:152", "FhePWOAClXg:0:160", "FhePWOAClXg:0:391"],
  "cross_reference_cards": ["E025", "E040"],
  "search_blurb": "AI 암묵지 추출 카카오페이증권 AI agent 매니저 대체 Anthropic 매출 월 두 배 화이트칼라 대체 헤지펀드 매니저 AI 자동화 일하는 방식 데이터화 soul extraction 증권사 RA 채용 시계열 인당 P&L 점프 KPI 감사 책임 라이선스 규제 빅테크 감원",
  "insight_quality": {
    "score_0_to_10": 8,
    "grade": "high",
    "score_reasons": [
      "1차/2차 효과 분리 명확 (보조 도구 → 추출 → 대체)",
      "한국·미국 형태 차이(채용 동결 vs 직접 감원) 분해",
      "Anthropic 매출·RA 채용·헤지펀드 letter 3축 다층 검증",
      "광고 콘텐츠라는 출처 디스카운트 명시",
      "monitoring signal 5개 시계열 검증 가능 + bull/bear case 명시"
    ],
    "quality_test": "platform_shift: AI가 가치 포획 위치를 사람 → 추출 데이터·모델로 옮기는가? — Yes, 1단계는 채용 동결·인당 P&L 점프 형태로 한국에서 먼저 발현",
    "missing_to_upgrade": [
      "한국 증권사 RA·PM 채용 공시 시계열 정량 데이터",
      "헤지펀드 letter에서 'AI agent P&L' 명시 빈도 시계열",
      "Anthropic 엔터프라이즈 매출 vs 컨슈머 매출 분해"
    ]
  },
  "storage_guidance": {
    "keep_as_fact": [
      "Anthropic 매출 월 2배 증가 발언",
      "카카오페이증권 소울 추출 프로젝트 존재",
      "미국 빅테크 화이트칼라 감원 누적 (사실 베이스)"
    ],
    "keep_as_inference": [
      "증권사 매니저 대체 시나리오의 *형태*(채용 동결)와 *시점*",
      "한국 KPI/감사 규제가 직접 감원을 막는다는 가설",
      "expected_direction"
    ],
    "must_not_store_as_fact": [
      "특정 직군 대체 시점 예측",
      "광고 콘텐츠 발언을 객관 데이터로 취급",
      "한국 증권사 RA 채용 감소 *원인*을 AI로 단정 (매크로 변수 분리 필요)"
    ]
  }
}


def update_jsonl(fp: Path, cid: str, new_card: dict) -> bool:
    lines = fp.read_text(encoding="utf-8").splitlines(keepends=True)
    new_lines = []
    found = False
    for l in lines:
        if not l.strip():
            new_lines.append(l)
            continue
        c = json.loads(l)
        if c.get("card_id") == cid:
            new_lines.append(json.dumps(new_card, ensure_ascii=False) + "\n")
            found = True
        else:
            new_lines.append(l)
    fp.write_text("".join(new_lines), encoding="utf-8")
    return found


def main() -> None:
    ok1 = update_jsonl(A2, "E010", E010)
    ok2 = update_jsonl(A4B, "E029", E029)
    print(f"E010 updated: {ok1}")
    print(f"E029 updated: {ok2}")


if __name__ == "__main__":
    main()
