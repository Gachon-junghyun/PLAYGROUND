# R4 카드 자동 템플릿 검출 보고

- 총 카드 수: **64**
- JSON 파싱 에러: 0
- framework 사전 정의 set 크기: 16
- 위반 카드 수: **0**

## Batch별 카드 수

| Batch | 카드 |
|---|---:|
| A1_moneygraphy_top4 | 6 |
| A2_moneygraphy_mid4 | 6 |
| A3_moneygraphy_small8 | 8 |
| A4a_moneycomics_top8 | 6 |
| A4b_moneycomics_bot8 | 5 |
| A5a_kimdante | 12 |
| A5b_oseon | 6 |
| A6a_jisikbu_top8 | 8 |
| A6b_jisikbu_bot8 | 7 |

## 검사한 패턴

- **P1_표면신호**: `라는 표면 신호가 실제로는`
- **P2_조건부전이**: `로 이어지는 조건부 전이 신호인지 확인한다`
- **P3_왜지금**: `왜 지금 ['\"][^'\"]+['\"]가 나타났고, 어떤 조건에서`
- **P4_호재악재판정**: `원초 신호를 곧바로 호재/악재로 판정하지 않고`
- **P5_1차2차분리**: `1차 영향과 2차 수혜/피해 대상을 분리한다`
- **P6_기존사고점프**: `카드의 기존 사고 점프는`
- **P7_framework복붙**: matched_thinking_pattern이 reverse_distillation_cards.json 사전 정의와 완전 일치

## 결과: 위반 0건 ✅

65장 모두 4 핵심 필드 자동 템플릿 패턴 미검출. R4 핵심 목표 달성.