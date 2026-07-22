# 추출 리포트

- 총 레코드: **192**
- core tier: 4 (2.1%) — 목표 10% 이하 OK

## 타입 분포
- proposition: 184
- tool_card: 6
- exemplar: 2

## aspect 분포
- 사고스타일: 181
- 도메인규칙: 7
- 작업유형: 1
- 출력형식: 3

## 소스 분포
- card:PLAY28_insight_distill_v2: 93
- func:r5_v4: 87
- module_readme: 6
- mvp_principle: 4
- exemplar_skeleton: 2

## dedup (card_id 중복 제거)
- 제거된 중복: 64건 (우선순위 낮은 소스에서 탈락)

## 금지문 스캔 (셀프체크: 긍정 명령형)
- 셀프체크 strict-grep(`마라/말 것/금지/피하/않/안 된다`) 매치: **52건**
  - 주의: `않/안` 은 서술 내용에도 흔해서 대부분 *오탐*(금지 명령이 아님).
- 진짜 금지 명령형(`하지 마/말 것/해선 안/금지한다` 등) 매치: **0건**
  - 원본 증류(PLAY13/28/43)가 이미 서술-긍정형으로 뽑아둬서 변환 대상 0건. 셀프체크 '금지문 0건' 통과.

## trigger 문체 적합 (상황 서술: ~때/작업/상황/구간/시점/국면/경우)
- 적합: **187/192** (97.4%)
- 미적합 5건(원본 함수 trigger_when 이 액션으로 끝남, 폴리시 패스 대상): f-013, f-015, f-023, f-024, f-031

## conflict 검사
- 본 어댑터는 card_id 기준 정확 중복만 병합(위 dedup). 의미 모순 conflict_group 부여는 Part B 적재 후 임베딩 근접쌍으로 점검 예정(현재 모두 null).

## 판단이 어려웠던 항목
- 카드 trigger: 원본 `trigger_conditions`가 구체 뉴스 이벤트라 컴파일러 trigger(상황 서술)와 문체가 어긋남 → labels+title로 '~판단할 때' 템플릿 합성. 변별력은 함수 trigger_when만 못함(README 명시).
- R5 함수를 procedure가 아닌 proposition으로 분류: 단계 순서가 있는 절차가 아니라 단일 추상 사고 무브라 셔플 테스트상 proposition. trigger_when이 이미 상황 서술이라 그대로 채택.
