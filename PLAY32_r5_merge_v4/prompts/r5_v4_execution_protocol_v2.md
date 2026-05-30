# R5 v4 사고 함수 실행 프로토콜 v2 — 반증 중심 개선판

작성: 2026-05-28
기반: [r5_v4_execution_protocol.md](r5_v4_execution_protocol.md) (v1)
개선 계기: physical_ai_2026q2 thesis 실행 회고 (2026-05-28). v1로 작성 후 사용자 피드백 — "말만 리포트, 가시성 제로, 영어 검색·미국 모듈 누락, 함수 5개 중 1개만 실제로 일함".
모범 사례: [samples/power_infra_2026q2_thesis_T3_execution.md](../samples/power_infra_2026q2_thesis_T3_execution.md)

---

## 0. v1 → v2 핵심 변경 (왜 바뀌었나)

v1은 "함수를 *수행*하라"는 정신은 맞았지만, 실전에서 4개 실패 모드가 나왔다. v2는 이 4개를 **게이트로 강제**한다.

| # | v1 실패 모드 | v2 게이트 |
|---|---|---|
| 1 | **함수를 발견 도구로 오용** — thesis·종목을 함수에서 짜내려다 4/5 함수가 인용에 그침 | **§1 게이트 A**: thesis·종목은 *데이터에서* 먼저 만든다. 함수는 그 뒤 *반증*에만 쓴다. |
| 2 | **"5개 결합" 룰이 인용을 늘림** — 결합 숫자 채우려 안 맞는 함수 끼워넣음 | **§1 게이트 B**: 함수 1~2개만. 그중 1개는 반드시 *반증/anti-thesis 함수* (F44류). |
| 3 | **수행 로그 = 리포트 착각** — Step A~F 로그가 사용자가 읽을 수 없는 산출물 | **§4 게이트 C**: 산출물 2개 분리 강제 — `report.md`(사용자 가독) + `*_execution.md`(분석가 로그). report부터 쓴다. |
| 4 | **글로벌 thesis인데 한국 풀만 봄** — 영어 뉴스·미국 모듈 0회, KB "현대차가 토요타 추월"을 한국 언론 인용으로만 뒷받침 | **§2 게이트 D**: 글로벌 player 있는 thesis면 WebSearch + module_*_us *필수*. 누락 시 thesis 미완성. |

**한 줄 정신**: *함수는 thesis를 만드는 렌즈가 아니라, 이미 만든 thesis를 깨는 망치다.*

---

## 1. 입력 게이트 (작업 시작 전 강제)

### 게이트 A — thesis는 데이터에서, 함수는 그 뒤에

작업 순서를 **역전**한다. v1은 함수 → 데이터였지만 v2는:

```
1. news_alert.db sweep (한국) + WebSearch (글로벌)  ← 먼저
2. 거친 thesis 1~2줄 + 후보 종목 5~8개를 *데이터에서* 도출
3. 그 thesis를 깨려고 함수를 고른다                  ← 나중
```

⚠️ 함수 ID부터 고르고 시작하면 v1 실패 재현. **데이터 sweep 없이 함수 선택 금지.**

### 게이트 B — 함수 1~2개, 그중 1개는 반증 함수

- **단일 함수 OK** (v1의 "결합 강제" 룰 폐기). 진짜 일하는 1개 > 인용 5개.
- 2개 쓸 거면 **반드시 1개는 anti-thesis/반증 함수**: F44(서사 vs 채택), F27(펀더 vs 가격 디버전스), F84(저밸류 ≠ 매수), F78(양방향 순효과 미정) 등.
- 나머지 1개는 *thesis 핵심 회로*. 단, 이것도 "방향 힌트"로 그칠 위험 — §3에서 verification_questions에 *데이터로 답 못 하면 그 함수는 버린다*.

**반증 함수가 ROI의 핵심**: physical_ai 회고에서 F44만 진짜 일했다. 이유 — "주가 올랐네"로 끝낼 걸 "거품 신호 아니야?"로 강제로 묻게 했기 때문. 반증 함수는 *인간이 까먹는 체크리스트* 역할.

### 게이트 입력 3슬롯 (v1 유지, 순서만 변경)

1. **도메인·섹터** (먼저 확정)
2. **데이터 sweep 후 도출한 거친 thesis 1~2줄 + 후보 종목** (게이트 A 산출)
3. **반증용 함수 1~2개** (게이트 B, thesis 도출 *후*)

> 시드 thesis 카드가 사용자 제공이면 그대로. 없으면 *자체 합성임을 산출물 상단에 박제* (v1 physical_ai에서 누락 → 시드 진정성 미검증).

---

## 2. 데이터 게이트 — 글로벌 thesis면 영어·미국 모듈 필수

### 게이트 D — 누락 시 thesis 미완성 처리

thesis에 **글로벌 player(NVIDIA·Tesla·빅테크·해외 OEM)가 등장하면** 다음 *모두* 실행:

```bash
# 1. 한국 풀 (v1 그대로 — 1순위 유지)
python scripts/search_news_alert.py --days 90 "키워드들"   # + 본문 1,500자+ 직접 인용

# 2. 글로벌 뉴스 — WebSearch 6~8건 통합 호출 (한 메시지)
#    필수 각도: 글로벌 대장 분기실적·가이던스 / 캐파·공급망 / TAM 추정 / 경쟁사 / 정책
WebSearch "{player} earnings 2026 guidance"
WebSearch "{도메인} TAM 2030 Goldman Morgan Stanley"
WebSearch "{핵심 병목} supply shortage 2026 capacity"

# 3. 미국 종목 정량 — module_*_us
python -m module_fundamentals_us NVDA    # PER/매출 YoY/컨센 상승여력
python -m module_fundamentals_us TER     # 비교 baseline은 2종 이상
python -m module_business_us <ticker>    # 사업 구조 (EDGAR)
python -m module_disclosure_us <ticker>  # SEC 공시
python -m module_macro_us                # 매크로 필요 시
```

**검증 결과 4분류** (v1 유지): 강화 / 부분 / 부정 / 정보 공백.

⚠️ KB가 "현대차가 토요타 시총 추월"이라 쓰면, *토요타·현대차 글로벌 정량을 직접* 확인. 한국 언론의 외신 *재인용*에 의존하면 게이트 D 위반.

### DART 정량 backbone (04 프로토콜 1순위 — v1에서 누락됨)

```bash
python -m module_disclosure <code1> <code2> ... --days 90
python -m module_valuation <code> --auto-peers 4
python -m module_embedding peers <code> --top 12   # 시드 빈자리 자동 발견
```

physical_ai v1은 이걸 0회 호출하고 news layer만 썼다 → "분석가 로그"는 됐지만 "리포트"는 안 됨. **종목 매핑 thesis면 DART·valuation 최소 1회 필수.**

---

## 3. 함수 수행 (v1 Step A~C 압축 — 반증에 집중)

### Step A — 함수 unpack (v1 유지)

선택한 1~2개 함수의 verification_questions / anti_signal / action_at_trigger / data_sources 추출.

```python
import json
with open('PLAY32_r5_merge_v4/data/r5_v4_thinking_functions.json','rb') as f:
    v4 = json.load(f)
for fn in v4['functions']:
    if fn['function_id'] in ('F44',):   # 1~2개만
        print(fn['verification_questions'], fn['anti_signal'], fn['action_at_trigger'])
```

### Step B — verification_questions에 데이터로 답 + **답 못 하면 버린다**

v1과 차이: 검증 질문에 *mvp 자산·WebSearch로 답이 안 나오면 그 함수는 인용에 그친 것*. 솔직히 표시하고 **그 함수를 thesis 본문에서 빼라** (정보 공백으로만 남김). 끝까지 끌고 가서 "5개 다 썼다" 분식 금지.

| Q | 데이터 답 | source label | 답 됨/공백 |
|---|---|---|---|
| F44 Q1 | (데이터) | [news_alert.db\|src\|date] / [WebSearch\|src] | 됨 |

**source label 강제**: `[news_alert.db|source|YYYY-MM-DD]`, `[DART|항목|date]`, `[WebSearch|매체]`, `[module_fundamentals_us|ticker]`.

### Step C — anti_signal 데이터 판정 (v1 유지, 이게 반증의 핵심)

각 함수 anti_signal이 데이터로 **발화하는지** 결론. "가능성 있다" 가설 금지.
- 미충족 → 함수 발화 유효 (thesis hold)
- 부분/완전 충족 → thesis warn/downgrade
- **새 무력화 조건 발견 → 함수 진화 큐 등록** (§5)

---

## 4. 산출 게이트 — 2개 파일 분리, report 먼저

### 게이트 C — report.md(가독) + execution.md(로그)

**작성 순서: report.md 먼저, execution.md 나중.** (v1은 로그만 써서 실패.)

#### `report.md` — 사용자가 읽고 액션하는 문서

필수 구조 (physical_ai v2에서 검증된 골격):

```
1. 한 줄 결론 (TL;DR) — 사이클 위치 + 진짜 베타 1개 + 반증 신호 + 단기 변동성
2. 사이클 캘린더 — "지금이 어디인가" 분기점 표 (날짜·누가·무엇·출처)
3. 글로벌 player 정량 표 — 시총·Fwd PER·매출 YoY·컨센 상승여력 (module_*_us)
4. 핵심 병목 정량 — 왜 이 밸류체인인가 (캐파 갭 숫자)
5. 종목 매핑 — 카테고리별 (진짜 베타 / 분기 anchor / narrative / 반증 위험 / 시드 빈자리)
6. 자금 흐름 — ETF·IPO·수급 (컨센 형성 phase 신호)
7. 모니터링 시계열 — 변수 / 선행·동행·후행 / 다음 측정 시점
8. 베어 케이스 — 무엇이 깨면 thesis 약화 (측정 가능한 트리거)
9. 정보 공백 + 다음 액션 (모듈 호출 매핑)
10. 출처 (URL — 외신 anchor markdown 링크)
11. 한계 — 정직 진단 (못 한 호출·자산 한계·시점 변동성)
```

**가독 원칙**:
- 표·이모지 카테고리(🎯⚠️📈⛔🕳️)로 *스캔 가능*하게.
- 매수/매도 권유 0건. "진짜 베타"·"narrative 베타"·"반증 위험" 같은 *분석 라벨*만.
- 함수 ID는 report 본문에 *최소* 노출 (예: "반증 신호" 정도). 함수 unpack 표는 execution.md로.

#### `*_execution.md` — 분석가 로그 (선택, R5 진화용)

Step A~C unpack·anti_signal 판정·함수 진화 큐. report.md의 *부록*. 사용자가 안 읽어도 됨.

저장 위치: `mvp/llm_outputs/<DATE>/<thesis>/report.md` + `.../thesis_<name>_execution.md`.

---

## 5. 함수 진화 큐 (v1 D-6 유지 — 라이브러리 개선 동력)

thesis 실행 중 함수 spec 한계 발견 시 `data/function_redesign_queue.jsonl` append:

```yaml
- function_id: F44
  origin_thesis: <thesis>_<date>
  proposed_anti_signal_addition: "<데이터로 발견한 새 무력화 조건>"
  evidence_anchor: ["[source|date]", ...]
```

physical_ai 라운드 등록 예시 2건:
- **F44**: "컨센 다발 상향 + 역방향 의견 + IPO 따따블·ETF 신규 *동시 출현* = 컨센 형성 phase 자체 시그널" (채택 지표 직접 측정 전이라도)
- **F71**: "상장 베타가 시드 코퍼스·news 풀에 catch 안 되면 함수가 분석으로만 작동, 베팅 액션 불가" (T3 F87 "상장 베타 부재"와 동일 골격)

---

## 6. 빠른 체크리스트 (v2)

```
입력 게이트:
[ ] 도메인 확정
[ ] news_alert.db + WebSearch sweep *먼저* → 거친 thesis 1~2줄 + 후보 종목 5~8개
[ ] 그 thesis 깨려고 함수 1~2개 선택 (1개는 반증 함수 F44류)

데이터 게이트 D:
[ ] 글로벌 player 있으면 WebSearch 6~8건 통합 + module_fundamentals_us 2종+
[ ] 종목 매핑 thesis면 module_disclosure/valuation/embedding 최소 1회
[ ] source label 전부 강제

함수 수행:
[ ] verification_questions 데이터로 답 — *답 못 하는 함수는 버린다* (분식 금지)
[ ] anti_signal 발화 여부 데이터로 결론
[ ] 새 무력화 조건 → 진화 큐

산출 게이트 C:
[ ] report.md *먼저* (11개 섹션, 가독·스캔 가능, 함수 ID 최소 노출)
[ ] execution.md 나중 (분석가 로그, 선택)
[ ] 시드 자체 합성이면 상단 박제
[ ] 매수/매도 권유 0건 / 정보 공백 명시 / 한계 정직
```

---

## 7. 안티패턴 (v2 추가분)

| # | 안티패턴 | 결과 |
|---|---|---|
| 1~7 | (v1 동일) | — |
| 8 | **함수부터 고르고 thesis를 짜냄** | 4/5 인용 그침 (physical_ai v1) |
| 9 | **결합 숫자 채우려 안 맞는 함수 끼움** | 날 무딘 리포트 |
| 10 | **수행 로그를 리포트로 제출** | "말만 리포트" — 사용자 못 읽음 |
| 11 | **글로벌 thesis인데 한국 풀만** | 외신 재인용 의존, 정량 약함 |
| 12 | **답 안 나오는 함수를 끝까지 끌고 가 "다 썼다" 분식** | 정직 룰 위반 |

---

## 8. 변경 이력
- 2026-05-28 — v2 최초. v1(반증 정신 OK, 실전 4 실패 모드) → 게이트 A(thesis 먼저·함수 나중)·B(1~2개·반증 함수 필수)·C(report/log 분리)·D(글로벌 영어·미국 모듈 필수) 강제. physical_ai_2026q2 회고 반영.
