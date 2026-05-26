# PLAY14_trade_planner — ATR 기반 진입/손절/익절/사이즈 계산기

## 목적
사용자가 이미 매매 가설을 세웠을 때, 그 가설대로 진입하면 "얼마 잃을 수 있고 / 몇 R 목표가 어느 가격이고 / 몇 주 사야 하는가"를 산술로만 답하는 단일 모듈. 매매 funnel 3·4·5단계(진입가·타이밍·청산·사이즈)의 *계산 layer*이며, 권유·시그널 생성·백테스트는 하지 않는다 (mvp §9-1 원칙 준수).

## 실행법

```powershell
# 의존성: 표준 라이브러리만. pip install 불필요.

# 1) 번들된 60일 더미 데이터로 빠르게 동작 확인
python PLAY14_trade_planner/trade_planner.py --demo

# 2) 실제 종목 CSV로 (헤더: date,open,high,low,close,volume)
python PLAY14_trade_planner/trade_planner.py --csv path/to/ohlcv.csv `
    --direction long --entry 127.5 --equity 10000000 --risk-pct 0.01 `
    --stop-atr 1.5 --targets 1,2,3 --atr-period 14

# 3) JSON 출력
python PLAY14_trade_planner/trade_planner.py --demo --json
```

주요 인자:
- `--csv` / `--demo` (둘 중 하나 필수)
- `--direction long|short` — long의 stop은 entry 아래, short은 위.
- `--entry` — 미지정 시 CSV 마지막 종가.
- `--equity` — 계좌 자본. 단위 무관, 출력에 동일 단위로 표시됨.
- `--risk-pct` — 한 거래에 잃을 의향이 있는 자본 비율. 가드: (0, 0.1]. 0.1 넘으면 에러.
- `--stop-atr` — `손절거리 = ATR × 이 값`. 이 거리가 곧 1R이 된다.
- `--targets` — R-multiple 사다리. `"1,2,3"`이면 1R/2R/3R 가격을 보여줌.
- `--atr-period` — Wilder ATR 윈도, default 14.

## 입력 / 출력

- **입력 CSV 헤더**: `date,open,high,low,close,volume` (정확히 이 이름. 누락 시 에러.)
- **최소 행 수**: `atr_period + 1` 이상 (default 15행). 부족하면 에러.
- **출력 (텍스트, default)**: 한 화면 안에 들어가는 6~10줄.
  - `ATR`, 20일 일간수익률 시그마
  - `entry`, `stop`, `stop_distance` (몇 시그마 거리인지 함께)
  - `risk_per_share`, `risk_amount`, `position_size_shares`, `position_value`, `exposure_pct_of_equity`
  - R-multiple 사다리: 각 R마다 가격·주당이익·도달시 총이익
  - `notes`: 너무 타이트한 stop, 자본 초과 노출, 추격매수 형태 등 자동 가드 코멘트
- **출력 (JSON, `--json`)**: 위 항목을 dict 한 덩어리로 stdout 출력. 다른 도구로 파이프 가능.

### 샘플 실행 (번들 데이터)

```
$ python trade_planner.py --demo
as_of=2026-05-22  last_close=127.97  ATR(14)=2.3843  sigma_20d=0.0149
direction=long  entry=127.97  stop=124.3935 (dist=3.5765, = 1.87× daily sigma)
risk_per_share=3.5765  × shares = risk_amount=100,000.0 (1.00% of equity 10,000,000)
position_size=27960.2605 shares  value=3,578,074.53  exposure=35.78% of equity
targets (R-multiple ladder):
  1.0R @ 131.5465  per-share +3.5765  total_at_target 100,000.00
  2.0R @ 135.123   per-share +7.153   total_at_target 200,000.00
  3.0R @ 138.6995  per-share +10.7295 total_at_target 300,000.00
```

## 가정 & 제약

- **권유 layer 아님.** 진입가·방향은 사용자가 외부에서 결정해야 한다. 이 모듈은 "이 진입가에서 ATR 기반 stop을 두면 얼마 잃고 얼마 벌 가능성이 있는가"만 답한다. mvp §9-1 (매수/매도 권유 금지) 원칙과 충돌하지 않게 의도적으로 추천 로직 없음.
- **R-multiple 정의.** `1R = ATR × stop_atr_mult`. 즉 stop-loss 거리가 곧 1R 단위. `--targets 1,2,3`은 entry에서 1R/2R/3R 떨어진 가격을 보여주는 것이지, "여기서 익절해라"는 시그널이 아니다.
- **ATR 구현.** Wilder smoothing. 첫 n개 TR의 단순평균으로 seed → 이후 `(prev*(n-1)+TR)/n`. TradingView·MetaTrader 기본값과 동일 정의. EMA/SMA 변형은 사용하지 않음.
- **Position size 계산은 분수주를 가정.** 한국 주식처럼 정수 단위만 가능한 거래소면 `round()`로 절삭/반올림한 뒤 실제 risk가 약간 달라진다 — 사용자가 호출 측에서 처리. (요건이 명시되지 않아 분수 그대로 둠.)
- **가드의 한계.** notes는 휴리스틱 4종: ① stop이 일간 sigma 1.5배 미만이면 경고, ② position_value > equity면 레버리지 경고, ③ entry가 last_close ±5% 밖이면 지정가/추격 형태 안내. 더 정교한 risk 모델(VaR, kelly 등)은 의도적으로 미구현.
- **risk_pct 상한 0.1.** 한 거래에 자본 10% 이상 거는 건 거의 항상 실수라서 코드 단에서 거부. 정 우회하고 싶으면 `plan_trade()`를 직접 호출하며 가드 조건만 풀면 되지만 README에 명시한 정책은 0.10.
- **CSV 정렬.** 시간 오름차순 가정 (오래된 게 위, 최신이 마지막 행). 거꾸로 들어오면 ATR·last_close가 잘못 계산된다. 입력 검증 안 함.
- **데이터 결손 처리 없음.** 갭(공휴일/거래정지)이 있어도 그대로 계산. ATR이 이상치를 한 행 잡으면 후속 일자까지 영향 — 입력 데이터 품질은 호출 측 책임.
- **통화/단위.** 가격과 equity 단위가 같다고 가정. KRW/share + KRW equity 일관성만 맞추면 됨. FX 환산 없음.
- **번들 더미 CSV는 가상 데이터.** `sample_ohlcv.csv`는 seed=42 가우시안 워크로 생성된 60일치 (2026-03-02 ~ 2026-05-22, 100 → 127.97). 실제 종목 아님 — 동작 검증·교습용.
- **외부 API 없음.** OHLCV 페치는 이 PLAY 범위 밖. 사용자가 별도로 CSV를 만들어 와야 한다. (mvp의 `module_text_chart` 또는 외부 데이터 소스에서 export.)
- **디스패치 안전.** 표준 라이브러리만 사용, --demo 실행이 100ms 안에 끝남. 45초 제약과 무관.

## 변경 이력
- 2026-05-19 — 최초 생성. ATR(Wilder) + R-multiple ladder + 휴리스틱 4종 가드(notes). 60일 더미 CSV 번들. CLI(텍스트/JSON) 지원.
- 2026-05-19 — rename PLAY3→PLAY14 (번호 충돌 해소). 기존 PLAY3_market_timing과 디렉토리명 겹침. README 제목·실행 예시 경로 동기 갱신.
