# PLAY22_corpus_drift

## 목적
insight_corpus의 daily/ 파일들을 시간순으로 훑어 산업·사고함수·품질점수·promotion 분포가 어떻게 흔들리는지(드리프트) 측정한다. 한 렌즈로 쏠리는 에코챔버, 품질 급락, 측정 결손을 빨리 잡는 게 목표.

## 실행법
```powershell
# 의존성 없음 (Python 표준 라이브러리만). Python 3.9+

# 동봉된 sample(실제 daily 5/19~5/25 스냅샷)으로 즉시 실행
python PLAY22_corpus_drift\drift.py

# 라이브 코퍼스를 직접 가리키기
python PLAY22_corpus_drift\drift.py --daily C:\Users\fivep\OneDrive\Desktop\mvp\research_Mvp\insight_corpus\daily

# 일자별 지표를 CSV로도 저장
python PLAY22_corpus_drift\drift.py --csv timeline.csv
```

## 입력 / 출력
- **입력:** `--daily` 폴더 안의 `LLM_create_YYYY-MM-DD.json` 파일들. 각 파일에서 `cards[].industry`, `cards[].auto_quality.score/grade`, `cards[].activated_R5_functions`, `cards[].primary_thinking_function`, `cards[].promotion_candidate`, `cards[].borrowed_R4_cards`, `summary.parser_cron_anomaly` 를 읽음.
- **출력:** 콘솔 텍스트 리포트 — 일자별 스냅샷, 품질 점수 추세 + 급락 플래그, 사고함수 다양성(지속 렌즈 vs 단발), 산업 집중도(HHI) 추세, 반복 차용된 R4 베이스 카드 top. `--csv` 지정 시 일자별 지표 CSV.

## 가정 & 제약
- **산업 집중도는 HHI**(Herfindahl)로 계산. 1=한 산업 독점, 1/n=완전 분산. 0.5 이상이면 과편중으로 플래그.
- **품질 급락 기준**은 전일 대비 mean_score 2점 이상 하락으로 임의 고정. 측정 이상(`parser_cron_anomaly`)이 같은 날 있으면 태그를 붙여 "진짜 품질 저하인지 측정 결손인지" 구분을 돕는다(자동 판정은 안 함).
- **에코챔버 휴리스틱**: 전 기간 매일 등장한 함수가 전체 함수 종류의 절반을 넘으면 "쏠림 의심" 플래그. 임계는 직관값이라 데이터 누적되면 재조정 필요.
- daily 파일 스키마는 날짜마다 미세하게 다를 수 있어 모든 필드를 `.get()`으로 방어적으로 읽음. 없는 필드는 조용히 건너뜀.
- 동봉 sample은 실제 mvp 코퍼스의 5/19~5/25 스냅샷 6일치(파일당 4카드)를 복사한 것. 라이브 데이터가 갱신되면 `--daily`로 원본을 직접 가리킬 것.
- 6일치는 추세 판단에 표본이 적다. HHI가 0.38로 6일 내내 평탄한 건 카드 수·산업 구성이 거의 고정이라 그런 것으로, 표본이 쌓여야 의미 있는 드리프트가 드러난다.

## 변경 이력
- 2026-05-25 — 최초 생성. daily 6일치 드리프트 리포트(점수 추세/함수 다양성/산업 HHI/차용 카드) 구현, 실제 스냅샷 sample 동봉.
