# PLAY16_thesis_to_plan — state_report.md → PLAY14 입력 어댑터

## 목적
mvp `research_Mvp/llm_outputs/.../state_report.md`의 Block 6 표(`현재가` + `컨센 상승여력`)에서 종목별 entry·direction·confidence·atr_mult_suggested를 추출해 PLAY14 trade_planner가 바로 받을 수 있는 JSON으로 변환. 권유 layer 아님 — *thesis 문서에 이미 담긴 시장 가정을 기계가 읽을 수 있는 형태로 옮기는 어댑터*.

## 실행법

```powershell
# 의존성: 표준 라이브러리만.

# 1) state_report.md 전체에서 7사 plan 추출
python PLAY16_thesis_to_plan/thesis_to_plan.py `
    "C:\Users\fivep\OneDrive\Desktop\mvp\research_Mvp\llm_outputs\2026-05-19\power_infra_20260519\state_report.md" `
    --pretty --out PLAY16_thesis_to_plan/plans.json

# 2) 특정 종목만
python PLAY16_thesis_to_plan/thesis_to_plan.py state_report.md --ticker 298040 --pretty

# 3) 추출한 plan을 PLAY14에 물려 ATR 기반 손절/사이즈까지 산출
#    (별도 OHLCV CSV 필요 — PLAY15로 생성)
python PLAY15_market_data_fetch/market_data_fetch.py 298040 --source dummy --out t.csv
python PLAY14_trade_planner/trade_planner.py --csv t.csv `
    --direction long --entry 3555000 --equity 100000000 `
    --risk-pct 0.01 --stop-atr 1.52 --targets 1,2,3
```

주요 인자:
- `path` — state_report.md 경로 (mvp 출력물).
- `--ticker` — 6자리 코드로 필터. 미지정 시 표 안의 모든 종목.
- `--out` — JSON 저장 경로. 미지정 시 stdout.
- `--pretty` — indent=2 JSON.

## 입력 / 출력

- **입력:** state_report.md (markdown 파일). 표 헤더에 `현재가`와 `상승여력`이 둘 다 포함된 행을 Block 6 표로 인식.
- **출력 JSON 스키마** (배열의 각 원소):
  - `ticker` (str, 6자리) · `name` (str)
  - `entry` (float, KRW) — 현재가 값을 그대로
  - `direction` (`long`|`short`) — 상승여력 부호
  - `confidence` (float, 0~1) — `min(|상승여력|/50, 1.0)`
  - `upside_pct` (float) — 원본 상승여력 %
  - `atr_mult_suggested` (float) — `0.8 + confidence*1.2` (0.8~2.0R)
  - `source_row` — 추출 근거 (종목셀·현재가·상승여력 원본 문자열)

5/19 power_infra 7사 박제 결과 (`plans_power_infra_20260519.json`):
```
034020 두산에너빌 long  conf=0.887 (+44.34%)
298040 효성중     long  conf=0.601 (+30.04%)
267260 HD현대일렉 long  conf=0.738 (+36.89%)
062040 산일전기   long  conf=0.392 (+19.62%)
052690 한전기술   long  conf=1.000 (+52.17%)
010120 LS일렉    short conf=0.019 (-0.95%)   ← 컨센 도달
001440 대한전선   short conf=0.112 (-5.58%)   ← 컨센 도달
```

## 가정 & 제약

- **mvp Block 6 표 양식 의존.** `| 종목 | 현재가 | ... | 컨센 상승여력 | ...` 헤더를 가정. mvp가 향후 표 헤더명을 바꾸면 (예: "상승여력" → "타깃가") 파서가 깨진다. 다른 thesis 문서에는 그대로 적용되지 않을 수 있음.
- **종목셀 형식.** `효성중공업 298040`, `효성중(298040)`, `효성중（298040）` 정규식으로 모두 캐치. 종목명에 한글·영문·숫자·중점·공백 허용. 그 외 특수문자 들어가면 누락.
- **현재가 파싱.** 콤마·`**`·`*` 제거 후 float. 통화 기호나 단위(`원`) 들어가면 ValueError로 행 skip.
- **상승여력 부호=direction.** `+` 이상 long, `-` short. 이건 *컨센 목표주가 기준*이지 본 어댑터의 권유가 아니다. 컨센이 틀릴 가능성·thesis 자체가 컨센과 충돌(F26 분리 레짐)할 가능성은 어댑터 layer에서 처리하지 않음 — 사용자 판단.
- **confidence 정규화.** `|upside|/50` cap 1.0. 50%는 임의 기준 — mvp Block 6에서 한전기술이 +52% 단일 max라서 그쪽이 confidence 1.0이 되도록 잡음. 다른 산업/시점에서 그대로 의미 가지진 않음.
- **atr_mult_suggested는 안내값.** confidence 높을수록 stop을 멀리(0.8R → 2.0R). 단순 매핑 — 변동성·이벤트 위험 반영 안 함. PLAY14에서 사용자가 override 가능.
- **thesis 강도(§1 핵심 명제)는 미반영.** 본 어댑터는 *Block 6 정량만* 읽는다. "양분화 thesis" 같은 문맥 정보는 무시. 향후 §1 키워드(강화/약화/stall) 가중치 추가 가능 — 다음 라운드.
- **단위.** entry는 KRW (state_report 한국 종목). 다른 통화는 단위만 다를 뿐 어댑터는 무차원으로 처리.
- **mvp 디렉토리 read-only.** 본 PLAY는 절대 mvp 파일을 수정하지 않는다.
- **디스패치 안전.** 표준 라이브러리만, 단일 파일 파싱 ~50ms.

## 변경 이력
- 2026-05-19 — 최초 생성. state_report.md Block 6 → 7사 plan JSON. 5/19 power_infra thesis 박제 (`plans_power_infra_20260519.json`).
