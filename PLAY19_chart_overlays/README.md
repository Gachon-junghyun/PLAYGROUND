# PLAY19_chart_overlays — text 차트 + SMA + 매물대 사이드바

## 목적
OHLCV CSV → 캔들 text 차트 위에 SMA(20/60/120) overlay + 우측에 매물대 사이드바. mvp `module_text_chart` 스타일을 참고하되 *독립 구현*(표준 라이브러리만, pandas/numpy 무관).

## 실행법

```powershell
# 의존성: 표준 라이브러리만.

# 1) 기본 (SMA 20/60/120, height 24)
python PLAY19_chart_overlays/chart_overlays.py PLAY14_trade_planner/sample_ohlcv.csv

# 2) 짧은 시계열에 맞춰 SMA 줄이기
python PLAY19_chart_overlays/chart_overlays.py PLAY14_trade_planner/sample_ohlcv.csv --height 18 --sma "20,60"

# 3) SMA 비활성, 캔들만
python PLAY19_chart_overlays/chart_overlays.py PLAY14_trade_planner/sample_ohlcv.csv --sma ""
```

## 입력 / 출력

- **입력 CSV:** PLAY14·PLAY15 호환 헤더.
- **출력 (stdout):** 단일 텍스트 블록 — 헤더 2줄 + 차트 그리드 + X축 라벨.

캔들 문자 (mvp와 동일 코딩):
- `█` BULL (close ≥ open)
- `░` BEAR
- `│` 윗꼬리/아랫꼬리
- `0` DOJI (open ≈ close)

SMA overlay 문자:
- `·` SMA20
- `+` SMA60
- `*` SMA120
- 캔들과 겹치는 셀에선 캔들이 우선 (overlay는 빈 셀에만)

우측 사이드바: 같은 행 그리드 위 typical price 기준 누적 거래량 가로 막대. POC 행은 `◀POC` 마커.

샘플 출력 (`sample_chart.txt`, 60일 더미):
```
as_of=2026-05-22  range=99.07~129.07  n=60  SMA: 20=· 60=+
    127.31 |          █░░█░│█ ░█|▏███···
    104.36 |   │███│░███░█       |▏██████ ◀POC
```

## 가정 & 제약

- **PLAY 간 import 금지 (CLAUDE.md §3).** PLAY17 매물대 logic을 *별도로 구현*. 두 PLAY 사이에 가벼운 중복이 있다 — 의도된 결과.
- **SMA window > 시계열 길이면 그 라인은 그려지지 않음.** 60일 데이터에 SMA120 요청하면 SMA120은 빈 상태로 무시. 에러 안 냄.
- **그리드 등간격(가격, 영업일).** 가격 축 로그 스케일 X. 날짜 축은 영업일 간격(공휴일 압축 — 입력 CSV에 휴일 없으면 자연 영업일).
- **X축 라벨은 첫·중간·마지막 3개만.** 시계열 길어지면 라벨 사이 공백이 늘어남. 끝 라벨이 width 밖이면 잘려서 마지막 한 글자만 보일 수 있음 — 알려진 cosmetic 한계, 차트 본문 해석에는 영향 없음.
- **DOJI 임계 0.01%.** open과 close 차이가 그 미만이면 DOJI 처리. 일반적 정의.
- **거래량 축 단위 없음.** 사이드바는 *상대치*(최대 bar = 매물대 최고 bin). 절대 거래량은 PLAY17 JSON으로 확인.
- **컬러 없음.** ANSI 컬러 코드 안 씀. 터미널·로그 어디서나 동일 폭.
- **신호·추천 없음.** "SMA20 골든크로스" 같은 해석은 본 모듈 범위 밖. 사용자가 시각적으로 판단.
- **인코딩.** 출력은 UTF-8 (`█`, `▏`, `◀` 등). cp949 터미널에서 깨질 수 있음 — PowerShell은 `chcp 65001` 필요할 수 있음.
- **디스패치 안전.** 60일·height 24 = O(n×h) ~수십 ms.

## 변경 이력
- 2026-05-19 — 최초 생성. 캔들 + SMA(20/60/120) overlay + 매물대 사이드바, POC 마커, 표준 라이브러리 only.
