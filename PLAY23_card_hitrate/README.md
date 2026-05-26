# PLAY23_card_hitrate

## 목적
R4 인사이트 카드의 방향성 콜(expected_direction + time_horizon)이 실제 가격으로 맞았는지 채점해서, 균일하게 8/10으로 찍힌 self-grade를 *실측 적중률 분산*으로 대체한다.

## 실행법
```powershell
# 의존성 없음 (Python 표준 라이브러리만). Python 3.9+

# 동봉 sample(R4 카드 + 합성 가격)으로 즉시 실행
python PLAY23_card_hitrate\hitrate.py

# 실제 데이터로
python PLAY23_card_hitrate\hitrate.py ^
  --cards C:\Users\fivep\OneDrive\Desktop\mvp\research_Mvp\insight_corpus\r4_all_cards.jsonl ^
  --predictions my_predictions.csv ^
  --prices my_prices.csv
```

## 입력 / 출력
- **입력 1 `--cards`:** R4 카드 jsonl. `card_id`로 `expected_direction`, `time_horizon`, `framework_used`를 자동 조인.
- **입력 2 `--predictions` (사용자 작성):** CSV 헤더 `card_id,ticker,as_of_date[,direction,horizon]`. 코퍼스에 없는 두 가지(**종목·기준일**)만 채우면 됨. direction/horizon 열은 선택(있으면 카드값 덮어씀).
- **입력 3 `--prices`:** CSV 헤더 `date,ticker,close` (date는 `YYYY-MM-DD`).
- **출력:** 콘솔 스코어카드 — 전체 방향성 적중률, 방향별/호라이즌별/프레임워크별 적중률, 카드별 HIT/MISS + 실제 수익률, 방향성 아님(제외) 목록, 데이터 부족 스킵 목록.

## 가정 & 제약
- **★ 코퍼스 자체엔 종목도 기준일도 없다.** R4 카드는 테마 단위라 ticker가 안 붙어 있고 생성 날짜도 없음. 그래서 이 PLAY는 사용자가 `predictions.csv`에 `ticker`와 `as_of_date`를 채워야만 돌아간다. 이 갭을 자동으로 메울 방법은 현재 없음(향후 watchlist.json 연계 후보).
- **방향 매핑:** 문자열에 `bull`→상승(+1), `bear`→하락(−1). 단 `conditional`/`mixed`/`neutral`이 들어가면 "방향성 베팅 아님"으로 보고 **적중률에서 제외**하고 따로 집계. R4 64장 중 약 절반(conditional 22 + mixed 10)이 여기 해당 → 전체 카드를 한 적중률로 묶는 건 무의미하므로 의도적으로 분리했다.
- **호라이즌→평가창(거래일):** short=5, mid=20, long=60, mid_to_long=40. `unspecified`는 스킵. 이 매핑은 `HORIZON_DAYS` 상수로 조정 가능.
- **거래일 인덱싱:** prices.csv에 실재하는 행을 기준으로 forward 인덱싱(시작=as_of_date 이후 첫 거래일, 종료=거기서 window행 뒤). 달력/공휴일 계산을 피하려는 선택이라, prices가 거래일만 담고 있다고 가정. 결측일이 많으면 window의 실제 캘린더 길이가 들쭉날쭉해질 수 있음.
- **적중=방향만** 본다(수익률 크기·손익비·거래비용 미반영). `conditional` 카드의 조건 충족 여부도 평가 안 함.
- **동봉 sample은 합성 가격**(seed=42 랜덤워크 80거래일)이다. 적중률 숫자 자체는 무의미하고 *파이프라인이 도는지* 확인용일 뿐. 실제 평가는 진짜 가격 CSV로 할 것.

## 변경 이력
- 2026-05-25 — 최초 생성. R4 카드 방향성 적중률 채점기 구현(방향성/비방향성 분리, 호라이즌→거래일창, 방향·호라이즌·프레임워크별 집계). R4 jsonl + 합성 가격 sample 동봉.
