# PLAY15_market_data_fetch — OHLCV fetcher (PLAY14 호환 CSV 출력)

## 목적
ticker + days → PLAY14가 그대로 받을 수 있는 CSV(`date,open,high,low,close,volume`)를 만드는 단일 모듈. yfinance → KRX → 더미 순으로 fallback. 권유 layer 아님, 단순 데이터 페치 + 정규화.

## 실행법

```powershell
# 의존성: 표준 라이브러리만 필수. yfinance는 있으면 사용, 없으면 자동 fallback.
# (선택) pip install yfinance
# 또는 dummy/krx만 쓰려면 표준 라이브러리로 충분.

# 1) auto 모드 (yfinance → krx → dummy 순)
python PLAY15_market_data_fetch/market_data_fetch.py 298040 --days 60 --out PLAY15_market_data_fetch/out.csv

# 2) 강제로 dummy
python PLAY15_market_data_fetch/market_data_fetch.py 298040 --days 60 --source dummy --out PLAY15_market_data_fetch/out.csv

# 3) stdout으로 (pipe 가능)
python PLAY15_market_data_fetch/market_data_fetch.py AAPL --days 30 --source yfinance > aapl.csv

# 4) PLAY14에 바로 물려보기 (sanity)
python PLAY15_market_data_fetch/market_data_fetch.py 298040 --days 30 --source dummy --out t.csv
python PLAY14_trade_planner/trade_planner.py --csv t.csv --direction long `
    --equity 10000000 --risk-pct 0.01 --stop-atr 1.5 --targets 1,2,3
```

주요 인자:
- `ticker` — 한국은 6자리(298040), 미국은 심볼(AAPL).
- `--days` — 영업일 기준 길이. default 60.
- `--source` — `auto|yfinance|krx|dummy`. default `auto`.
- `--out` — 미지정 시 stdout으로 CSV.

## 입력 / 출력

- **입력:** ticker 문자열, days(int).
- **출력 CSV 헤더:** `date,open,high,low,close,volume`. PLAY14 `load_ohlcv()`와 정확히 호환.
- **stderr 로그:** 사용된 source, 시도 횟수, 실패 사유.

샘플 (`sample_298040.csv`, dummy, days=30):
```
date,open,high,low,close,volume
2026-03-20,101.0,105.0,100.51,104.42,107868
...
```

## 가정 & 제약

- **yfinance 미설치 시 자동 skip.** ImportError를 RuntimeError로 변환 후 다음 source.
- **KRX endpoint는 best-effort.** KRX는 OTP 2-step + ISIN 체크섬을 요구한다. 본 모듈은 ISIN 체크섬 자리를 더미로 보내고 단일 endpoint만 호출 → 응답이 비거나 400을 반환하는 경우가 잦다. 실제 KRX 데이터가 필요하면 `pykrx` 같은 라이브러리 사용 권장. 본 PLAY는 KRX 시도 실패 시 dummy로 fallback하므로 워크플로 자체는 안 깨지지만, *KRX 경로에서 실데이터를 받을 거란 기대는 하지 마라*. README에 명시한 대로 dummy fallback이 정상 동작.
- **dummy는 결정론적.** ticker MD5 → seed → 시작가/drift/sigma 결정. 같은 ticker는 항상 같은 시계열. 단 현재 날짜를 기준으로 영업일을 역산하므로 *호출일이 다르면 날짜 라벨은 달라진다* (가격 패턴은 동일).
- **dummy는 실데이터 아님.** 실제 종목 시세와 무관한 가우시안 워크. PLAY14 동작 검증·교습용으로만 사용.
- **시간 정렬.** 항상 오름차순(과거 → 최신). PLAY14가 이 정렬을 가정한다.
- **결측치 처리 없음.** yfinance가 NaN을 주면 그대로 float 변환 — NaN이면 후속 ATR 계산에서 깨질 수 있음. 호출 측에서 검증 필요.
- **rate limit/캐싱 없음.** 같은 ticker를 반복 호출하면 매번 fetch. yfinance API 정책 위반 주의.
- **시크릿 없음.** API 키 사용 안 함. yfinance는 무료 endpoint, KRX는 공개 페이지.
- **디스패치 안전.** 가장 무거운 경로(yfinance + krx 시도 후 dummy fallback)도 ~8초 안에 끝나는 걸 sanity check 완료. 디스패치 45초 제약과 무관.
- **샘플 출력 `sample_298040.csv`/`auto_298040.csv` 번들.** 30영업일 dummy 데이터. 실제 효성중공업 시세와 *무관*. PLAY14·PLAY17·PLAY20 입력 검증용.

## 변경 이력
- 2026-05-19 — 최초 생성. yfinance/krx/dummy 3-source fallback, PLAY14 호환 CSV. KRX endpoint는 best-effort (실패 시 dummy fallback이 정상 동작).
