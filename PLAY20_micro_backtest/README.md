# PLAY20_micro_backtest — 한 줄 룰 백테스트 (R-multiple 기반)

## 목적
entry 룰 1줄 + OHLCV CSV → 거래 리스트 + 승률·평균 R-multiple. ATR 손절/익절·max_hold·슬리피지 포함. look-ahead 회피. 권유 layer 아님 — 단순 룰 시뮬레이터.

## 실행법

```powershell
# 의존성: 표준 라이브러리만.

# 1) 20일 신고가 돌파 룰, long
python PLAY20_micro_backtest/micro_backtest.py PLAY20_micro_backtest/sample_252d.csv `
    --rule "breakout_high:20" --direction long --stop-atr 1.5 --take-atr 3.0

# 2) SMA 10/30 골든크로스
python PLAY20_micro_backtest/micro_backtest.py PLAY20_micro_backtest/sample_252d.csv `
    --rule "sma_cross_up:10,30" --json

# 3) 신데드 short
python PLAY20_micro_backtest/micro_backtest.py sample_252d.csv `
    --rule "breakdown_low:20" --direction short --stop-atr 1.5 --take-atr 2.0

# 4) PLAY15로 종목 데이터 받아 즉시 백테
python PLAY15_market_data_fetch/market_data_fetch.py AAPL --days 252 --source yfinance --out aapl.csv
python PLAY20_micro_backtest/micro_backtest.py aapl.csv --rule "sma_cross_up:20,60"
```

주요 인자:
- `csv` (필수) — OHLCV.
- `--rule` (필수) — DSL: `sma_cross_up:fast,slow` | `sma_cross_down:fast,slow` | `breakout_high:w` | `breakdown_low:w`.
- `--direction` — `long|short`. default long.
- `--atr-period` — Wilder ATR window. default 14.
- `--stop-atr` — 손절거리 = ATR × 이 값. default 1.5R.
- `--take-atr` — 익절거리 = ATR × 이 값. default 3.0R.
- `--max-hold-days` — 청산 안 되면 시장가. default 20.
- `--slippage-pct` — 양방향. default 0.001 (0.1%).
- `--json` — summary + trades JSON.

## 입력 / 출력

- **입력 CSV:** PLAY14·PLAY15 호환 헤더.
- **출력 (text):**
  - 1행: rule·dir·rows·stop/take 파라미터
  - 2행: trades·win_rate·avg_R·sum_R·best/worst R
  - 거래별 표: signal_date · entry_date · exit_date · entry · exit · why(stop/take/time) · R · days
- **출력 (json):** `{summary, trades[]}`.

샘플 (`sample_252d.csv` — 252영업일 dummy 298040, breakout_high:20 long):
```
trades=8  win_rate=12.5%  avg_R=-0.56  sum_R=-4.51
2025-04-03→04-04→04-15  long  entry 109.85 → exit 118.62 (take, +1.97R, 7d)
2025-04-21→04-22→04-22  long  entry 120.78 → exit 116.64 (stop, -1.03R, 0d)
...
```
(dummy 가우시안 워크라서 결과는 우연. 실제 종목 적용 시 의미 부여 X.)

## 가정 & 제약

- **look-ahead 회피.**
  - 시그널은 bar t의 close에서 판단 → t+1 *시가*로 entry.
  - 손절/익절은 t+1 이후 bar의 high/low로 확인.
- **같은 bar에 stop+take 동시 도달 시 stop 우선.** 보수적 가정. 실제로는 인트라데이 경로에 따라 다르지만 OHLCV daily 로는 결정 불가 → 보수 채택.
- **연속 시그널.** 진입 중에 새 시그널이 나와도 무시. 청산 후 다음 bar부터 재진입 가능. (피라미딩·다중 포지션 미지원.)
- **슬리피지.** 양방향 percent 슬립 (long 진입: 시가×(1+s), 청산: ×(1-s)). 호가창·체결 슬립 모델링 없음.
- **수수료 0.** 별도 옵션 미제공 — 필요하면 slippage_pct에 함산.
- **분수주 가정.** position size 계산 없음 (이 PLAY는 R-multiple만 본다). 자본·사이즈는 PLAY14에서.
- **DSL 4종만.** sma_cross_up/down (2개 SMA 교차), breakout_high (n일 신고가 종가 돌파), breakdown_low (n일 신저가 종가 이탈). 거래량·RSI·MACD 등 미지원 — 다음 라운드.
- **win/loss 정의.** R-multiple > 0이면 win. R == 0 (정확히 본전)은 loss로 집계 (`r > 0` 비교).
- **dummy 데이터는 실종목 아님.** 결과의 R-multiple·승률은 룰의 실효성 판단 근거가 *못 된다*. 본 PLAY는 코드·인터페이스 검증용이지 룰 유효성 입증용이 아님.
- **52주 신고가 같은 longer-window 룰은 데이터 길이 필요.** 252일 dummy로는 sma_cross_up:50,200 같은 룰은 시그널이 거의 안 발생할 수 있음.
- **mvp 디렉토리 read-only.** mvp의 백테스트·시뮬레이션 모듈을 참조 안 함.
- **디스패치 안전.** 252일 단일 패스 ~50ms.

## 변경 이력
- 2026-05-19 — 최초 생성. 4종 룰 DSL, ATR 손절/익절, look-ahead 회피, 슬리피지 0.1%. 252일 dummy 샘플 박제.
