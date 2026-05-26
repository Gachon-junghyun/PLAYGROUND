# PLAY17_volume_profile — 매물대 (Volume Profile)

## 목적
OHLCV CSV → 가격 bin × 누적 거래량 분포. POC(거래량 최대 bin), Value Area(누적 70%), 매물대 top-3를 텍스트 바 차트 + JSON으로 출력. 권유 layer 아님, 단순 분포 계산.

## 실행법

```powershell
# 의존성: 표준 라이브러리만.

# 1) text bar chart
python PLAY17_volume_profile/volume_profile.py PLAY14_trade_planner/sample_ohlcv.csv --bins 20

# 2) JSON 요약
python PLAY17_volume_profile/volume_profile.py PLAY14_trade_planner/sample_ohlcv.csv --bins 30 --json

# 3) 봉의 high~low 전체 범위에 거래량을 균등 분할 (정확하지만 약간 무거움)
python PLAY17_volume_profile/volume_profile.py PLAY14_trade_planner/sample_ohlcv.csv --bins 30 --weighting hl_split

# 4) PLAY15로 받아 바로 분석
python PLAY15_market_data_fetch/market_data_fetch.py 298040 --source dummy --out t.csv
python PLAY17_volume_profile/volume_profile.py t.csv --bins 25
```

주요 인자:
- `csv` (필수) — OHLCV (`date,open,high,low,close,volume`).
- `--bins` — 가격 분할 수. default 30.
- `--weighting` — `tpv`(typical price 한 bin에 적재) | `hl_split`(봉 범위 균등 분할). default `tpv`.
- `--json` — JSON 요약 출력 (text chart 대신).
- `--width` — text chart bar 폭. default 40.

## 입력 / 출력

- **입력 CSV:** PLAY14·PLAY15 호환 헤더 (`date,open,high,low,close,volume`).
- **출력 (text, default):** 가격 역순 바 차트 + `VA`(value area) · `POC` · `TOP`(top-3) · `◀NOW`(last_close 위치) 마커.
- **출력 (JSON):** `poc` / `value_area` / `top3` / `price_range` / `total_volume` / `last_close`. 전체 profile 배열은 `--json` 출력에서 생략(`profile_len`만).

샘플 (PLAY14 더미 sample_ohlcv.csv, bins=20):
```
range      99.07 ~     129.07    last_close=127.97    POC≈114.82
VA[70%] 103.57 ~ 123.07
... (위쪽 last_close 부근은 거래량 빈약, 중간대 매물대 두꺼움)
```
→ `sample_profile.json`에 동일 데이터 JSON 저장.

## 가정 & 제약

- **POC 정의.** "거래량 최대 단일 bin". bin 개수에 따라 POC 위치가 달라진다. bin=30~50이 일반적, bin=100 이상은 노이즈로 의미 희석.
- **Value Area 알고리즘.** POC에서 좌우 큰 쪽으로 1 bin씩 추가하며 70% 도달 시 정지. 표준 마켓 프로파일 정의에 부합. 좌우 동률이면 left 우선.
- **TPV vs HL_SPLIT.**
  - `tpv`: 한 봉의 거래량을 (high+low+close)/3 가까운 한 bin에만 적재. 빠르고 단순, 봉이 짧을 때 적합.
  - `hl_split`: 봉의 high~low 범위에 걸친 bin 개수로 거래량 균등 분할. 갭/장대봉이 많을 때 더 자연스러움. *시간 가중치는 반영 안 함* — 봉 안에서 시점별 거래량 분포는 알 수 없음.
  - 진짜 정확한 매물대는 tick 단위 데이터가 필요. 본 모듈은 OHLCV daily 기반 근사.
- **bin 크기는 등간격(가격 기준).** 로그 스케일·ATR 정규화 안 함. 변동성 큰 종목일수록 bin 분포가 한쪽으로 쏠릴 수 있음.
- **last_close 마커.** `◀NOW`는 마지막 행의 close가 위치한 bin 표시. 거래 신호가 아니라 단순 위치 표시.
- **데이터 결손 처리 없음.** 갭/거래정지일 그대로 처리. 거래량 0이면 해당 일자는 분포에 기여 안 함.
- **시그널·권유 없음.** "매물대 돌파/지지" 같은 해석은 본 모듈에서 안 한다. 사용자가 결과를 보고 판단.
- **디스패치 안전.** 60일·20 bin = 단순 O(n×bins) ~수십 ms.

## 변경 이력
- 2026-05-19 — 최초 생성. POC + VA 70% + top-3, tpv/hl_split weighting, text chart + JSON. PLAY14 더미 데이터 60일 sample 검증.
