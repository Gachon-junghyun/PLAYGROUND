# PLAY18_thesis_scorecard — thesis 예측 채점 모듈

## 목적
mvp `refine_recommend.md §2-1` 양식(boolean 임계 박제 예측)을 받아 hit/miss/pending/invalid로 채점하고, §2-2 누적 ledger에 추가 가능한 markdown row를 출력. 자동 채점 가능한 예측만 박제하라는 원칙을 코드 layer에서 강제하는 도구.

## 실행법

```powershell
# 의존성: 표준 라이브러리만.

# 1) 샘플 예측 채점 (markdown ledger row)
python PLAY18_thesis_scorecard/thesis_scorecard.py PLAY18_thesis_scorecard/sample_predictions.json --as-of 2026-10-20

# 2) JSON 출력
python PLAY18_thesis_scorecard/thesis_scorecard.py PLAY18_thesis_scorecard/sample_predictions.json --as-of 2026-10-20 --format json

# 3) 다른 채점 기준일
python PLAY18_thesis_scorecard/thesis_scorecard.py preds.json --as-of 2026-06-01
```

## 입력 / 출력

**입력 JSON 스키마** (단일 dict 또는 배열):
```json
{
  "prediction_id": "2026-05-19-POWER-F26-01",
  "claim": "12일 -22% + 컨센 유지 = F26 분리 레짐",
  "direction": "bull",
  "judge_at": "2026-07-03",
  "hit_when":  {"field": "upside_pct", "op": "<",  "threshold": 15.0},
  "miss_when": {"field": "upside_pct", "op": ">=", "threshold": 15.0},
  "observed":  {"upside_pct": 12.4},
  "notes": "298040 효성중 7/3 종가..."
}
```

**op 지원:** `>=`, `<=`, `>`, `<`, `==`, `!=`.

**출력 (markdown, default):**
```
| 예측 ID | 판정 시점 | 도래 여부 | hit/miss/pending | 채점 근거 |
|---|---|---|---|---|
| 2026-05-19-POWER-F26-01 | 2026-07-03 | 도래 | hit | upside_pct=12.4 < 15.0  ✓  ... |
| 2026-05-19-POWER-F44-01 | 2026-10-15 | 도래 | miss | law_passed=True NOT == False ✗ ... |
| 2026-05-19-POWER-F23-01 | 2026-08-01 | pending | invalid | observed에 필요한 field 없음 ... |
```

**출력 (json, `--format json`):** `[{prediction_id, status, reason, judge_at, as_of}, ...]`. status는 `hit|miss|pending|invalid`.

샘플 4건 (`sample_predictions.json`) — 5/19 power_infra thesis 박제 케이스 더미:
- F26 분리 레짐: 가상 7/3 관측값 upside_pct=12.4 → hit
- F08 lead time: 가상 8/15 36개월 → hit (anti_signal 미발동)
- F44 송전법: 가상 10/15 본회의 통과 → miss (bear thesis 무력화)
- F23 META CapEx: 8/1 미관측 → pending/invalid

## 가정 & 제약

- **boolean 임계 강제.** 모호한 예측("추적 1순위", "주의 깊게 본다")은 입력 자체가 불가 — `hit_when` field/op/threshold 셋 다 필수. 이게 refine_recommend.md §2-1의 핵심 원칙이고 본 모듈은 그 강제 layer.
- **`status` 4종.**
  - `hit`: hit_when 만족
  - `miss`: hit_when 불만족 (또는 miss_when 만족)
  - `pending`: as_of < judge_at *이고* observed 비어있음
  - `invalid`: observed에 필요한 field가 없거나 op 미지원
- **observed가 있으면 judge_at 도래 전이라도 채점.** 백테스트·재채점 용도. 실시간 진행 중인 예측에 부분 observed를 채워 넣고 미리 보는 것도 허용. 운영상 ledger에 commit 할 때는 *judge_at 도래 후*가 원칙.
- **자동 hit_rate 집계 없음.** 본 모듈은 단건 채점만. 누적 ledger 분석(함수별 hit rate, 산업별 hit rate, F08 demotion 시그널 등)은 다음 PLAY에서. 현재는 markdown row 출력까지만.
- **`direction` 필드 미사용.** 입력 필드는 받지만 채점 logic은 hit_when만 사용. direction은 ledger 가독성과 향후 집계용.
- **`miss_when` 자동 도출.** miss_when 미지정 시 `not hit` = miss로 간주. 단 invalid는 별도.
- **시간 기준은 ISO date 문자열.** datetime 시·분 무시.
- **mvp 디렉토리 read-only.** refine_recommend.md를 직접 갱신하지 않는다. 채점 결과 markdown row를 사용자가 수동으로 `_prediction_ledger.md`에 append.
- **자동 데이터 페치 없음.** observed 채우기는 사용자/다른 PLAY 책임. (PLAY15 fetcher + 별도 어댑터로 자동화 가능 — 다음 라운드 후보)
- **디스패치 안전.** 단순 dict 비교, 100건도 수십 ms.

## 변경 이력
- 2026-05-19 — 최초 생성. boolean 임계 4종 status 채점, markdown/json 출력, 5/19 power_infra 4건 더미 박제.
