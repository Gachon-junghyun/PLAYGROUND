# R2 카드 통합 요약 (43장)
> 각 카드 ID 클릭하면 jsonl에서 본문 확인 가능. RAG 검색 시 search_blurb를 임베딩 키로 사용.

## R2 매크로 (C001~C016)
- **C001** 이란-미국 협상 쟁점 → 결렬 리스크  
  · 라벨: `oil_geopolitics` · 화자: 오선의 미국 증시 라이프 + 김단테 월가아재 · 방향: conditional — 합의 진전 시 bullish_short, 결렬 신호 시 bearish_short · 시간: short · src: 14건 · conf: medium — 화자 2명(오선·김단테) 일치, 김단테가 쟁점 4개를 구
- **C002** 호르무즈 봉쇄 → 미국 역봉쇄 응징  
  · 라벨: `oil_geopolitics` · 화자: 오선의 미국 증시 라이프 + 김단테 월가아재 · 방향: bearish_short (지정학 리스크), mixed (장기적으로는 양측 모두 지속 어렵다는 분석) · 시간: short · src: 15건 · conf: medium-high — 김단테 단독으로 봉쇄 메커니즘을 깊이 분석(다수
- **C003** 유가 100불 돌파 → 인플레·증시 전이  
  · 라벨: `oil_geopolitics` · 화자: 김단테 월가아재 + 오선의 미국 증시 라이프 · 방향: mixed — 유가 자체는 bullish, 증시 영향은 conditional(실적·AI 흐름이 흡수) · 시간: short · src: 16건 · conf: medium — 화자 2명 일치, 김단테는 수치·시나리오 제시(publi
- **C004** 휴전 합의 → 시장 안도 랠리  
  · 라벨: `oil_geopolitics` · 화자: 오선의 미국 증시 라이프 + 김단테 월가아재 · 방향: bullish_short (단, 시한 임박·새 공격 시 conditional) · 시간: short · src: 17건 · conf: medium-high — 화자 2명 강한 일치, 다수 명제가 휴전→상승 
- **C005** 어닝 호조 + AI/반도체 → 사상 최고치 랠리  
  · 라벨: `us_equity_market` · 화자: 오선의 미국 증시 라이프 + 김단테 월가아재 · 방향: bullish_short · 시간: short · src: 10건 · conf: high — 화자 2명 일치, public_fact·data 근거 다수(
- **C006** 이란·호르무즈 협상 단계 → 증시 일희일비  
  · 라벨: `us_equity_market, oil_geopolitics` · 화자: 오선의 미국 증시 라이프 + 김단테 월가아재 · 방향: conditional · 시간: intraday · src: 11건 · conf: medium — 화자 2명 일관 관찰, 다만 '원유↑+증시↑' 디커플링은
- **C007** Fed 매파 + 반도체 약세 → 변동성/하방 압력  
  · 라벨: `us_equity_market, fed_policy` · 화자: 오선의 미국 증시 라이프 + 김단테 월가아재 · 방향: bearish_short · 시간: short · src: 6건 · conf: medium — 화자 2명 관찰, 명제 수는 적으나 인과 사슬 명확(ca
- **C008** 인도 장기 성장 → 신흥국 알파 시나리오  
  · 라벨: `emerging_markets` · 화자: 머니코믹스 · 방향: bullish_long · 시간: long · src: 12건 · conf: medium — 단일 화자(머니코믹스)지만 data 근거 다수(11% 매
- **C009** MSCI 비중 9% 신흥국 → 자본유입 캐치업  
  · 라벨: `emerging_markets` · 화자: 머니코믹스 · 방향: conditional · 시간: mid · src: 12건 · conf: medium — 단일 화자, 조건부 예측(conditional_predi
- **C010** 고용·유가 강세 → 금리 동결 장기화  
  · 라벨: `employment_data, fed_policy, inflation_data` · 화자: 오선의 미국 증시 라이프 · 방향: neutral_short / bearish_for_rate_cut_bets · 시간: short · src: 8건 · conf: medium — 단일 화자(오선) 중심이지만 월가 은행/연준 총재의 외부
- **C011** PPI 예상 하회 → 디스인플레·피벗 기대  
  · 라벨: `inflation_data, fed_policy` · 화자: 김단테 월가아재 + 오선의 미국 증시 라이프 · 방향: mixed (단기 bullish 반응, 중기 conditional) · 시간: short · src: 10건 · conf: medium — 화자 2명(김단테·오선) 모두 등장, 같은 PPI 이벤트
- **C012** FOMC 분열·매파 동결 → 증시 하방  
  · 라벨: `fed_policy, inflation_data` · 화자: 오선의 미국 증시 라이프 · 방향: bearish_short · 시간: short · src: 18건 · conf: medium — 단일 화자(오선) 보고지만 FOMC 위원별 실명 인용 다
- **C013** 제로→4%대 금리 레짐 → 듀레이션 충격  
  · 라벨: `fed_policy, inflation_data` · 화자: 김단테 월가아재 · 방향: bearish_long (구조적), neutral_for_marginal_hike · 시간: long · src: 22건 · conf: low~medium — 단일 화자(김단테) 구조론적 해석 위주, evid
- **C014** 중국 기업 부상 → 장기 이미지 개선  
  · 라벨: `china_macro` · 화자: 머니그라피 · 방향: bullish_long_conditional · 시간: long · src: 7건 · conf: low — 단일 화자(머니그라피), 근거는 모두 인상·해석 기반(evid
- **C015** 코스피 변동성 — 강세장 vs 외부 충격  
  · 라벨: `korea_economy` · 화자: 김단테 월가아재 · 방향: mixed · 시간: short · src: 8건 · conf: low — 단일 화자(김단테), 명제 대부분 fact_statement,
- **C016** 한국 경제 양가성 — 상대 안정 vs 구조적 문제  
  · 라벨: `korea_economy` · 화자: 머니그라피 · 방향: mixed · 시간: unspecified · src: 3건 · conf: low — 단일 화자(머니그라피), 근거는 비교 관찰과 해석 위주, 동일

## R2 산업·섹터 (C017~C028)
- **C017** 리니지 BM 종언 → 넥슨·신작 르네상스  
  · 라벨: `game_industry` · 화자: 머니그라피 · 방향: mixed — 대기업 전반 bearish, 넥슨·신작 bullish_long · 시간: long · src: 14건 · conf: low~medium — 단일 화자(머니그라피), 근거는 종목 일화와 정성
- **C018** 닌텐도·캡콤·스퀘어 → 콘솔/IP 강세  
  · 라벨: `game_industry` · 화자: 머니그라피 · 방향: bullish_short · 시간: short · src: 11건 · conf: medium — 단일 화자지만 판매량/주가 반등/영업이익률 등 data 
- **C019** 게임 산업 블루칩 → 성장 둔화  
  · 라벨: `game_industry` · 화자: 머니그라피 · 방향: bearish_mid · 시간: mid · src: 9건 · conf: low~medium — 단일 화자, 2.8%/4.7% 등 data 근거는
- **C020** 유비식 vs 락스타식 → 내러티브 회귀  
  · 라벨: `game_industry` · 화자: 머니그라피 · 방향: bullish_long (내러티브 중심 게임/스튜디오 한정) · 시간: long · src: 14건 · conf: low — 단일 화자(머니그라피), 디자인 철학·업계 분위기 기반 정성적
- **C021** 엔비디아 방중 → AI 반도체 강세  
  · 라벨: `semiconductor_cycle, ai_tech` · 화자: 오선의 미국 증시 라이프 + 김단테 월가아재 · 방향: bullish_short · 시간: short · src: 7건 · conf: medium — 화자 2명(오선·김단테) 같은 방향, 근거 public_
- **C022** 인텔·AMD·마이크론 개별주 변동  
  · 라벨: `semiconductor_cycle, single_stock_move` · 화자: 오선의 미국 증시 라이프 + 김단테 월가아재 · 방향: mixed · 시간: short · src: 15건 · conf: high — 화자 2명 일치, 구체 수치 근거 다수(23.6%, 18%,
- **C023** 빅테크 캐펙스 ↔ 반도체 연쇄  
  · 라벨: `big_tech_earnings, semiconductor_cycle` · 화자: 김단테 월가아재 + 오선의 미국 증시 라이프 · 방향: conditional · 시간: mid · src: 10건 · conf: medium — 화자 2명 일치 방향성, 김단테는 인과 메커니즘, 오선은
- **C024** 애플 미국 내 칩 생산 → 인텔·삼성 파운드리  
  · 라벨: `big_tech_earnings, semiconductor_cycle` · 화자: 오선의 미국 증시 라이프 · 방향: bullish_short · 시간: short · src: 5건 · conf: low — 단일 화자(오선), 단 source 명제의 evidence_t
- **C025** AI 컴퓨팅 제약 → 종량제 전환  
  · 라벨: `ai_tech` · 화자: 김단테 월가아재 · 방향: mixed · 시간: mid · src: 14건 · conf: low — 단일 화자(김단테), 다만 같은 화자가 다수 명제로 일관된 회
- **C026** 중국 가전 부상 → 한국 빅2 위협  
  · 라벨: `consumer_electronics` · 화자: 머니그라피 · 방향: bullish_china_bearish_korea_long · 시간: long · src: 12건 · conf: medium — 단일 화자(머니그라피), 샤오미 매출 수치(56조/54조
- **C027** 가전 저성장 → 콘텐츠·니치가 브랜드 위  
  · 라벨: `consumer_electronics, entertainment_content` · 화자: 머니그라피 · 방향: mixed — 전통 가전 bearish_long / 콘텐츠 결합·니치 bullish_long · 시간: long · src: 19건 · conf: medium — 단일 화자(머니그라피), interpretation·pr
- **C028** 에너지 공급 축소 → 인플레 전이 시나리오  
  · 라벨: `energy_commodities` · 화자: 김단테 월가아재 + 오선의 미국 증시 라이프 · 방향: bullish_energy_short / bearish_macro_mid / mixed_equity · 시간: short · src: 14건 · conf: medium — 화자 2명(김단테·오선) 시각 일치(에너지 가격 상승 추

## R2 기업·종목 (C029~C040)
- **C029** 니치마켓 카테고리 창출 → 고이익률  
  · 라벨: `brand_strategy` · 화자: 머니그라피 · 방향: bullish_mid · 시간: mid · src: 13건 · conf: low~medium — 단일 화자(머니그라피), 단일 사례(스탠바이미) 
- **C030** 카테고리 창출자 vs 빠른 추격자  
  · 라벨: `brand_strategy, consumer_electronics` · 화자: 머니그라피 · 방향: bearish_long for 카테고리 창출자, bullish_short for 빠른 추격자 · 시간: long · src: 8건 · conf: medium — 단일 화자(머니그라피), 다이슨 사례 1건이지만 인과 사
- **C031** 중국 브랜드 부상 → 글로벌 가전 위협  
  · 라벨: `brand_strategy` · 화자: 머니그라피 · 방향: bullish_long for 중국 브랜드, bearish_long for 한국 브랜드 일부 · 시간: long · src: 12건 · conf: medium — 단일 화자(머니그라피)지만 high confidence 
- **C032** 게임 IP·플랫폼 확장 → 흥행  
  · 라벨: `brand_strategy, game_industry` · 화자: 머니그라피 · 방향: bullish_short · 시간: mid · src: 12건 · conf: high — 단일 화자지만 evidence_type=data 명제 2건(
- **C033** 구매주기 긴 홈서비스 인접 확장 시나리오  
  · 라벨: `startup_business` · 화자: 머니코믹스 · 방향: bullish_long · 시간: long · src: 9건 · conf: medium — 단일 화자(머니코믹스) 본인 사례 1건, 회원 4만명·기
- **C034** 고객 민원 데이터화 → CS가 차별화 무기  
  · 라벨: `startup_business` · 화자: 머니코믹스 · 방향: bullish_mid · 시간: mid · src: 11건 · conf: medium — 단일 화자, 근거 data 1건(250개 민원율 일일 트
- **C035** 임원·젊은조직이 스타트업 성과 가른다  
  · 라벨: `startup_business` · 화자: 머니코믹스 · 방향: conditional · 시간: mid · src: 10건 · conf: medium — 단일 화자 본인 사례, confidence_level h
- **C036** BM 혁신·내재화 → 후발주자 점유율 역전  
  · 라벨: `startup_business, brand_strategy, game_industry` · 화자: 머니코믹스 + 머니그라피 · 방향: mixed · 시간: mid · src: 13건 · conf: medium — 화자 2명(머니코믹스, 머니그라피) 서로 다른 사례로 같
- **C037** 어닝 비트 광범위 → 증시 신고가  
  · 라벨: `corporate_earnings` · 화자: 오선의 미국 증시 라이프 + 김단테 월가아재 · 방향: bullish_short · 시간: short · src: 10건 · conf: high — 화자 2명 일치, 블룸버그 데이터(81%) 등 public_
- **C038** 호실적 발표 → 개별주 두자릿수 급등  
  · 라벨: `corporate_earnings, single_stock_move` · 화자: 오선의 미국 증시 라이프 + 김단테 월가아재 · 방향: bullish_short · 시간: intraday · src: 13건 · conf: high — 화자 2명 일치, 수치(18%/31%/23.6%/12%/13
- **C039** 어닝 비트인데 주가 하락 디커플링  
  · 라벨: `corporate_earnings, single_stock_move` · 화자: 오선의 미국 증시 라이프 · 방향: bearish_short · 시간: intraday · src: 6건 · conf: medium — 단일 화자(오선) 중심이나 사례 3건(팔런티/테슬라/메타
- **C040** 비미국 일반기업 매출 우상향 패턴  
  · 라벨: `corporate_earnings` · 화자: 머니그라피 + 머니코믹스 · 방향: bullish_long · 시간: long · src: 12건 · conf: medium — 화자 2명, 수치 근거 다수(매출 절대치·성장률·마진율)

## R2 일반론·메타 (C041~C047)
- **C041** 지정학 긴장 완화 → 위험자산 랠리  
  · 라벨: `market_sentiment, risk_factors` · 화자: 오선의 미국 증시 라이프 + 김단테 월가아재 · 방향: bullish_short · 시간: short · src: 9건 · conf: medium — 화자 2명(오선·김단테) 일치, 다수 명제가 동일 이벤트
- **C042** 악재 무시 경고 → 하방 헷지 준비  
  · 라벨: `market_sentiment, risk_factors, investment_strategy` · 화자: 김단테 월가아재 + 오선의 미국 증시 라이프 · 방향: bearish_short · 시간: short · src: 15건 · conf: medium — 김단테 다수 명제 일관, 오선 분석가 인용(UBS 헤펠레
- **C043** 실적·펀더멘털 → 지정학 노이즈 흡수  
  · 라벨: `risk_factors, market_sentiment` · 화자: 오선의 미국 증시 라이프 + 김단테 월가아재 · 방향: bullish · 시간: mid · src: 9건 · conf: medium — 화자 2명(오선 중심·김단테 보조) 일치, 오선 명제가 
- **C044** 장기 자산배분 → 분산·하이리스크 판단  
  · 라벨: `investment_strategy, risk_factors` · 화자: 김단테 월가아재 + 머니그라피 + 머니코믹스 + 오선의 미국 증시 라이프 · 방향: mixed · 시간: long · src: 14건 · conf: medium — 화자 4명 모두 등장하나 각자 다른 자산군(미국 대형주·
- **C045** 트럼프 협상 변덕 → 시장 단기 안도  
  · 라벨: `geopolitics_general` · 화자: 오선의 미국 증시 라이프 + 김단테 월가아재 · 방향: mixed — 발언에 따라 단기 bullish/bearish 교차, 추세는 conditional · 시간: short · src: 15건 · conf: medium — 오선·김단테 2명 일치, 사실 보도와 해석 혼합, 다수 
- **C046** 미·중 정상회담·관세 → 무역 긴장 재점화  
  · 라벨: `geopolitics_general` · 화자: 오선의 미국 증시 라이프 + 머니코믹스 · 방향: bearish_short(관세 인상 시) / conditional(정상회담 결과 의존) · 시간: short · src: 11건 · conf: medium — 오선의 사실 보도 다수와 머니코믹스의 해석, 두 화자 시
- **C047** 캠피셔 룰 — 지정학 충격은 단기  
  · 라벨: `analyst_view` · 화자: 김단테 월가아재 + 오선의 미국 증시 라이프 · 방향: bearish_short → bullish_mid (V자 회복형 컨센서스) · 시간: short · src: 15건 · conf: medium — 캠피셔 관련 명제 7건이 김단테 단독, 오선의 월가 IB

## R0 머니그라피 (D001~D014)
- **D001** 상권 잔존가치 = 자연·유적·공간  
  · 라벨: `startup_business, korea_economy` · 화자: 유정수 (글로우서울 대표) + 안스타 (커피 크리에이터) · 방향: conditional · 시간: long · src: 0건 · conf: medium — 단일 영상이지만 전문가 2명(글로우서울·언스페셜티) 일치
- **D002** 외국인 유입이 상권 미래 가른다  
  · 라벨: `startup_business, korea_economy, consumer_electronics` · 화자: 유정수 (글로우서울 대표) + 안스타 · 방향: bullish_short · 시간: mid · src: 0건 · conf: medium — 단일 영상이지만 ETF·언스페셜티 두 사업자 실제 매출 
- **D003** 카페 시장: 공간형 → 맛 본위 전환  
  · 라벨: `startup_business, brand_strategy, consumer_electronics` · 화자: 안스타 (언스페셜티 대표) + 유정수 · 방향: mixed · 시간: mid · src: 0건 · conf: medium — 단일 영상이지만 커피 산업 내부자 1명(언스페셜티) + 
- **D004** 건물주는 공실로 7년 버틴다  
  · 라벨: `korea_economy, startup_business, risk_factors` · 화자: 유정수 (글로우서울 대표) · 방향: bearish_long · 시간: long · src: 0건 · conf: low~medium — 단일 영상·단일 화자지만 정량 메커니즘(1억/5%
- **D005** 오너 일관 철학 → 브랜드 재무력  
  · 라벨: `brand_strategy, investment_strategy` · 화자: 조수용 + 이재용 · 방향: bullish_long · 시간: long · src: 0건 · conf: medium — 단일 영상이지만 화자 2명(조수용·이재용) 일치, 구체 
- **D006** AI 시대 진짜 콘텐츠 브랜드 부상  
  · 라벨: `ai_tech, entertainment_content, investment_strategy` · 화자: 조수용 + 남세동 · 방향: bullish_long · 시간: long · src: 0건 · conf: medium — 영상 1개·화자 2명 일치, 뉴욕타임스·버핏 매수 등 구
- **D007** AI 빅테크 캐펙스 → 이익 잠식  
  · 라벨: `ai_tech, big_tech_earnings, risk_factors` · 화자: 이재용 + 남세동 · 방향: mixed · 시간: mid · src: 0건 · conf: medium — 영상 1개지만 매출·영업이익·캐펙스 비율 등 구체 수치 
- **D008** AI 침투로 전문 SaaS 디레이팅  
  · 라벨: `ai_tech, single_stock_move, risk_factors` · 화자: 이재용 + 남세동 · 방향: bearish_long · 시간: mid · src: 0건 · conf: medium — 영상 1개, 어도비/세일즈포스/아틀라시안/오토데스크 구체
- **D009** 글로벌 게임 시장 성숙 → 일본 IP·중국 부상  
  · 라벨: `game_industry, entertainment_content` · 화자: 이재용 + 이종범 · 방향: bullish_long for Japan IP holders, bearish_short for Korean big publishers, bullish_mid for Chinese game stocks · 시간: mid · src: 0건 · conf: medium — 단일 영상이지만 산업 분석가 발화·구체 수치(2.8%, 
- **D010** 디자이너 팬덤화 → 럭셔리 브랜드 변동성↑  
  · 라벨: `brand_strategy, entertainment_content` · 화자: 한송인 + 장석종 + 이론(Ron) · 방향: mixed — bullish_short for designer-led houses on appointment news, bearish_long for brand equity erosion · 시간: mid · src: 0건 · conf: medium — 패션 매거진 편집장·셀러브리티 평론가 등 다중 화자 일치
- **D011** 인플루언서 공동구매 시장 3~4조 부상  
  · 라벨: `startup_business, consumer_electronics, brand_strategy` · 화자: 유봉석(뽀큐티) + 이재용 + 육식맨 · 방향: bullish_mid for commerce platforms (메타·구글·셀러 에그리게이터), bearish_mid for legacy BDC-dependent MCN · 시간: mid · src: 0건 · conf: medium-high — 영상 2개(셀러 인터뷰 + 도파민/플랫폼) 교차
- **D012** JTBC 올림픽 7천억 베팅 → 미디어 적자 리스크  
  · 라벨: `entertainment_content, corporate_earnings, risk_factors` · 화자: 박재민 + 이재용 · 방향: bearish_mid for JTBC and legacy broadcasters, neutral for IOC (현금 5조 방어), bearish_long for winter sports ecosystem · 시간: mid · src: 0건 · conf: medium — JTBC 매출·중계권 추정치(7천억)는 업계 추정, 평창
- **D013** 중국 가전 부상 → 한국 강자 정체  
  · 라벨: `consumer_electronics, china_macro, brand_strategy` · 화자: 최문균(나의 시선) + 이재용 · 방향: bullish_mid for Chinese consumer electronics (Xiaomi/Roborock/Anker/DJI), bearish_short for Korean legacy appliance makers · 시간: mid · src: 0건 · conf: medium — 영상 1개지만 산업 분석가+테크 큐레이터 일치, 매출·주
- **D014** K-스낵 정체 vs 김 수출 1.6조 부상  
  · 라벨: `consumer_electronics, korea_economy, single_stock_move` · 화자: 정동현 + 이재용 · 방향: bullish_mid for K-nori exporters & 오리온, neutral for 농심/롯데/해태, bullish_short for 김 회사 PE deals · 시간: mid · src: 0건 · conf: medium — 영상 1개지만 백화점 푸드 팀장+재무 분석가 교차, 영업

## R0 머니코믹스 (D015~D022)
- **D015** 트럼프 타코 협상 패턴 시나리오  
  · 라벨: `geopolitics_general, market_sentiment` · 화자: 백찬규(NH투자증권) · 방향: conditional — 단기 변동성 확대, 발언 직후 매도 후 타코 반등 매수 · 시간: short · src: 0건 · conf: medium — 단일 화자지만 1기·2기·이란 3회 패턴 반복 + 거래의
- **D016** 금융억압→달러약세→자산 대이동  
  · 라벨: `fed_policy, us_equity_market, inflation_data` · 화자: 백찬규(NH투자증권) · 방향: bearish_long(달러·미국채) + bullish_long(원자재·신흥국·실물자산) · 시간: long · src: 0건 · conf: medium — 단일 화자지만 2차대전 직후 미국 자본통제·워본드 등 역
- **D017** 호르무즈 봉쇄 장기화·한국 정유 재발견  
  · 라벨: `oil_geopolitics, energy_commodities, korea_economy` · 화자: 박정우(전 한화투자증권) · 방향: bullish_mid (한국 정유주·LNG 인프라), conditional (유가·금) · 시간: mid · src: 0건 · conf: medium — 단일 화자지만 SK이노 호주 광산, 캘리포니아 항공유, 
- **D018** 인도 디지털굿즈 자본주의·MSCI 자금 시프트  
  · 라벨: `emerging_markets, ai_tech, geopolitics_general` · 화자: 백찬규(NH투자증권) · 방향: bullish_long (인도 IT·금융), conditional (Nifty 단기는 트럼프 관세 변수) · 시간: long · src: 0건 · conf: medium — 단일 화자, MSCI 비중·인도 업종구성 그래프 등 데이
- **D019** AI 토큰 권력화·1인 증폭 시대  
  · 라벨: `ai_tech, startup_business, corporate_earnings` · 화자: 김지현(SK경영경제연구소 부사장 출신 AI 소장) · 방향: bullish_long (AI 인프라·반도체·HBM), bearish_long (전통 화이트칼라 헤드카운트) · 시간: long · src: 0건 · conf: medium — 단일 화자지만 우버·광진구청 공무원·크래프톤 비전공자 등
- **D020** OpenAI vs Anthropic 한계비용 모델 분기  
  · 라벨: `ai_tech, big_tech_earnings, corporate_earnings` · 화자: 김지현(AI 소장) · 방향: mixed — AI 인프라(HBM·반도체) bullish_long, 단일 모델 회사 주가 bearish_short on 분기 미스 · 시간: mid · src: 0건 · conf: medium — 단일 화자, Anthropic 4월 보고서·OpenAI 
- **D021** 정보 비대칭 시장 묶기 사업화  
  · 라벨: `startup_business, brand_strategy, investment_strategy` · 화자: 김민기(아정당 대표) + 남성훈(아임박스 대표) + 머니코믹스 사보팀 회고 · 방향: bullish_mid (정보비대칭 묶음 플랫폼), bearish_long (단순 인플루언서 커머스) · 시간: mid · src: 0건 · conf: medium — 화자 3명(아정당·아임박스·머니코믹스 사보팀)이 다른 방
- **D022** 애널리스트 직업 위기·셀리포트 정치비용  
  · 라벨: `analyst_view, ai_tech, investment_strategy` · 화자: 정의훈(유진투자증권 우주산업 애널리스트) + 강대석(PTR자산운용 매니저, 전 유진·유안타 시황 애널리스트) · 방향: bearish_long (전통 셀사이드 리서치 헤드카운트), bullish_long (개인 브랜드 IP·AI 차트분석 서비스) · 시간: long · src: 0건 · conf: medium — 화자 2명(셀사이드·바이사이드 동시) + AI 차트분석 

## R0 김단테+오선 (D023~D032)
- **D023** 호르무즈 통행료 정착 → 영구 리스크 프리미엄  
  · 라벨: `oil_geopolitics, inflation_data, us_equity_market` · 화자: 김단테 월가아재 · 방향: bearish_long(채권/소프트웨어), bullish_mid(에너지/원유원월/메모리), conditional · 시간: mid · src: 0건 · conf: medium — 단일 화자 김단테가 시트리니 리서치 현장 취재 원문을 인
- **D024** 이란-미국 휴전의 함정과 이스라엘 변수  
  · 라벨: `oil_geopolitics, geopolitics_general, market_sentiment` · 화자: 김단테 월가아재 · 방향: mixed, conditional · 시간: short · src: 0건 · conf: high — 김단테 다수 영상에서 일관된 시각, 페제스키안·아라그치·네타
- **D025** AI 4대 병목: 메모리·전력·CPU·광통신  
  · 라벨: `ai_tech, semiconductor_cycle, big_tech_earnings` · 화자: 김단테 월가아재 · 방향: bullish_mid · 시간: mid · src: 0건 · conf: high — 김단테 빅테크 실적 영상에서 4개 회사 코멘트 직접 인용, 
- **D026** 에이전틱 AI → CPU 슈퍼사이클·인텔 부활  
  · 라벨: `ai_tech, semiconductor_cycle, single_stock_move` · 화자: 김단테 월가아재 · 방향: bullish_mid, conditional · 시간: mid · src: 0건 · conf: high — 김단테 인텔 2영상 + 오선 4/24·5/05·5/08 영상
- **D027** 엔트로픽 양다리(구글-아마존) 순환출자 구조  
  · 라벨: `ai_tech, big_tech_earnings, single_stock_move` · 화자: 김단테 월가아재 · 방향: bullish_short(GOOGL/AMZN), conditional(NVDA) · 시간: mid · src: 0건 · conf: high — 김단테가 빅테크 실적+엔트로픽 딜 구조를 일관되게 분석, 오
- **D028** AI 코딩 침투 → 소프트웨어 SaaS 멀티플 학살  
  · 라벨: `ai_tech, corporate_earnings, investment_strategy` · 화자: 김단테 월가아재 · 방향: bearish_mid(SaaS), bullish_mid(반도체/하드웨어) · 시간: mid · src: 0건 · conf: high — 김단테 마소 해고 영상 + 오선 4/23 영상에서 IBM/서
- **D029** 유가 → PPI → CPI 2개월 시차 전가  
  · 라벨: `inflation_data, fed_policy, oil_geopolitics` · 화자: 김단테 월가아재 + 오선의 미국 증시 라이프 · 방향: bearish_mid(채권/멀티플), bullish_short(금/원자재), conditional · 시간: mid · src: 0건 · conf: high — 김단테 PPI 영상의 양영빈 기자 인용 + 오선 5/12, 
- **D030** 오픈AI 6000억 컴퓨팅 약정 vs 1220억 자금  
  · 라벨: `ai_tech, single_stock_move, risk_factors` · 화자: 김단테 월가아재 · 방향: bearish_short(OpenAI 관련주), mixed, conditional · 시간: short · src: 0건 · conf: medium — 김단테 영상+오선 4/28 영상 동일 WSJ 보도 인용,
- **D031** 달리오 13단계 9단계 진입·대만 확전 시나리오  
  · 라벨: `geopolitics_general, us_equity_market, risk_factors` · 화자: 김단테 월가아재 · 방향: bearish_long, conditional · 시간: long · src: 0건 · conf: medium — 단일 화자 김단테 1영상이지만 달리오 원글 직접 인용+클
- **D032** 캠피셔 3단계 패턴 + 단기 과열 경계  
  · 라벨: `us_equity_market, market_sentiment, investment_strategy` · 화자: 김단테 월가아재 + 오선의 미국 증시 라이프 · 방향: bullish_short, conditional, mixed · 시간: short · src: 0건 · conf: high — 김단테 캠피셔 인용 영상 + 오선 4/22, 4/30, 5/

## R0 지식부장관 (D033~D040)
- **D033** 달러-미국국채 디커플링 시나리오  
  · 라벨: `fed_policy, us_equity_market, risk_factors` · 화자: 지식부장관 · 방향: bearish_long_ust | bullish_short_usd | conditional · 시간: mid · src: 0건 · conf: medium — 단일 채널·단일 화자지만 BIS·세계금위원회식 통계와 코
- **D034** UAE OPEC 탈퇴 → 美 네트워크 편입  
  · 라벨: `oil_geopolitics, geopolitics_general, ai_tech, semiconductor_cycle` · 화자: 지식부장관 · 방향: bearish_long_oil | bullish_usd | mixed · 시간: mid · src: 0건 · conf: low — 단일 영상·단일 화자, 단 페트로달러/유로달러 시스템 구분 등
- **D035** 韓 원유 다변화 = 블렌딩 전략  
  · 라벨: `oil_geopolitics, korea_economy, energy_commodities` · 화자: 지식부장관 · 방향: neutral | conditional · 시간: mid · src: 0건 · conf: medium — 3개 영상 일관, 수입 비중·API·황 함량·TMX 89
- **D036** 터키 금 매각 → 리라 방어 + 中매입  
  · 라벨: `emerging_markets, geopolitics_general, energy_commodities` · 화자: 지식부장관 · 방향: mixed | conditional · 시간: short · src: 0건 · conf: medium — 단일 영상이나 WGC 통계·CBRT 보유량 변화·정치 의
- **D037** 신흥국 달러부채 외환위기 메커니즘  
  · 라벨: `emerging_markets, risk_factors, geopolitics_general` · 화자: 지식부장관 · 방향: bearish_long_em_currency · 시간: long · src: 0건 · conf: medium — 단일 영상이나 부채·금리·환율·운하수입 수치 일관, 다른
- **D038** 中쇼크 2.0: 전기차·배터리·태양광 과잉공급  
  · 라벨: `china_macro, semiconductor_cycle, energy_commodities, risk_factors` · 화자: 지식부장관 + 메인 컨텍스트 함의 · 방향: bearish_long_competitors | bullish_short_consumer · 시간: long · src: 0건 · conf: medium — 단일 영상이나 수출·점유율·성장률 수치 다수, IMF 경
- **D039** 韓 보톡스 산업: 균주·소송·치료시장 확장  
  · 라벨: `startup_business, korea_economy, brand_strategy` · 화자: 지식부장관 · 방향: bullish_long_treatment | conditional · 시간: long · src: 0건 · conf: low — 단일 영상·단일 화자, 산업사적 서술 위주로 단기 트리거는 약
- **D040** SMR 추진선 → K-조선 新 모멘텀  
  · 라벨: `energy_commodities, korea_economy, startup_business` · 화자: 지식부장관 · 방향: bullish_long_korean_shipbuilding | conditional · 시간: long · src: 0건 · conf: low — 단일 영상·단일 화자, 상업운항 전 개념설계 단계라 시점 리스
