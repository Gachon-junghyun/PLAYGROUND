# R5 v4 사고 함수 실행 프로토콜

작성: 2026-05-28
모범 사례: [samples/power_infra_2026q2_thesis_T3_execution.md](../samples/power_infra_2026q2_thesis_T3_execution.md)
사용 대상: R5 v4 87 함수(F01~F87) 라이브러리를 *진짜로 빌려 쓰는* 모든 thesis 작업.

---

## 0. 너의 역할

너는 **인용가가 아니라 수행자**다. R5 v4 함수의 가치는 *trigger_when을 적는 것*에 있지 않고, **검증 질문을 던지고 답을 찾고, anti_signal 발화 여부를 판정하고, action_at_trigger를 실행하는 것**에 있다. 인용은 사고의 외피다.

### 핵심 정의

- **인용**: "F87이 한전 vs 발전사 분리를 정당화한다"
- **수행**: "F87 Q1~Q3 9개 질문 던졌더니 한전은 정치 락(소매 요금 인상 0%), 발전사는 SMP 자동 연동 — 단, **상장 베타 부재** (GS EPS·SK E&S·포스코에너지 모두 비상장) → 진짜 베타는 두산에너빌리티(OEM 그릇 위치). 시드 카드 코퍼스가 두산을 빼서 *발전사*로 잘못 라벨링됨. **anti_signal에 '상장 베타 부재' 조건이 빠져 있음 → F87 spec 보강 후보 등록**"

---

## 1. 입력 (3개 슬롯)

작업 시작 전 3개 입력 확정:

1. **시드 thesis 카드** — PLAY31 B*카드 또는 사용자가 직접 제시. 1~3장. 카드의 `matched_thinking_pattern` + `reasoning_move` + `attention_hook` + `report_attribution.stance_vs_consensus`가 시드.
2. **연관 R5 v4 함수** — 시드 카드와 매칭되는 F* ID 리스트. 직접 매핑(같은 사고 회로) 또는 mirror(다른 도메인의 같은 골격). 2~5개 권장. 단일 함수 사용 금지 — 함수 결합이 단일보다 강함 (T3 사례 F87+F75+F53).
3. **도메인** — 산업·섹터. 예: "전력 인프라", "반도체 장비", "자동차 부품".

---

## 2. 6-Step 실행

### Step A — 함수 unpack (인용 금지)

선택한 각 F* 함수에 대해 다음 4개 필드를 **추출**:

```python
import json
with open('PLAY32_r5_merge_v4/data/r5_v4_thinking_functions.json','rb') as f:
    v4 = json.load(f)
for fn in v4['functions']:
    if fn['function_id'] in ('F87','F75','F53'):
        print(fn['verification_questions'])   # 검증 질문 모두
        print(fn['anti_signal'])              # 함수 무력화 조건
        print(fn['action_at_trigger'])        # watch/warn/critical/cross_ref/backtest
        print(fn['data_sources'], fn['indicators'], fn['indicators_examples_specific'])
```

**산출**: 함수당 9~12개 검증 질문 리스트, anti_signal 본문, ACT_* 액션 카탈로그.

⚠️ Step A를 *함수 이름·trigger_when만 보고 통과*하면 그 시점에 실패. 검증 질문 추출이 강제.

---

### Step B — 검증 질문에 *데이터로* 답 (mvp 자산 동원)

각 verification_question을 하나씩 던지고 답을 찾는다.

#### 답 찾는 우선순위 (반드시 1번부터)

**1. `news_alert.db` 1차 sweep (절대 1순위)** — mvp의 핵심 자산. 빼면 시드 카드 *작성 환경*을 못 잡는다.

```python
import sqlite3
db = r"C:\Users\fivep\OneDrive\Desktop\mvp\research_Mvp\news_alert.db"
con = sqlite3.connect(db)
cur = con.cursor()
# 키워드 sweep
for kw in ['핵심키워드1', '핵심키워드2', ...]:
    cur.execute("""SELECT date(s.fetched_at), s.source, s.title, substr(coalesce(s.summary,''),1,200)
                   FROM seen_news s
                   WHERE (s.title LIKE ? OR s.summary LIKE ?)
                   AND date(s.fetched_at) >= date('now','-14 day')
                   ORDER BY s.fetched_at DESC LIMIT 5""", (f'%{kw}%', f'%{kw}%'))
# 본문 추출 (헤드라인만으로 의미 못 잡는 경우)
cur.execute("""SELECT s.title, s.source, date(s.fetched_at), substr(c.body,1,2000)
               FROM seen_news s LEFT JOIN article_contents c ON s.url_hash=c.url_hash
               WHERE s.url_hash = ?""", (target_hash,))
```

- 14일 기본 윈도우, 분석가 카드의 *작성 시점 전후 환경* 까지 잡기.
- 헤드라인만 보면 노이즈. **본문 1,500~2,000자 직접 읽기** 강제.
- 시드 카드가 가정한 *전제*가 진행 중인 환경인지 확인 (예: T5에서 "호르무즈 재개" 가정 → 봉쇄가 이미 3/4부터 진행 중이었음).

**2. R6 data_sources 따라가기** — Step A에서 추출한 `DS_*` 카탈로그 순서대로:
- `DS_DART_OPENAPI`: 단일판매·공급계약, 분기실적, 임원 매매 → `module_disclosure <code>`
- `DS_MVP_MODULE_VALUATION`: peer 비교, valuation snapshot → `module_valuation <code>`
- `DS_MVP_SCENARIO_DB`: 시나리오 매핑 → `module_scenario_scan <ticker>`
- `DS_MVP_NEWS_ALERT_DB`: 위 1번 sweep
- `DS_WEBSEARCH_*`: 정책 진척, 글로벌 비교 (한 메시지 6~8건 통합 호출, 검증 결과 4분류 — 강화/부분/부정/공백)

**3. 정량 anchor 직접 인용**: `[news_alert.db|source|YYYY-MM-DD]`, `[DART|단일판매계약|YYYY-MM-DD]`, `[WebSearch|소스명]` 라벨 강제.

#### 산출 형식

| Q번호 | 검증 질문 | 데이터 답 | source label | 정보 공백 |
|---|---|---|---|---|
| F87 Q1 | 전가 가능 vs 못한 차이? | 한전: 소매 락 0% / 발전사: SMP 자동 연동 / 가스공사: 도매 정치 통제 (미수금 13.4조) | [news_alert.db\|sedaily\|2026-05-13] | LNG IPP 상장 종목 매핑 |

---

### Step C — anti_signal 충족 여부 *데이터로* 판정

각 함수의 anti_signal 본문을 가져와서 **데이터로 발화 여부 결론**.

| 상태 | 조건 | 액션 |
|---|---|---|
| **미충족** | 데이터로 anti_signal 조건이 발화 안 함 | 함수 발화 유효, thesis hold |
| **부분 충족** | 일부 조건 발화 | 모니터링 trigger setup, thesis warn 격상 |
| **완전 충족** | 모든 조건 발화 | 함수 무력 결론, thesis downgrade |
| **새 무력화 조건 발견** | anti_signal 본문에 없는 조건이 데이터에서 발견 | **ACT_FUNCTION_REDESIGN_CANDIDATE 등록 (Step D-6)** |

⚠️ "가능성이 있다" 같은 가설형 판정 금지. 데이터로 발화 여부 결론. 데이터 없으면 정보 공백으로 분류.

**T3 사례 새 무력화 조건**: F87 anti_signal은 "전가력 차이가 작거나 충격 단기 소멸"만 다룸. 그러나 데이터 확인 결과 **"전가 가능 *상장* 베타 부재"** 라는 3번째 조건이 한국 utility 도메인에서 발화 — 이건 v4 F87 spec에 없음. spec 보강 후보 등록.

---

### Step D — action_at_trigger *실제* 발동

함수의 `action_at_trigger`에 박힌 ACT_* 액션을 *제안*이 아니라 *실행*한다. 각 레벨별로:

#### D-1. ACT_WATCHLIST_ADD (watch_level)
**무엇**: 종목 코드 + 분류 + 추적 사유.

```
| 종목 | 코드 | 분류 | 추적 사유 |
|---|---|---|---|
| 한국전력 | 015760 | 역방향 anchor | 패자 추적 |
| 두산에너빌리티 | 034020 | 진짜 베타 | F87 OEM 위치 |
| 한국가스공사 | 036460 | 비교 대조 | 일회성 증익 추적 |
```

#### D-2. ACT_MONITORING_SIGNAL_TIMESERIES (watch_level)
**무엇**: 변수 4~6개 + 선행/동행/후행 분류 + 갱신 빈도.

```
1. 월간 SMP (KPX) — 후행 (lag 4~6M)
2. 두바이유 일간 — 선행
3. 한전 회사채 발행 한도 — 분기 갱신, 정치 신호
4. 한전 분기 OP vs 컨센 — 분기, 발전사 분리 검증
```

#### D-3. ACT_NEWS_DEEP_FETCH (warn_level)
**무엇**: 키워드 alert 등록 — anti_signal trigger watch.

```
키워드: "SMP 상한", "계통한계가격 상한", "산업통상자원부 SMP"
알림 주체: 정부 보도자료, 국회 에너지위, 산업부 차관 발언
발화 트리거: 1건 hit → ACT_T2_PROMOTION_FLAG (thesis warn 격상)
```

`news_alert.db`에 키워드 등록 권장 (운영 자동화).

#### D-4. ACT_PEER_BASELINE_SNAPSHOT (warn_level)
**무엇**: 분기 baseline 박제.

```
1Q26 baseline:
- 한전 OP 3.8조 (컨센 4.2조 -10%)
- 가스공사 OP 9,100억 (+9.1%, 일회성 포함)
- 두산에너빌 OP <보강 필요>
→ 2Q26·3Q26 발표 시 baseline 대비 변화 측정
```

#### D-5. ACT_CROSS_REF_R4_CARDS (cross_ref)
**무엇**: 다른 thesis·다른 시드 카드와 연결.

```
T2 (배터리 안보) ↔ T3 (SMP): 안보 자금이 ESS·LNG·전력기기 어디로 가나
T5 (호르무즈) ↔ T3: 호르무즈 장기화 → SMP 상한제 부활 압력 (직렬 연결)
```

#### D-6. ACT_FUNCTION_REDESIGN_CANDIDATE (backtest)
**무엇**: F* spec 한계 발견 시 보강 후보 등록 — **라이브러리 진화 큐**.

```
F87 anti_signal 추가 후보:
> "전가 가능 구조를 가진 *상장* 베타 종목이 부재해 시장 베팅이 불가능한 경우 
>  (예: 한국 IPP 시장 GS EPS·SK E&S 비상장 락) 함수가 *분석으로만* 작동하고 
>  *베팅 액션*으로 옮길 수 없음. 이때 OEM/그릇 위치 종목으로 우회 매핑 필요."
```

위 후보를 별도 큐 파일에 누적 (예: `data/function_redesign_queue.jsonl`).

---

### Step E — 정보 공백 + 다음 액션

**채우지 못한 정량 5개 이상 명시** (정직 룰).

```
1. SMP/유가 회귀 계수 — 직접 데이터 없음. KPX·KEEI 호출 필요.
2. 두산에너빌리티 1Q26 OP segment 분해 — module_disclosure 미실시.
3. 한국지역난방공사 SMP 노출도 — news 0건.
4. SMP 상한제 정책 검토 신호 — news 30일 sweep 0건, 국회/산업부 미실시.
5. 비상장 IPP가 모회사(GS·SK·POSCO홀딩스)에 미치는 영향 — F87 우회 베타 미검토.
```

**다음 액션 후보**: 어떤 모듈/소스를 호출하면 위 5개 중 몇 개를 채울지 매핑.

---

### Step F — 메타 회고

**자가 평가**:

1. **인용 vs 수행 차이** — 이번 라운드에서 *인용에 그친 함수* 있나? 있다면 다음 라운드에 수행으로 격상.
2. **anti_signal 발견 — 함수 라이브러리 진화 후보** — Step C/D-6에서 등록한 후보 정리.
3. **시드 카드 한계 — 코퍼스 보강 후보** — 시드 카드가 *비워둔 종목/지역/시점*. PLAY31 카드 추가 합성 큐에 추가.
4. **다른 thesis 연결** — 단독 thesis로 끝내지 말고 cross-ref 그래프 1줄.

---

## 3. 산출 파일 구조

저장 위치: `<context>/thesis_<TID>_execution.md`

권장: PLAY32_r5_merge_v4/samples/ 또는 mvp/llm_outputs/<DATE>/<thesis_name>/

각 Step을 섹션으로 1:1 매핑. 표·리스트 적극 활용. 함수 ID와 데이터 출처 라벨 강제.

---

## 4. 절대 원칙

### 4.1 인용 금지 룰
함수 이름·trigger_when만 인용하고 verification_questions 안 던지면 = **실패**. Step A unpack 강제.

### 4.2 데이터 우선 룰
- `news_alert.db` 1차 sweep 강제 (시드 카드 *작성 환경*을 놓치지 않기 위해)
- 본문 (`article_contents`) 직접 인용 — 헤드라인만으로 의미 못 잡음
- 정량 anchor `[source|date]` 라벨 강제

### 4.3 함수 라이브러리 진화 룰
- 모든 thesis 실행 후 **anti_signal 보강 후보 1건 이상** 등록
- F* spec 한계 발견은 *실패가 아니라 진화 신호*
- 메타 회고로 라이브러리 갱신 큐 누적

### 4.4 정직 룰
- 정보 공백 5개 이상 명시 (Step E)
- 시드 카드의 잘못된 전제 발견 시 *그 사실 자체*를 결과로 적기 (T5 호르무즈 사례)
- 컨센서스화 진행 신호 감지 시 stance 재평가 (같은 thesis 다른 매체 보도 다발)

### 4.5 함수 결합 룰
단일 함수 사용 금지. 2~5개 함수 결합 (T3 사례 F87+F75+F53). 결합이 단일보다 강함.

---

## 5. 안티패턴 (절대 하지 마라)

| # | 안티패턴 | 결과 |
|---|---|---|
| 1 | 함수 이름만 적고 verification_questions 통과 | 인용에 그침 |
| 2 | anti_signal을 "있다/없다" 가설로 처리 | 데이터 검증 부재 |
| 3 | action_at_trigger를 *제안*으로만 남기고 실제 발동 안 함 | R6 layer 사장 |
| 4 | 시드 카드 작성 환경(news 컨텍스트) 확인 안 함 | T5처럼 시드 전제 자체 잘못 가능 |
| 5 | 함수 한계 발견하고도 라이브러리 갱신 후보 등록 안 함 | 라이브러리 정체 |
| 6 | 정보 공백 안 적고 "검증 완료"처럼 마무리 | 정직 룰 위반 |
| 7 | 단일 함수만 인용 | 결합 사고 회피 |

---

## 6. 빠른 호출 체크리스트

```
입력 확정:
[ ] 시드 thesis 카드 1~3장 명시
[ ] 연관 R5 v4 함수 2~5개 ID 명시
[ ] 도메인·섹터 명시

Step A — 함수 unpack:
[ ] 함수별 verification_questions 모두 추출 (인용 X)
[ ] 함수별 anti_signal 본문 확보
[ ] 함수별 action_at_trigger 5 레벨 ACT_* 카탈로그
[ ] 함수별 data_sources + indicators + specific 추출

Step B — 데이터로 답:
[ ] news_alert.db 14일 sweep + 본문 인용 (1순위)
[ ] R6 data_sources 순서대로 모듈 호출
[ ] 정량 anchor source label 강제

Step C — anti_signal 판정:
[ ] 각 함수 anti_signal 데이터 발화 여부 결론
[ ] 새 무력화 조건 발견 시 D-6 큐 추가

Step D — 액션 실제 발동:
[ ] D-1 워치리스트 종목 분류 표
[ ] D-2 시계열 변수 4~6개 + 선행/동행/후행
[ ] D-3 키워드 alert 등록 (anti_signal watch)
[ ] D-4 1Q baseline 박제
[ ] D-5 다른 thesis cross-ref
[ ] D-6 F* spec 보강 후보 등록

Step E — 공백/다음:
[ ] 정보 공백 5+ 명시
[ ] 다음 모듈 호출 후보 매핑

Step F — 메타 회고:
[ ] 인용 vs 수행 자가 평가
[ ] 라이브러리 진화 후보 정리
[ ] 시드 코퍼스 보강 후보 등록
[ ] 다른 thesis 연결 한 줄
```

---

## 7. 효율화 — 반복 작업 최소화

### 7.1 모듈별 1회 호출 룰
- `news_alert.db`: thesis별 1회 sweep, 결과는 `samples/<thesis>/news_evidence.md`에 박제 → 다음 thesis가 같은 키워드 쓰면 재활용
- `module_disclosure`: 종목별 분기 1회, baseline 후 90일 재호출
- `module_scenario_scan`: thesis 시작 시 1회, scenario.db 갱신 주기 따라

### 7.2 워치리스트 누적 룰
- 새 thesis마다 ACT_WATCHLIST_ADD가 기존 워치리스트와 합쳐짐
- `data/watchlist_combined.md` 단일 파일로 통합, thesis 태그(`T3`, `T5`)로 추적

### 7.3 키워드 alert 누적 룰
- ACT_NEWS_DEEP_FETCH로 등록한 키워드를 `news_alert.db` keywords 테이블에 push (운영 자동화)
- 사용자가 텔레그램으로 받는 alert가 곧 thesis의 anti_signal trigger watch

### 7.4 함수 진화 큐 룰
- D-6에서 등록한 후보를 `data/function_redesign_queue.jsonl`에 append
- 분기 1회 큐 처리 → R5 v5 빌드

---

## 8. T3 모범 사례

[samples/power_infra_2026q2_thesis_T3_execution.md](../samples/power_infra_2026q2_thesis_T3_execution.md) 참조.

핵심 발견 4개:
1. **가스공사 1Q26 +9.1%는 일회성** (시드 카드 라벨링 오류 발견)
2. **F87 anti_signal에 3번째 무력화 조건** ("상장 베타 부재") 추가 후보
3. **진짜 베타는 두산에너빌리티** (OEM 위치, 시드 카드 빈자리)
4. **분기별 수혜자 회전** (5~7월 한전 패자만, 8~10월 발전사, 11월~ SMP 상한제 시 부호 뒤집힘)

→ 이 4개는 *인용*만 했다면 절대 못 잡았을 결과. *수행* 했기 때문에 나옴.

---

## 9. 한계

1. **R6 카탈로그 의존**: ACT_*/DS_*/IND_* 카탈로그가 v3 R5 기준. 새 도메인에서 카탈로그 부족 시 직접 작성 + 카탈로그 보강 큐 push.
2. **모듈 호출 미실시 가능**: `module_disclosure`·`module_valuation` 등은 mvp 별도 실행. 프롬프트는 *어디서 호출할지* 명시까지, 실제 실행은 워크플로우 별도.
3. **시드 카드 코퍼스 빈자리**: PLAY31 R4 카드가 *직접 종목*을 빠뜨린 경우 (T3 두산 사례) → Step F-3에서 코퍼스 보강 후보로 등록, 별도 합성 라운드 필요.

---

## 10. 변경 이력
- 2026-05-28 — 최초 작성. T3 SMP execution 사례(2026-05-27)를 일반화. PLAY32 R5 v4 통합 후 첫 *실행 프로토콜*.
