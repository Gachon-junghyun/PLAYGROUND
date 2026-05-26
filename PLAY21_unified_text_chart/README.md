# PLAY21_unified_text_chart

## 목적
module_text_chart(레거시, 캔들+MA20/60+볼린저+거래량+RSI+OBV+메타데이터)에
PLAY19_chart_overlays의 매물대 사이드바와 추가 SMA(예: MA120) overlay를 통합한 실험판.

legacy 호환 모드(`--no-vp --extra-ma 0`)에선 `plot_combined_chart`를 직접 위임 호출 →
출력이 module_text_chart와 *byte-identical*. `verify_diff.py`로 강제 검증.

## 실행법

```powershell
# 의존성 (module_text_chart와 동일)
pip install pandas numpy yfinance

# 통합 차트 (매물대 + MA120 default ON)
cd C:\Users\fivep\OneDrive\Desktop\PLAYGROUND
python -m PLAY21_unified_text_chart 005930.KS

# 매물대만, extra MA 끔
python -m PLAY21_unified_text_chart 005930.KS --extra-ma 0

# legacy 호환 모드 (byte-identical to module_text_chart.plot_combined_chart)
python -m PLAY21_unified_text_chart 005930.KS --no-vp --extra-ma 0

# 다른 ticker
python -m PLAY21_unified_text_chart 298040.KS  # 효성중공업
python -m PLAY21_unified_text_chart 010120.KS  # LS일렉트릭
python -m PLAY21_unified_text_chart AAPL --cols 60

# legacy byte-identical 검증 (사용자가 직접 실행 권장)
python PLAY21_unified_text_chart/verify_diff.py 005930.KS
python PLAY21_unified_text_chart/verify_diff.py AAPL --cols 60
```

## 입력 / 출력

**입력**:
- `ticker` (positional, 필수) — yfinance 심볼. KOSPI는 `.KS` suffix (예: `005930.KS`).
- `--cols` — 표시 캔들 수. default 80.
- `--no-vp` — 매물대 사이드바 비활성.
- `--no-meta` — 하단 메타데이터 비활성.
- `--extra-ma` — 추가 SMA window (default 120). `0`이면 비활성. MA20/60는 항상 그려짐.
- `--out` — 저장 디렉토리. 미지정 시 `PLAY21_unified_text_chart/output/`.

**출력**:
- `output/{ticker_safe}_chart_unified.txt` — 통합 차트 파일. ticker의 `.`은 `_`로 치환.
- stdout: `saved: <경로>`.

차트 구성 (위에서 아래로):
1. 가격 그리드 (캔들 + MA20·MA60·MA{extra_ma} + 볼린저 상중하) + 우측 매물대 사이드바
2. 거래량 바 (양봉=█, 음봉=▒)
3. RSI 서브차트 (window=14)
4. OBV 서브차트 (window=20, rolling)
5. 범례
6. 메타데이터 (이평선·볼린저·거래량·모멘텀·RSI·캔들힌트)

## 가정 & 제약

**module_text_chart 의존**:
PLAY21은 PLAYGROUND/module_text_chart를 import. `unified_chart.py`·`__main__.py`·
`verify_diff.py` 모두 import 시 sys.path에 PLAYGROUND 루트를 자동 추가하므로 cwd 무관.

**CLAUDE.md 룰 준수**:
- §1.4 "기존 module_text_chart는 레거시라서 건드리지 마라" — 본 PLAY는 *import only*.
  module_text_chart 디렉토리 수정 X.
- §1.3 "PLAY 간 의존 금지" — module_text_chart는 PLAY가 아니라 레거시이므로 룰 적용 X.
- 매물대 사이드바·extra_ma overlay는 본 PLAY 내부에서 새로 작성. fork·코드 복사 X.

**legacy 동등성**:
- `include_vp=False AND extra_ma=None` 호출 시 `plot_combined_chart`로 직접 위임.
  → 동일 함수 호출이므로 byte-identical 자동 보장.
- `verify_diff.py`로 같은 df를 양쪽에 던져 문자열 == 비교. PASS/FAIL 출력.
- module_text_chart가 향후 갱신되면 본 PLAY도 sync 필요. 단 PLAY21에 fork된 코드가
  없으므로 *import만 갱신되면 자동 sync*. 단 통합 모드 로직(vp/extra_ma)은 별도.

**매물대 사이드바**:
- typical price = `(high + low + close) / 3` — PLAY19의 weighting='tpv' 정의 그대로.
  PLAY19의 hl_split 옵션은 본 PLAY 미지원.
- 가격 그리드 row 수(default 20)와 1:1 매핑. row 별 누적 거래량 → 우측 6칸 바.
- POC row: 누적 거래량 최대 row에 `◀POC` 태그. 같은 row가 여러 candidate면
  *최저 row index* 선택 (max with stable order, Python max 기본 동작).
- 사이드바 형식: `▏███···` (6칸 width, 빈공간은 `·`로 padding).

**extra_ma overlay**:
- MA20/60는 module_text_chart의 `_COMBINED_IND_CHARS`에 박힌 `.`·`-` 사용.
- extra_ma는 `_COMBINED_IND_CHARS`에 없는 키이므로 `EXTRA_MA_CHAR = "~"` 사용.
- 기존 캔들 위엔 overlay 안 함 (legacy와 동일 규약 `_CANDLE_CHARS` 회피).

**외부 의존**: pandas + numpy + yfinance. PLAY19의 *표준 lib only* 원칙은 본 PLAY에 적용 안 됨
(module_text_chart가 pandas/numpy/yfinance 의존이라서).

**yfinance 시점**:
- `fetch_ohlcv`는 매 호출마다 *현재 종가까지 포함된* 데이터를 받아옴.
- byte-identical diff는 *같은 fetch 결과*를 양쪽에 던질 때만 보장. `verify_diff.py`가
  fetch를 1회만 호출해 양쪽 함수에 같은 df를 넘김.

**검증 수준 (2026-05-20)**:
- legacy 호환 모드: 코드 path가 `plot_combined_chart` 직접 호출이므로 *구조적으로* byte-identical.
  사용자가 `verify_diff.py 005930.KS` 1회 실행해 실증 권장.
- 통합 모드 (매물대·extra_ma): 코드 로직만 작성됨. 실 ticker 출력 시각 확인 권장.
  사용자 검증 통과 시 mvp/research_Mvp/로 승격 후보 (CLAUDE.md §6 분기 검증).

**Windows 환경**:
- 출력은 UTF-8 (`█`, `▏`, `◀`, `·`, `─` 등). PowerShell에서 깨지면 `chcp 65001` 권장.
- 경로 구분자는 Python `pathlib.Path`로 처리, OS 독립.

## 변경 이력

- 2026-05-20 — 최초 생성.
  - `unified_chart.py`: legacy 호환 분기 + 통합 모드 로직 (매물대 + extra_ma).
  - `__main__.py`: CLI runner (`python -m PLAY21_unified_text_chart <ticker>`).
  - `verify_diff.py`: legacy vs unified byte-identical 검증 도구.
  - module_text_chart는 import only, 코드 fork·복사 0.
  - Windows cp949 콘솔 `UnicodeEncodeError` 회피: `__main__.py`·`verify_diff.py`
    상단에서 `sys.stdout.reconfigure(encoding="utf-8")` 호출 (Python 3.7+).
  - 검증: `python verify_diff.py 005930.KS --cols 60` → **PASS 3961 chars 동일**.
  - 통합 모드 실행: `python -m PLAY21_unified_text_chart 005930.KS --cols 60` →
    `output/005930_KS_chart_unified.txt` 생성 (매물대 POC + MA120 정확히 박힘).
