"""R4 U1 업그레이드 — A1/A2 잔여 medium 6장(E003·E005·E007·E009·E011·E012) → high.

신규 필드: consensus_gap, bull_case, bear_case, monitoring_signals, analyst_view, cross_reference_cards.
기존 4 핵심 필드(raw_quote 진정성) 유지, implicit_question만 시점·형태·축으로 정밀화.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
A1 = ROOT / "data" / "r4_cards" / "A1_moneygraphy_top4.jsonl"
A2 = ROOT / "data" / "r4_cards" / "A2_moneygraphy_mid4.jsonl"


# ============ A1: E003 ============
E003 = {
  "card_id": "E003",
  "title": "자식상권 사이클 한계",
  "labels": ["startup_business", "korea_economy"],
  "source_origin": "channel_interpretation",
  "source_quality": "medium",
  "framework_used": "substitution",
  "matched_thinking_pattern": "임대료 밀려난 콘텐츠가 다음 정거장으로 점프하는 것을 *연속 함수*가 아니라 *지형 끝나면 끊기는 단계 함수*로 보는 사고",
  "attention_hook": "홍대→합정→망원, 이태원→경리단→해방촌까지는 이어졌는데, 해방촌 다음은 후암동인데 거긴 왜 안 뜨지? 빌라 8가구 조별과제가 재개발보다 어렵다잖아.",
  "implicit_question": "자식상권 사이클이 후암동·신당 같은 *용도지역 장벽*에서 멈추는 게 정해진 함수라면, 다음 핫플 후보지가 발표될 때마다 (a) 1종/2종 주거 빌라 비중 (b) 평균 필지 소유자 수 (c) 지구단위계획 변경 신청 건수 — 이 세 지표 중 어느 것이 *임대료 점프 6~12개월 전*에 핫플 가능성을 가르는 선행 지표인가?",
  "reasoning_move": "1차 해석=홍대→합정→망원처럼 자동으로 다음 동네가 뜬다는 연속 가정 거부. 후암동이 못 뜨는 이유를 *빌라 한 동에 8가구 의견 합치가 재개발보다 어렵다*는 행정·소유 구조 변수로 추가 → 해방촌이 마지막 정거장임을 단정. 즉 외국인타운은 다음 세대에 못 볼 수 있다는 비관 시나리오.",
  "consensus_gap": "시장 컨센서스: 젠트리피케이션은 인접 동네로 자동 점프하므로 '다음 핫플'은 항상 존재 (강북 부동산 미디어의 표준 내러티브). 화자 시각: 사이클은 *용도지역·소유 분산도*라는 구조 장벽에 부딪히는 순간 *끊긴다*. 핵심 차이는 *축*: 시장은 시간·거리 함수로 보고, 화자는 토지 행정 변수로 본다 — 따라서 시장이 후보지로 미는 동네를 화자는 *사이클 종착지*로 분류.",
  "bull_case": "사이클 연장 — 서울시·중구·용산구가 후암동·해방촌 일대를 지구단위계획으로 묶어 상업화 인센티브(용적률·층수 완화) 부여. 리츠·법인이 8가구 빌라 블록을 통매입해 소유 분산 문제 우회. 후암동 카페·F&B 신규 오픈이 분기 10개+ 누적되면 '용도지역 장벽 = 사이클 종착' 시나리오 무력.",
  "bear_case": "해방촌 평균 임대료 평당 30만원+ 4분기 연속 유지 + 후암동·신당 신규 F&B 폐업률 50%+ + 콘텐츠 사업자 인터뷰에서 '갈 곳이 없다' 발언 빈도 증가. 동시에 신당·을지로(힙지로)가 세운상가 재개발 명도로 시한부 확정되면 *부모-자식 사이클 종료 + 새 발화점 부재* 동시 진행. 강북 외식·콘텐츠 신규 창업 데이터 1년 누적 -20%YoY 진입.",
  "monitoring_signals": [
    "후암동·해방촌·신당·을지로 신규 F&B 인허가 건수 시계열 (Bear 트리거: 후암 신규 인허가 분기 5건 미만 + 해방촌 폐업이 신규 초과)",
    "서울시 지구단위계획·용도지역 변경 신청·고시 건수 (Bull 트리거: 후암·해방촌 지정 신청)",
    "리츠·법인 명의 빌라/건물 매입 등기 시계열 (Bull 트리거: 후암동 블록 단위 통매입 3건+)",
    "해방촌·후암동 평균 임대료·권리금 호가 (Bear 트리거: 해방촌 임대료 4분기 정체 + 후암동 호가 답보)",
    "유튜브·인스타그램 '후암동 카페·신당 맛집' 콘텐츠 발행량 (선행 지표 — 사이클 발화 6~12개월 전 신호)"
  ],
  "analyst_view": "상권 사이클 종착 분류 카드 — *부동산 매수 신호가 아니라* '다음 핫플은 어디인가' 질문을 받았을 때 후보지의 *용도지역·소유 분산도*부터 스크리닝해서 *사이클 도착 가능 종착지*와 *사이클 종료 동네*를 분리하는 시그널 카드. E001(잔존가치) cross-ref와 결합 시 '잔존가치 있는데 사이클 못 옴'(후암동) vs '잔존가치 없고 사이클도 끝'(합정) 같은 4분면 분류 가능. F&B 창업·임대 의사결정 일차 스크리닝 도구.",
  "original_signal": "홍대(부모) 메인 사망→합정 사망→망원·연남 분기, 연남만 생존; 이태원(부모) 사망→경리단(자식) 비리비리→해방촌까지 옴; 해방촌 너머 후암동은 2종 주거 빌라촌; 빌라 8가구 합의 = 상업개발 불가",
  "trigger_conditions": [
    "해방촌 임대료 추가 인상 뉴스",
    "후암동·삼각지·남영동 상권 확장 시도와 실패 사례",
    "1종↔2종 주거지 용도지역 변경 정책",
    "을지로(세운상가) 재개발 명도 진행으로 힙지로 가게 신당 동진",
    "재개발 시행사 결정으로 권리금 회수 불가 발생"
  ],
  "causal_chain": "[부모 상권 임대료 폭등] → [콘텐츠가 인접 자식 상권으로 점프] → [자식도 임대료 따라옴] → [2종 주거 빌라 블록·다수 소유자 분산이 상업화 차단] → [사이클 종료 = 다음 핫플 후보지 부재]",
  "expected_direction": "bearish_long",
  "time_horizon": "long",
  "confidence": "low — 단일 영상·단일 화자(유정수) 핵심, 시계열 사례는 풍부",
  "evidence_type": "speaker_inference",
  "abstraction_level": "medium",
  "technical_depth": "medium",
  "quant_support": "none",
  "speaker_views": {
    "유정수": "이태원이 부모, 경리단·한남동이 자식이었는데 부모 죽고 자식까지 비리비리. 망원처럼 해방촌으로 넘어왔는데 그 다음은 후암동이 다 2종 주거 빌라라서 못 간다.",
    "안스타": "F&B는 임대료 따라 동쪽으로 밀려나는데 신당이 그 다음이고, 을지로(힙지로)는 세운상가 재개발로 통째 시한부다."
  },
  "source_videos": [
    {
      "video_id": "Ut3cNLwXgto",
      "channel": "머니그라피",
      "quote": "해방촌 넘어선 후암동인데 후암동은 싹 다 2종 주거예요. 빌라 8가구 의견 맞추는 게 재개발하는 것보다도 어렵습니다. 안 돼요."
    }
  ],
  "source_references": ["Ut3cNLwXgto:2:1112", "Ut3cNLwXgto:2:1167", "Ut3cNLwXgto:2:1175", "Ut3cNLwXgto:2:1409"],
  "cross_reference_cards": ["E001", "E005"],
  "search_blurb": "자식상권 부모상권 젠트리피케이션 홍대 합정 망원 이태원 경리단 해방촌 후암동 2종주거 빌라촌 신당동 을지로 힙지로 시한부 상권사이클 용도지역 지구단위계획 소유분산도 8가구 합의 리츠 통매입",
  "insight_quality": {
    "score_0_to_10": 8,
    "grade": "high",
    "score_reasons": [
      "지형·용도지역이라는 *구조 변수*를 시간 함수보다 우선 도입",
      "consensus_gap을 시간·거리 축 vs 행정 변수 축으로 분리",
      "monitoring signal 5개 — 선행 지표(SNS 발행량) 포함",
      "bull/bear case에서 리츠 통매입·지구단위계획 변경이라는 무효화 조건 명시",
      "E001·E005와 cross-ref로 4분면 분류 도구화"
    ],
    "quality_test": "다음 핫플 추천 뉴스를 보고, 그 지역의 용도지역과 소유 구조부터 확인해 *사이클이 도착할 수 있는 종착지인가*를 판단할 수 있는가? — Yes.",
    "missing_to_upgrade": [
      "용도지역 변경 정책 변수의 정량 효과 (서울시 사례 history)",
      "리츠·법인 매입으로 8가구 문제 우회 사례 빈도 시계열"
    ]
  },
  "storage_guidance": {
    "keep_as_fact": ["후암동 2종 주거", "8가구 합의 난이도"],
    "keep_as_inference": ["matched_thinking_pattern", "reasoning_move", "consensus_gap", "다음 핫플 단정"],
    "must_not_store_as_fact": ["해방촌 5년 후 사망 단정", "후암동 영구 비상권화 단정"]
  }
}


# ============ A1: E005 ============
E005 = {
  "card_id": "E005",
  "title": "공장 잔존가치 자가훼손",
  "labels": ["startup_business", "investment_strategy"],
  "source_origin": "speaker_inference",
  "source_quality": "medium",
  "framework_used": "commoditization",
  "matched_thinking_pattern": "상권의 차별화 자산을 *임대 수익 극대화*를 위해 본인이 직접 파괴하면서 결국 강남화·획일화로 떨어지는 자기파괴 동학을 읽는 사고",
  "attention_hook": "성수가 위기라는데 왜 위기야? 임대료 오른 거 말고 — 건물주들이 황금알 낳는 거위를 직접 가르고 있다는 거잖아. 공장형 창고가 색깔의 본체였는데 그걸 16층으로 갈아엎으면 그게 강남이지 성수냐.",
  "implicit_question": "성수의 '잔존가치=붉은벽돌 공장' 자산이 *건물주의 단기 NPV 극대화 선택*으로 자가 침식되고 있다면, 차별성 소실은 어느 시점에 임대료·F&B 객단가 데이터로 처음 드러나는가? (a) 공장형 신축 비중이 50% 돌파하는 분기 (b) F&B 폐업이 패션·향수 입점을 초과하는 분기 (c) 외국인 방문 객단가가 강남과 수렴하는 분기 — 어느 선행 지표가 자가훼손 임계를 가장 빨리 잡는가?",
  "reasoning_move": "1차 해석=성수 임대료 폭등=상권 성숙으로 호재라는 시각 거부. 용적률 400% + 무신사·젠틀몬스터의 건물 매입 → 한층 공장 철거 후 12~16층 신축 → 색깔 사라짐 = '강남 신도시'와 차별점 소실. 즉 잔존가치를 만드는 주체와 파괴하는 주체가 동일인이라는 *내부 모순*을 변수로 추가, 성수의 향후 5년 차별성 소실을 단정.",
  "consensus_gap": "시장 컨센서스: 성수동 임대료 폭등·신축 러시 = 상권 성숙 신호, 랜드마크 강화 (강북 부동산·F&B 미디어 표준 내러티브). 화자 시각: 같은 데이터를 *차별성 자산이 합리적 단기최적화로 자가훼손되는 동학*으로 재해석 — 강남화 가속. 핵심 차이는 *형태*: 시장은 임대료 = 가치 동의어로 보고, 화자는 임대료 상승이 *원천 자산(공장형 건물) 파괴 인센티브*를 만든다는 역설을 본다.",
  "bull_case": "성수 차별성 유지 — 서울시·성동구가 지구단위계획·역사문화환경 보전지구로 일부 공장 블록을 묶어 신축 제한. 무신사·젠틀몬스터 같은 대형 매입자가 *외관 보전 + 내부 리노베이션* 전략으로 전환 (도쿄 다이칸야마·뉴욕 미트패킹 모델). 공장형 외관 보존 건물 비중이 50%+ 유지되면 자가훼손 시나리오 부분 무력.",
  "bear_case": "성수동 1·2가 신축 12~16층 비중이 5년 누적 50%+ 돌파 + F&B 신규 폐업이 입점 초과 4분기 연속 + 권리금 7억+ 거래가 패션·향수·안경 카테고리에만 집중. 외국인 객단가가 강남(청담·도산)과 수렴하기 시작하면 *성수 = 강남 동쪽 분점* 인식 확산, 임대료 사이클 정점 도래.",
  "monitoring_signals": [
    "성수동 1·2가 신축 인허가·착공 건수 시계열 + 신축/총 건물 비중 (Bear 트리거: 분기 신축 비중 5%+ 가속)",
    "성수 권리금·임대료 카테고리별 분포 (Bear 트리거: F&B 권리금 정체 + 패션·향수 권리금만 상승)",
    "F&B 신규 입점 vs 폐업 비율 (Bear 트리거: 폐업 > 입점 4분기 연속)",
    "서울시·성동구 지구단위계획·보전지구 지정 공고 (Bull 트리거: 공장 블록 보전 지정)",
    "외국인 결제 데이터 (BC카드·신한카드 공개분) 성수 vs 청담 객단가 수렴도 (선행 지표)"
  ],
  "analyst_view": "상권 자가훼손 동학 카드 — *부동산 매수/매도 신호가 아니라* '핫플 임대료 상승 = 호재' 1차 인과를 받았을 때 *차별성 자산이 같은 주체에 의해 파괴되는 역설*을 점검하는 시그널 카드. E001(잔존가치)과 E003(자식상권 한계)과 cross-ref 시 '잔존가치 있음 + 자가훼손 없음'(북촌·연남) vs '잔존가치 있음 + 자가훼손 진행'(성수) vs '잔존가치 없음'(합정)의 3분면 분류 가능. 도쿄·뉴욕 비교 사례까지 일반화하면 *임대료 상승이 가치 파괴 인센티브가 되는 모든 상권*에 적용 가능한 메타 카드.",
  "original_signal": "성수동 용적률 400%, 공장형 창고 철거 후 12~16층 신축 다수; 무신사·젠틀몬스터가 가장 많이 매입 후 새 건물; 권리금 2~5~7억(광장시장 15평 10억) → 개인 진입 불가; F&B 영업이익 불가, 패션·안경·향수만 생존",
  "trigger_conditions": [
    "성수동 신축 인허가·착공 증가",
    "무신사·젠틀몬스터 부동산 매입·재건축 공시",
    "성수 권리금 시세 추가 상승",
    "성수 카페·F&B 폐업 비중 증가",
    "용도지역·용적률 정책 변화"
  ],
  "causal_chain": "[공장형 창고 = 성수 잔존가치 본체] → [용적률 400% + 임대료 폭등이 신축 NPV 극대화 유인] → [건물주가 잔존가치 자가파괴 (16층 신축)] → [F&B 영업이익 불가 → 패션·향수·안경만 입점 가능 → 다양성 소실] → [성수 = 강남 동쪽 분점화, 외국인 객단가까지 수렴]",
  "expected_direction": "bearish_long",
  "time_horizon": "long",
  "confidence": "medium — 단일 영상·핵심 화자 1명(유정수)이나 매입 사례·권리금·F&B 폐업 등 정량 데이터 다층 검증 가능",
  "evidence_type": "speaker_inference",
  "abstraction_level": "medium",
  "technical_depth": "medium",
  "quant_support": "one_or_two_numbers",
  "speaker_views": {
    "유정수": "성수동 위기는 임대료가 아니라 건물주가 황금알 낳는 거위 배를 가르는 거다. 공장 잔존가치가 본체인데 그걸 부수면 강남이랑 차별이 없어진다.",
    "안스타": "성수 권리금이 너무 세서 개인 단위 진입은 불가, 들어가는 건 큰 기업과 패션·안경·향수 같은 영업이익 높은 카테고리뿐이라 다양성이 죽는다."
  },
  "source_videos": [
    {
      "video_id": "Ut3cNLwXgto",
      "channel": "머니그라피",
      "quote": "성수동이 위기인 이유가 임대료가 너무 올랐기 때문만이 아니라 임대료가 오르니까 성수동 건물주들이 황금알을 낳는 거위에 배를 가르기 시작했어요. 공장 창고를 부수고 16층짜리 건물을 짓는 거예요."
    }
  ],
  "source_references": ["Ut3cNLwXgto:2:1005", "Ut3cNLwXgto:2:1015", "Ut3cNLwXgto:2:1031", "Ut3cNLwXgto:2:1089"],
  "cross_reference_cards": ["E001", "E003"],
  "search_blurb": "성수동 용적률 공장형 창고 무신사 젠틀몬스터 권리금 광장시장 강남화 잔존가치 자가훼손 F&B 패션브랜드 팝업스토어 부동산 재건축 자기파괴 동학 보전지구 지구단위계획 다이칸야마 미트패킹",
  "insight_quality": {
    "score_0_to_10": 8,
    "grade": "high",
    "score_reasons": [
      "잔존가치 모델의 *자가 침식* 메커니즘을 일반화 (도쿄·뉴욕 비교 사례)",
      "consensus_gap을 형태 차이로 분리 (임대료=가치 vs 임대료=파괴 인센티브)",
      "monitoring signal 5개 — 외국인 객단가 수렴이라는 선행 지표 포함",
      "bull case에 도시계획 정책 무효화 조건 명시",
      "E001·E003과 3분면 분류 도구화"
    ],
    "quality_test": "성수동 신축 인허가 뉴스를 받았을 때 '랜드마크 강화'가 아니라 '차별성 소실 가속'으로 다시 읽을 수 있는가? — Yes.",
    "missing_to_upgrade": [
      "지구단위계획·공장지역 보존 조례 변수의 정량 효과",
      "기업 매입의 임대 vs 자가 사용 비중 시계열",
      "도쿄·뉴욕 보전 모델 대비 한국 정책 갭"
    ]
  },
  "storage_guidance": {
    "keep_as_fact": ["용적률 400%", "성수 권리금 2~7억"],
    "keep_as_inference": ["matched_thinking_pattern", "reasoning_move", "consensus_gap", "차별성 소실 단정"],
    "must_not_store_as_fact": ["성수 5년 후 강남화 단정", "외국인 객단가 수렴 단정"]
  }
}


# ============ A2: E007 ============
E007 = {
  "card_id": "E007",
  "title": "AI 패턴 발견 → 전문가 SaaS 침식",
  "labels": ["ai_tech", "us_equity_market", "single_stock_move"],
  "source_origin": "channel_interpretation",
  "source_quality": "medium",
  "framework_used": "substitution",
  "matched_thinking_pattern": "특정 도메인 전문가의 '암묵지'를 AI가 공식화한 순간, 그 도메인 전문 SaaS의 미래 캐시플로우부터 깎아 본다",
  "attention_hook": "어도비는 매출도 영업이익도 역대 최고로 찍는데 주가는 30~40% 빠진다. 실적이 좋은데 왜? 라는 질문이 화자를 끌고 들어간다.",
  "implicit_question": "어도비·세일즈포스·아토라시안의 *실적 비트와 주가 디레이팅 디버전스*가 이미 시작됐다면, 다음 단계는 (a) 신규 라이트 유저 이탈이 ARR 가이던스에 처음 반영되는 분기 (b) 챗GPT/Cursor가 PSD·DWG 등 전문 확장자를 네이티브 지원하는 발표 시점 (c) AI 네이티브 진입자(Cursor, Lovable)의 ARR이 어도비 Creative Cloud ARR 성장률을 추월하는 분기 — 어느 신호가 *디레이팅 2단계 (가이던스 컷)*를 가장 먼저 알리는가?",
  "reasoning_move": "헤드라인은 'AI 수혜 IT'인데, 화자는 1차 인과(매출=주가)를 끊고 'AI가 못 풀던 회계 부정·법인 셋업·영상 효과음 위치 같은 모호한 패턴까지 공식화한다'는 남세동의 관찰을 함수에 넣음 → 어도비·세일즈포스·오토데스크·지라처럼 '전문가 패턴'에 기대 마진을 빨던 SaaS는 신규 유입(부루·러버블·바이브 코딩)에서부터 시장이 빠진다고 점프.",
  "consensus_gap": "시장 컨센서스: 어도비·세일즈포스 등 엔터프라이즈 SaaS는 락인·전환비용·번들로 AI 시대에도 멀티플 유지 (BofA를 제외한 대다수 sell-side). 화자 시각: 실적이 멀쩡한 동안에도 *신규 라이트 유저 진입로*에서 substitution이 진행되며, 디레이팅은 매출 컷보다 *2~4분기 앞*에 일어난다. 핵심 차이는 *시점·축*: 시장은 매출·ARR 가이던스 컷 시점을 멀티플 처벌 기준으로 보고, 화자는 *신규 결제 코호트 진입 채널 시프트*를 본다.",
  "bull_case": "전문가 SaaS 디레이팅 지연 — 어도비 Firefly·Acrobat AI 통합으로 *AI 네이티브 라이트 유저까지 자체 흡수*. PSD·AI·DWG·JIRA 같은 전문 확장자·워크플로우의 *조직 단위 락인*이 컴플라이언스·감사 책임으로 5년+ 유지. 어도비·세일즈포스·아토라시안 RPO 25%+ 4분기 연속 + 신규 결제자 평균 연령 안정 시 substitution 시나리오 후순위.",
  "bear_case": "Cursor AI·Lovable·Vrew·Canva의 ARR 합계 1년 누적 +200% + 어도비·아토라시안 신규 결제 -10%YoY 동반 + 챗GPT/Gemini가 PSD·DWG 네이티브 지원 공식 발표 + 어도비 어닝콜에 'creative subscriptions 신규 결제자 연령' 첫 언급. 이 4개가 한 분기에 겹치면 컨센서스가 신규 진입 channel shift를 인정, 멀티플 디레이팅 2단계 (가이던스 컷) 본격화.",
  "monitoring_signals": [
    "어도비·세일즈포스·아토라시안·오토데스크 분기 RPO·신규 결제 가이던스 (Bear: 두 분기 연속 컨센 미스 + 신규 결제 YoY 둔화)",
    "Cursor AI·Lovable·Vrew·Canva 글로벌 ARR 시계열 (Bear: 합계 1년 +200% 이상)",
    "챗GPT/Gemini의 전문 확장자(PSD·AI·DWG) 네이티브 지원 발표 (Bear 트리거 — 발표 자체가 신호)",
    "BofA·MS·GS sell-side의 'AI loser' 리스트 변화 (선행 지표 — 명단 추가 = 컨센서스 시프트 시작)",
    "어도비·아토라시안 어닝콜에 '신규 결제자 연령·신규 진입 채널' 멘트 빈도 (선행 지표 — 첫 언급이 진짜 신호)"
  ],
  "analyst_view": "엔터프라이즈 SaaS substitution 시점 추적 카드 — *어도비·세일즈포스 매도 신호가 아니라* '실적 비트 + 주가 하락' 디버전스를 받았을 때 (a) 헤비 유저 락인이 깨졌는지 (b) 신규 진입 채널이 시프트됐는지 (c) sell-side 컨센서스가 어디까지 인정했는지를 3축으로 추적하는 시그널 카드. E010(전문툴 vs 쉬운툴) cross-ref와 결합 시 '재무제표 선행 신호'를 *코호트 연령 + 신규 결제 ARR 디버전스* 두 축으로 동시 검증. 헤비 유저 락인 자체는 의심하지 않음 — 의심하는 건 *신규 진입 분배*.",
  "original_signal": "어도비 분기 매출 35조·영업이익 12조 역대 최고에도 주가 1년간 30~40% 하락; 세일즈포스 1년 -27%, 아틀라시안(지라) -40%; BofA가 'AI에 가장 타격받을 기업'으로 어도비 지목; 챗GPT가 어도비 PSD/AI 확장자 끌어안음",
  "trigger_conditions": [
    "AI에 타격받을 기업 리스트(BofA 등) 발표",
    "어도비·세일즈포스·오토데스크·아틀라시안 등 전문가용 SaaS 분기 실적 비트에도 주가 음의 반응",
    "챗GPT/재미나이가 특정 전문 확장자(PSD, AI, .dwg)를 네이티브로 지원한다는 발표",
    "Cursor AI 같은 신규 진입자의 ARR이 1년 만에 10억 달러 돌파",
    "어도비·아토라시안 어닝콜에 '신규 결제자 연령' 첫 멘트"
  ],
  "causal_chain": "[AI가 모호한 도메인 패턴(회계 부정·영상 편집·CAD 설계)을 학습] → [전문가용 SaaS의 라이트 유저 신규 유입이 쉬운 AI 툴(Cursor·Vrew·Lovable)로 이탈] → [기존 충성 헤비 유저 매출은 유지되지만 신규 코호트 단절이 시작] → [실적 비트해도 멀티플 디레이팅 1단계 (현재) → 신규 결제 가이던스 컷 시 2단계 진입] → [최종적으로 헤비 유저 자연감소가 가이던스 ARR을 추월하는 분기에 디레이팅 완료]",
  "expected_direction": "bearish_long",
  "time_horizon": "long",
  "confidence": "medium — 2개 화자(남세동·이재용) 일치, 구체 종목·실적 숫자 5건 이상, sell-side(BofA) 컨센서스 일부 동조",
  "evidence_type": "mixed",
  "abstraction_level": "medium",
  "technical_depth": "medium",
  "quant_support": "multi_numbers",
  "speaker_views": {
    "남세동": "회계 부정의 공식도, 영상 효과음 위치의 패턴도 결국 다 있다. 모호하다고 믿었던 전문가 영역이 AI에 잡힌다.",
    "이재용": "전문가용·특화 소프트웨어는 결국 부루·재미나이·GPT 같은 말랑한 툴로 대체될 거라는 가정이 주가에 선반영되고 있다."
  },
  "source_videos": [
    {
      "video_id": "6zXcw8lf_zo",
      "channel": "머니그라피",
      "quote": "특화된 소프트웨어들이 결국은 재미나이나 GPT 혹은 부르와 같은 말랑말랑한 좀 더 쉬운 툴로써 대체가 될 것이라는 가정하에 이런 식으로 주가가 반영되고 있는 거죠"
    }
  ],
  "source_references": ["6zXcw8lf_zo:7:920", "6zXcw8lf_zo:7:927", "6zXcw8lf_zo:7:940", "6zXcw8lf_zo:5:500"],
  "cross_reference_cards": ["E008", "E010"],
  "search_blurb": "Adobe Salesforce Atlassian Jira Autodesk SaaS AI substitution vibe coding Cursor ARR 어도비 디레이팅 전문가툴 챗GPT PSD 확장자 BofA AI loser 신규 결제 코호트 신규 진입 채널 시프트 sell-side 컨센서스",
  "insight_quality": {
    "score_0_to_10": 8,
    "grade": "high",
    "score_reasons": [
      "디레이팅 1단계(현재)와 2단계(가이던스 컷)를 시점으로 분리",
      "consensus_gap을 매출 컷 시점 vs 신규 채널 시프트 시점 축 차이로 명시",
      "monitoring signal 5개 — 챗GPT 확장자 지원이라는 단발성 트리거 포함",
      "bull case에 락인·번들 유지 시나리오 명시 (시나리오 균형)",
      "E008(CapEx)·E010(전문툴 vs 쉬운툴)과 cross-ref로 SaaS 디레이팅 종합 추적 가능"
    ],
    "quality_test": "이 카드는 'AI 수혜=빅테크' 헤드라인에만 머무르지 않고 전문가용 SaaS의 어느 사용자층(신규 라이트 유저)부터 빠지는지를 분리해서 본다 — substitution이 가격이 아닌 진입로에서 일어남을 추적",
    "missing_to_upgrade": [
      "어도비·세일즈포스·아토라시안 KPI(신규 결제 코호트 ARPU·평균 연령) 13F·sell-side 데이터",
      "Cursor·Lovable·Vrew의 엔터프라이즈 침투율 정량 시계열",
      "PSD/AI/DWG 확장자 호환성 임계점 (헤비 유저 이탈 트리거)"
    ]
  },
  "storage_guidance": {
    "keep_as_fact": [
      "어도비 분기 매출 35조·영업이익 12조",
      "세일즈포스 1년 -27%, 아틀라시안 -40%",
      "BofA가 어도비를 AI 타격 1순위 지목"
    ],
    "keep_as_inference": ["matched_thinking_pattern", "reasoning_move", "consensus_gap", "expected_direction"],
    "must_not_store_as_fact": [
      "어도비가 망한다는 단정",
      "디레이팅 2단계 진입 시점 단정",
      "신규 유저 이탈률 추정치"
    ]
  }
}


# ============ A2: E009 ============
E009 = {
  "card_id": "E009",
  "title": "1인당 매출 허들 5억 → 10억",
  "labels": ["ai_tech", "startup_business", "investment_strategy"],
  "source_origin": "speaker_inference",
  "source_quality": "medium",
  "framework_used": "operating_leverage",
  "matched_thinking_pattern": "회사 평가의 단위경제 기준선 자체가 점프했는지(허들이 옮겨갔는지)부터 확인하는 사고",
  "attention_hook": "IT 잘하는 회사 기준이 '1인당 매출 5억'이었는데 어느새 10억으로 바뀌었다. Cursor AI는 150명에 ARR 1조 5천억, 1인당 100억. 이건 그냥 잘하는 회사 줄세우기가 아니라 '기준선' 자체가 옮겨간 상황 같다.",
  "implicit_question": "1인당 매출 허들이 5억→10억으로 점프했다면 (한국 IT sell-side·PE 밸류에이션 적용 기준), 기존 인력 베이스 SaaS의 디스카운트는 (a) 신규 채용 동결이라는 *고용 컷 형태*로 발현되는지 (b) 구조조정이라는 *headcount 컷 형태*로 발현되는지 (c) 인수합병이라는 *지배구조 컷 형태*로 발현되는지 — 한국에서는 어느 형태가 먼저 그리고 어느 분기에 발화하는가?",
  "reasoning_move": "1차 인과는 'AI 회사 매출 성장 = 좋음'인데, 화자는 한 칸 뒤로 빠져 '1인당 매출액 기준선' 자체가 무엇인가를 함수로 둠 → IT 5억→10억, Cursor 100억, 두나무 20억을 같은 축에 놓고 '이건 근본 없는 숫자'라고 표현 → 기존 인력 베이스 SaaS는 이 새 허들에 못 미치면 자동 디스카운트된다는 식으로 점프.",
  "consensus_gap": "시장 컨센서스: AI 네이티브 기업의 1인당 매출 100억은 *예외적 outlier*로 일반 SaaS 밸류에이션에 적용 불가 (한국 sell-side·VC 표준). 화자 시각: outlier가 아니라 *허들 점프*. 기존 SaaS는 같은 매출이어도 디스카운트가 시작됐고, 이는 단발성이 아니라 연속 사이클. 핵심 차이는 *축*: 시장은 1인당 매출을 회사간 비교 metric으로 보고, 화자는 *시계열 허들 함수*로 본다 — 따라서 시장이 '예외'라고 부르는 숫자가 화자에게는 *새 평균선*.",
  "bull_case": "1인당 매출 허들 점프 무효 — Cursor·Anthropic 같은 AI 네이티브 ARR이 *컴퓨팅 비용·API 마진 압박*으로 1인당 *영업이익* 기준으로 환산하면 기존 SaaS와 큰 차이 없음. 한국 IT의 단위경제 허들은 *매출이 아니라 영업이익률*로 재정의되어 기존 인력 베이스 회사가 디스카운트 회피. 두나무·네이버·카카오 IT 자회사 1인당 영업이익이 Cursor 수준 유지 시 시나리오 무력.",
  "bear_case": "Cursor·Lovable·Perplexity 같은 AI 네이티브의 1인당 매출이 100억+ 유지 + 한국 IT 대기업 신규 채용 공시 -20%YoY 두 분기 연속 + 국내 SaaS 분기 IR에서 'AI 생산성 점프·인당 매출' 멘트 빈도 증가 + PE·VC 밸류에이션 기사에 '1인당 매출 멀티플 적용' 표현 등장 — 이 4개가 한 분기에 겹치면 한국 IT 노동시장 진입 모델 자체가 재편 시작.",
  "monitoring_signals": [
    "AI 네이티브 기업(Cursor·Anthropic·Perplexity·Lovable) ARR/직원수 공개 시계열 (Bear: 1년+ 1인당 100억 유지)",
    "한국 IT 대기업(네이버·카카오·NHN 등) 신규 채용 공시 시계열 (Bear: -20%YoY 두 분기 연속)",
    "국내 SaaS·IT 분기 IR에서 'AI 생산성·1인당 매출' 멘트 빈도 (선행 지표)",
    "PE·VC sell-side 보고서의 '1인당 매출 멀티플' 표현 등장 빈도 (선행 지표 — 컨센서스 시프트 신호)",
    "두나무·네이버 IT 자회사 1인당 영업이익 시계열 (Bull 트리거: Cursor 수준 영업이익률 달성 시 시나리오 약화)"
  ],
  "analyst_view": "단위경제 허들 시프트 카드 — *AI 종목 매수 신호가 아니라* 한국 IT·SaaS·PE 밸류에이션을 받았을 때 '1인당 매출 기준선이 어디에 있는가'를 먼저 확인하는 시그널 카드. E012(신입 안 뽑는 시대)와 cross-ref 시 *허들 점프 → 신규 채용 동결 → 노동시장 진입 모델 재편*의 3단 연쇄를 추적. E007(전문가 SaaS substitution)·E029(AI 매니저 대체)와 결합 시 *AI 시대의 인력 비용 함수 재정의*라는 메타 가설 검증용. 매출이 아니라 영업이익 기준 허들로 재정의 가능성도 동시 점검.",
  "original_signal": "Cursor AI ARR 약 10억 달러(1조 5천억), 직원 약 150명, 1인당 매출 약 100억 원; 한국 IT 회사 잘한다 기준 5억→10억으로 이동; 두나무 1인당 매출 약 20억; 보이저X 매출 100억 미만, 영업손실 수십억",
  "trigger_conditions": [
    "AI 네이티브 기업의 ARR/직원수 공개(Cursor, Anthropic, Perplexity)",
    "기존 SaaS·IT 기업의 1인당 매출액 컴퍼러블 발표",
    "벤처·PE 밸류에이션 시 1인당 매출 멀티플 적용 기사",
    "구조조정·인력 축소 공시(생산성 정상화)",
    "한국 IT 대기업 분기 IR에 '1인당 매출·AI 생산성' 멘트 시작"
  ],
  "causal_chain": "[AI 네이티브 기업이 소수 인력으로 ARR 빠르게 점프 (Cursor 150명·ARR 10억$)] → [업계 1인당 매출 허들 기준선 자체가 5억→10억 + outlier로 100억 점프] → [PE·VC·sell-side가 1인당 매출을 *시계열 허들*로 재정의] → [기존 인력 베이스 SaaS·IT 기업은 같은 매출이어도 디스카운트 + 신규 채용 동결로 1인당 매출 방어] → [노동시장 진입 모델 변화 (E012 cross-ref) + 구조조정 가속]",
  "expected_direction": "mixed",
  "time_horizon": "mid",
  "confidence": "medium — 화자 2명(남세동·이재용) 1인당 매출 기준점 일치 언급, 구체 회사 3곳 수치, 매출 vs 영업이익 허들 정의 미합의",
  "evidence_type": "mixed",
  "abstraction_level": "medium",
  "technical_depth": "medium",
  "quant_support": "multi_numbers",
  "speaker_views": {
    "이재용": "근본 없는 숫자. 한국 두나무 1인당 매출 20억이 큰데 Cursor는 100억이다. 1인당 매출 허들이 점프하고 있다.",
    "남세동": "주니어를 안 뽑는 세상으로 이미 바뀌었다. 코딩 80%를 AI가 한다."
  },
  "source_videos": [
    {
      "video_id": "6zXcw8lf_zo",
      "channel": "머니그라피",
      "quote": "커서 AI 같은 회사는... AR 10억불 정도 나온다고... 직원이 150명이래요. 1인당 매출 100억. 근본 없는 숫자거든요. 한국에서 1인당 매출이 큰 회사 중에 하나가 두나무... 20억 정도 나와요."
    }
  ],
  "source_references": ["6zXcw8lf_zo:3:275", "6zXcw8lf_zo:3:283", "6zXcw8lf_zo:3:290", "6zXcw8lf_zo:10:996"],
  "cross_reference_cards": ["E007", "E012"],
  "search_blurb": "1인당 매출 ARR Cursor Anthropic 두나무 보이저엑스 단위경제 SaaS 허들 디레이팅 신입채용 위축 주니어 안 뽑는 시대 AI 생산성 점프 허들 시프트 PE VC 밸류에이션 멀티플 영업이익률 노동시장 재편",
  "insight_quality": {
    "score_0_to_10": 8,
    "grade": "high",
    "score_reasons": [
      "허들이 *시계열 함수*인지 *비교 metric*인지 축 차이를 명시",
      "consensus_gap에서 outlier vs 새 평균선 인식 차이 분리",
      "bull case에 '매출 허들 → 영업이익 허들 재정의' 무효화 조건 명시",
      "monitoring signal 5개 — sell-side 표현 등장이라는 선행 지표 포함",
      "E007·E012·E029와 cross-ref로 AI 인력 비용 함수 메타 가설 추적"
    ],
    "quality_test": "operating_leverage로 단위경제·1인당 매출 기준선 변화에 집중. '잘하는 회사'의 정의가 점프하는 regime change를 회사 단위로 분해",
    "missing_to_upgrade": [
      "전 산업 1인당 매출 분포 변화 정량 데이터 (sell-side 컴퍼러블 보고서)",
      "AI 네이티브 기업의 컴퓨팅 비용·API 마진 시계열 (1인당 영업이익 환산)",
      "기존 IT 회사 인력 베이스 조정 속도 (구조조정 분기별)"
    ]
  },
  "storage_guidance": {
    "keep_as_fact": [
      "Cursor AI ARR 10억 달러·150명",
      "두나무 1인당 매출 약 20억",
      "한국 IT 잘하는 회사 기준 5억→10억 이동(업계 통념)"
    ],
    "keep_as_inference": ["matched_thinking_pattern", "reasoning_move", "consensus_gap", "expected_direction"],
    "must_not_store_as_fact": [
      "향후 모든 IT 기업이 1인당 100억을 달성해야 한다는 단정",
      "Cursor 1인당 영업이익 단정"
    ]
  }
}


# ============ A2: E011 ============
E011 = {
  "card_id": "E011",
  "title": "취향 소멸 시대 브랜드 재부상",
  "labels": ["brand_strategy", "ai_tech", "entertainment_content", "market_sentiment"],
  "source_origin": "channel_interpretation",
  "source_quality": "medium",
  "framework_used": "regime_shift",
  "matched_thinking_pattern": "정보·취향이 과잉으로 임계점을 넘으면 사용자가 0으로 리셋되어 '진짜 브랜드'에만 신뢰가 몰린다는 사고",
  "attention_hook": "신문·잡지 다 죽는다는데 뉴욕타임스 주가는 오르고 워렌 버핏이 마지막으로 매수한 게 뉴욕타임스다. AI 시대 = 콘텐츠 인플레인데 왜 종이 미디어가 다시 오르나?",
  "implicit_question": "AI 추천이 사용자의 결정 행위를 임계점 이상 대신하면, 신뢰 앵커로의 자금·트래픽 집중이 (a) 디지털 구독자 가속 증가 (b) 광고 단가(CPM) 점프 (c) 멀티플 리레이팅 — 어느 KPI에 가장 먼저 나타나는가? 그리고 그 시점은 AI SERP가 구글 검색 점유율 30%+를 넘는 분기와 얼마나 정렬되는가?",
  "reasoning_move": "1차 인과는 'AI=콘텐츠 무한 생성=미디어 더 죽음'인데, 조수용은 '취향이 소멸하는 임계점'을 함수에 추가 → 정보 과잉이 임계점을 넘으면 사용자가 무엇을 고를지 모르게 되고, 그 공백을 메우는 게 '에디터 더 뽑은 뉴욕타임스 같은 브랜드'라고 점프 → 결과: 미디어 산업 파이는 줄지만 진짜 소수 브랜드만 살아남는 양극화.",
  "consensus_gap": "시장 컨센서스: AI 시대 = 콘텐츠 생성 비용 0 수렴 → 모든 미디어 디스카운트 (구글 SERP·OpenAI Search 트래픽 잠식 우려). 화자 시각: 같은 AI 침투를 *취향 변수가 0으로 수렴하는 임계점*으로 재해석하면 상위 5~10개 신뢰 앵커 브랜드만 *멀티플 리레이팅* 대상. 핵심 차이는 *형태*: 시장은 미디어 전체를 한 카테고리로 보고, 화자는 *양극화 곡선*으로 본다 — 상위는 리레이팅, 중하위는 가속 소멸.",
  "bull_case": "취향 소멸 가설 무효 — AI 추천이 사용자의 *선택 행위*를 대체하지 않고 *비교·요약*만 보조하면 취향 변수는 유지. NYT·뉴요커의 디지털 구독 가속도가 일반 미디어 평균과 큰 차이 없으면 *신뢰 앵커 집중*이라는 양극화 가설 약화. 광고 시장 전체 위축이 NYT 같은 상위 브랜드까지 함께 누르면 신뢰 앵커 프리미엄 부재 입증.",
  "bear_case": "AI SERP 점유율 30%+ 돌파 + 구글 검색 클릭률 -20%YoY + NYT·뉴요커·이코노미스트 디지털 구독 증가율이 일반 미디어 평균을 2배+ 추월 4분기 연속 + 버크셔 13F에서 NYT 비중 추가 확대 + 매거진B·롱블랙 같은 신뢰 앵커 브랜드의 구독료 인상 흡수 — 이 5개가 같이 진행되면 양극화 가설 본격 확정, 상위 브랜드 멀티플 리레이팅 사이클 진입.",
  "monitoring_signals": [
    "NYT·뉴요커·이코노미스트·매거진B 디지털 구독자 증가율 vs 미디어 평균 (Bear 트리거: 2배+ 추월 4분기 연속)",
    "AI SERP·OpenAI Search 점유율 시계열 + 구글 검색 클릭률 (Bear 트리거: SERP 30%+ + 클릭률 -20%YoY)",
    "버크셔·블랙록 등 대형 자산운용사 13F에서 NYT·미디어주 비중 변화 (Bear 트리거: 추가 확대)",
    "신뢰 앵커 브랜드 구독료 인상 + 이탈률 (Bull 트리거: 인상 후 이탈률 점프 = 가격 결정력 부재)",
    "AI 추천이 결정 행동에 미치는 비율 조사(설문·행동 데이터) (선행 지표 — 임계점 도달 신호)"
  ],
  "analyst_view": "미디어 양극화 시점 추적 카드 — *NYT 매수 신호가 아니라* 'AI = 미디어 죽음' 1차 인과를 받았을 때 *취향 변수 임계점*에서 양극화가 시작되는지 추적하는 시그널 카드. 미디어 산업 파이는 *축소 + 상위 리레이팅*으로 분리됨을 전제. 동일 사고 패턴이 SaaS(E007)·콘텐츠 생성 시장에도 적용 가능 — '신뢰 앵커가 어디인가'를 산업별로 묻는 메타 카드. 광고·구독·자산운용 3축에서 모니터링.",
  "original_signal": "뉴욕타임스 주가 상승; 워렌 버핏 버크셔 마지막 매수가 뉴욕타임스; 뉴요커 등 종이 잡지 일부 부활; 챗GPT·재미나이가 '뭐 사야 돼?'에 직접 답함; 조수용 '의식 있는 소수' 지향론",
  "trigger_conditions": [
    "NYT·뉴요커 등 레거시 미디어 디지털 구독자 증가율",
    "AI 검색 점유율이 구글 SERP 클릭률에 미친 영향 데이터",
    "버크셔 13F 뉴욕타임스 비중 변화",
    "AI 추천 알고리즘이 결정 행동에 미치는 비율 조사",
    "매거진B·롱블랙·NYT 구독료 인상 발표 + 이탈률"
  ],
  "causal_chain": "[AI 검색·추천이 사용자의 선택 행위를 대신함] → [개인 취향 변수가 임계점 넘어 0으로 수렴] → [신뢰 앵커 필요성 증가] → [에디터 컬렉션·일관된 관점 가진 소수 브랜드(NYT, 뉴요커, 매거진 B 류)에 구독·트래픽 집중] → [미디어 파이는 줄지만 상위 5~10개 브랜드는 멀티플 리레이팅 + 광고·구독 가격 결정력 회복]",
  "expected_direction": "bullish_short",
  "time_horizon": "mid",
  "confidence": "medium — 화자 2명(조수용·이재용) 일치, 구체 사례(NYT, 버핏) 2건, AI SERP 정량 데이터 부족",
  "evidence_type": "expert_interpretation",
  "abstraction_level": "medium",
  "technical_depth": "low",
  "quant_support": "one_or_two_numbers",
  "speaker_views": {
    "조수용": "AI 시대에 취향이 소멸한다. 그 공백을 메우는 건 결국 브랜드밖에 안 남는다. 진짜만 살아남는 시대.",
    "이재용": "버핏이 마지막으로 매수한 게 뉴욕타임스. AI가 재생산할 수 없는 1차 원소스 콘텐츠가 가치를 갖는다."
  },
  "source_videos": [
    {
      "video_id": "M-NxLzCNH-s",
      "channel": "머니그라피",
      "quote": "취향의 공백 시대에 살아남을 수 있는 거는 결국에는 브랜드밖에 안 남는다는 거예요... 그래서 지금 뉴욕타임스 주가가 올라가고 있어요"
    }
  ],
  "source_references": ["M-NxLzCNH-s:5:530", "M-NxLzCNH-s:5:540", "M-NxLzCNH-s:5:556", "M-NxLzCNH-s:5:574"],
  "cross_reference_cards": ["E007"],
  "search_blurb": "New York Times Berkshire Hathaway Warren Buffett 뉴요커 매거진B 조수용 브랜드 철학 AI 취향 소멸 정보 과잉 임계점 1차 원소스 콘텐츠 구독 모델 양극화 신뢰 앵커 AI SERP 멀티플 리레이팅 가격 결정력",
  "insight_quality": {
    "score_0_to_10": 8,
    "grade": "high",
    "score_reasons": [
      "양극화(파이 축소 + 상위 리레이팅) 분리 + 어느 KPI에 먼저 나타나는지 함수화",
      "consensus_gap을 *카테고리 통합 vs 양극화 곡선* 형태 차이로 명시",
      "bull case에 가설 무효 조건(취향 변수 유지·광고 시장 동반 위축) 명시",
      "monitoring signal 5개 — AI 추천 행동 비율이라는 선행 지표 포함",
      "E007 cross-ref로 SaaS 양극화와 동형 가설 일반화"
    ],
    "quality_test": "단기 트렌드가 아닌 사용자 행동 변수(취향) 자체가 0으로 가는 구조 변화를 다룸 → 1차 인과(AI=미디어 죽음) 거부 후 신뢰 앵커 함수로 점프",
    "missing_to_upgrade": [
      "NYT 디지털 구독 증가율 정량 시계열 (분기 단위)",
      "AI SERP가 미디어 트래픽에 준 정량 충격 (구글 검색 결과 클릭률·CTR)",
      "버크셔 13F NYT 비중 변화 history"
    ]
  },
  "storage_guidance": {
    "keep_as_fact": [
      "워렌 버핏이 버크셔 회장 물러나기 전 마지막 매수가 뉴욕타임스",
      "조수용의 '의식 있는 소수' 브랜드론"
    ],
    "keep_as_inference": ["matched_thinking_pattern", "reasoning_move", "consensus_gap", "양극화 시나리오"],
    "must_not_store_as_fact": ["NYT 외 모든 종이 미디어 부활 단정", "AI SERP 점유율 수치 단정"]
  }
}


# ============ A2: E012 ============
E012 = {
  "card_id": "E012",
  "title": "신입 안 뽑는 시대 자가발전",
  "labels": ["startup_business", "ai_tech", "korea_economy", "investment_strategy"],
  "source_origin": "speaker_inference",
  "source_quality": "medium",
  "framework_used": "second_order_effect",
  "matched_thinking_pattern": "기업이 'AI로 생산성 점프'를 1차로 누리면 그 비용 절감이 신입 채용 단절이라는 2차 효과로 옮겨 붙는 경로를 보는 사고",
  "attention_hook": "서울대 컴공이 서류 합격이 안 된다는 시대다. 기업은 신입을 안 뽑는데, '경력 같은 신입'이 되라고 한다. 도대체 그 경력은 어디서 쌓아야 되나? 회사 밖에서.",
  "implicit_question": "AI가 주니어 일을 대체하는 1차 효과가 *기업의 매몰비용 회피 행동*으로 옮겨 붙는다면, 노동시장 진입 모델 재편의 첫 신호는 (a) 국내 IT 신입 채용 공고 수 -20%YoY (b) 바이브 코딩 출신 채용 사례 분기 100건+ (c) 팔란티어식 직접 육성 프로그램 국내 도입 — 어느 지표가 *2026~2027년 사이* 가장 먼저 임계 돌파하는가?",
  "reasoning_move": "1차 인과는 'AI 코딩 80% 대체 → 주니어 채용 감소'인데, 화자는 한 단계 더 들어가 '경력직만 뽑는다=육성을 매몰비용으로 본다'는 기업 의사결정 함수를 추가 → 그러면 신입의 무기는 '회사 밖에서 사용자 1000명 모은 프로젝트' 같은 자가발전 레퍼런스 → 이건 바이브 코딩 같은 도구 접근성이 결정한다는 점프.",
  "consensus_gap": "시장 컨센서스: AI 코딩은 주니어 보조 도구, 채용 모델은 5~10년에 걸쳐 점진적 변화 (인사·HR 표준 내러티브). 화자 시각: *이미 2026 진입 시점에 경력직 위주 전환이 시작*됐고, 노동시장 진입 자격이 *회사 안 OJT*에서 *회사 밖 프로젝트 레퍼런스*로 시프트. 핵심 차이는 *시점·형태*: 시장은 점진적 변화·고용 보호 정책 흡수로 보고, 화자는 *기업 매몰비용 회피*가 즉각 발현되어 신입 채용 *공고 자체가 사라지는 형태*로 발현.",
  "bull_case": "신입 채용 단절 가설 약화 — 정부의 청년 고용 보조금·청년취업진로지원사업 강화로 기업이 신입 채용 유지. 한국 IT 대기업이 *AI 도입 후 1인당 매출 점프*를 인력 축소가 아니라 *총매출 확대*로 흡수 (네이버·카카오 클라우드·AI 자회사 신규 사업). 국내 IT 신입 채용 공고가 -10%YoY 이내 유지되면 채용 단절 가설 부분 무력.",
  "bear_case": "국내 IT 신입 채용 공고 -20%YoY 두 분기 연속 + 경력 1~3년차 채용 공고 +30%YoY (대체 효과 확인) + 팔란티어·OpenAI 한국 진출 시 '직접 육성·고졸 채용' 프로그램 도입 + 바이브 코딩(Replit·Lovable) 출신 한국 IT 기업 채용 사례 분기 50건+ 발표. 이 4개가 같이 진행되면 노동시장 진입 모델 재편 본격화, 청년 실업률 구조적 점프.",
  "monitoring_signals": [
    "국내 IT 대기업·중견(네이버·카카오·NHN·라인·쿠팡·토스) 신입 채용 공고 수 시계열 (Bear: -20%YoY 두 분기 연속)",
    "경력 1~3년차 vs 신입 채용 공고 비율 변화 (Bear: 1~3년차 +30%YoY로 대체 확인)",
    "Replit·Lovable·Cursor 한국 사용자 증가율 + 바이브 코딩 출신 채용 사례 빈도 (선행 지표)",
    "팔란티어·OpenAI·Anthropic의 한국 진출 + 직접 육성 프로그램 발표 (Bear 트리거 — 단발성 발표)",
    "정부 청년 고용 보조금·청년취업진로지원 예산 변화 (Bull 트리거: 예산 확대)"
  ],
  "analyst_view": "노동시장 진입 모델 재편 카드 — *주식 매수/매도 신호가 아니라* AI 생산성 점프 뉴스를 받았을 때 *기업 매몰비용 회피 행동*이 어느 분기에 신입 채용 컷으로 발현되는지 추적하는 시그널 카드. E007(전문가 SaaS substitution)·E009(1인당 매출 허들)와 cross-ref 시 'AI 생산성 → 단위경제 허들 점프 → 신규 채용 동결'의 3단 연쇄 검증. 한국 대학·교육·청년 정책 함의가 큰 카드 — 매크로 청년 실업 사이클 분석 도구로도 활용.",
  "original_signal": "서울대 컴공 서류 합격 어렵다는 보고; 남세동의 '코딩 80% AI가 대체, 주니어 안 뽑는 세상'; 팔란티어 CEO의 고졸 인재 직접 육성 발언; '경력 같은 신입' 요구; 회사 밖 사용자 1000명 프로젝트 권유",
  "trigger_conditions": [
    "주요 빅테크·국내 IT 기업 신입 채용 공고 수 추적",
    "신입 채용 규모 vs 경력직 채용 규모 비율 변화",
    "팔란티어·OpenAI 등 직접 육성 프로그램 발표",
    "바이브 코딩 툴(Replit, Lovable) 사용자 증가율",
    "초봉 격차(스타트업 vs 대기업) 데이터",
    "정부 청년 고용 보조금·청년취업진로지원 예산 발표"
  ],
  "causal_chain": "[AI가 주니어 업무 80% 대체] → [기업이 신입 육성을 매몰비용으로 인식] → [경력직·즉시전력만 채용 + 신입 공고 자체 소멸] → [신입은 회사 밖 프로젝트(바이브 코딩 + 사용자 1000명 모음)로 자가발전 후 진입] → [도구 접근성·문제 정의력이 새로운 진입 자격 함수 + 청년 실업 구조 변화]",
  "expected_direction": "conditional",
  "time_horizon": "long",
  "confidence": "medium — 화자 3명(남세동·이재용·창선) 같은 방향, 정량 데이터(채용 공고 시계열) 미확보",
  "evidence_type": "expert_interpretation",
  "abstraction_level": "medium",
  "technical_depth": "low",
  "quant_support": "one_or_two_numbers",
  "speaker_views": {
    "남세동": "주니어를 안 뽑는 세상으로 바뀌었다. 정직성실과 메타인지가 70점. 바이브 코딩이 당분간 경제적 가치 최고.",
    "이재용": "기업이 육성 비용을 매몰비용으로 본다. 신입은 회사 밖에서 사용자 1000명 모은 프로젝트 같은 레퍼런스를 만들어야 한다."
  },
  "source_videos": [
    {
      "video_id": "6zXcw8lf_zo",
      "channel": "머니그라피",
      "quote": "지금 신입을 안 뽑는 이유는 기본적으로 이제 육성을 하겠다라는 마인드 자체가 이제 기업에게 많이 없어지거든... 경력 같은 신입이 돼야 되잖아요... 사용자 1,000명을 만드는 모음으로 성공했습니다 이런 식으로 회사 밖에 다양한 프로젝트를 통해서 경험을 쌓는 게 지금에서는 필요하다"
    }
  ],
  "source_references": ["6zXcw8lf_zo:10:990", "6zXcw8lf_zo:10:996", "6zXcw8lf_zo:10:1023", "6zXcw8lf_zo:10:1070"],
  "cross_reference_cards": ["E007", "E009"],
  "search_blurb": "신입 채용 단절 바이브 코딩 Replit Lovable 팔란티어 고졸 육성 매몰비용 경력 같은 신입 자가발전 사용자 1000명 회사 밖 프로젝트 메타인지 정직성실 AI 노동시장 청년 실업 진입 모델 재편 청년 고용 보조금",
  "insight_quality": {
    "score_0_to_10": 8,
    "grade": "high",
    "score_reasons": [
      "1차 효과(AI 대체)와 2차 효과(매몰비용 인식)를 분리 + 시점 함수로 정밀화",
      "consensus_gap을 점진적 변화 vs 즉각적 공고 소멸 시점·형태 축으로 분리",
      "monitoring signal 5개 — 경력 1~3년차 채용 +30%YoY 대체 효과 검증 지표 포함",
      "bull case에 정부 보조금·총매출 확대 흡수라는 무효화 조건 명시",
      "E007·E009와 cross-ref로 AI 노동시장 메타 가설 추적 가능"
    ],
    "quality_test": "second_order_effect로 'AI 생산성 점프'의 직접 수혜자가 아닌 '신입 채용 단절'이라는 의외의 피해자를 분리해 추적",
    "missing_to_upgrade": [
      "국내 IT 신입 채용 수 추이 정량 데이터 (워크넷·잡코리아·사람인 분기 통계)",
      "바이브 코딩 출신 채용 사례 정량화 (한국 IT 기업 인재상 변화 추적)",
      "정부 청년 고용 정책 효과 (보조금 → 채용 유지 효과 측정)"
    ]
  },
  "storage_guidance": {
    "keep_as_fact": [
      "남세동의 신입 채용·코딩 80% 대체 발언",
      "이재용의 '경력 같은 신입' 처방"
    ],
    "keep_as_inference": ["matched_thinking_pattern", "reasoning_move", "consensus_gap", "노동시장 진입 모델 변화"],
    "must_not_store_as_fact": [
      "모든 기업이 신입을 안 뽑는다는 단정",
      "팔란티어식 직접 육성이 표준이 된다는 예측",
      "청년 실업률 구조적 점프 단정"
    ]
  }
}


def update_jsonl(fp: Path, updates: dict) -> dict:
    """updates: {card_id: new_card_dict}. 다른 라인은 그대로 보존."""
    lines = fp.read_text(encoding="utf-8").splitlines()
    new_lines = []
    found = {cid: False for cid in updates}
    for l in lines:
        if not l.strip():
            new_lines.append(l)
            continue
        c = json.loads(l)
        cid = c.get("card_id")
        if cid in updates:
            new_lines.append(json.dumps(updates[cid], ensure_ascii=False))
            found[cid] = True
        else:
            new_lines.append(l)
    fp.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    return found


def main() -> None:
    r1 = update_jsonl(A1, {"E003": E003, "E005": E005})
    print(f"A1 updates: {r1}")
    r2 = update_jsonl(A2, {"E007": E007, "E009": E009, "E011": E011, "E012": E012})
    print(f"A2 updates: {r2}")

    # 라인 수 검증
    for fp in (A1, A2):
        lines = [l for l in fp.read_text(encoding="utf-8").splitlines() if l.strip()]
        print(f"{fp.name}: {len(lines)} lines")


if __name__ == "__main__":
    main()
