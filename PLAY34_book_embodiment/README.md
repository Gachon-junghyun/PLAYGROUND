# PLAY34_book_embodiment

## 목적
책에서 얻은 **잔여물(residue)** — 사고 기본값을 바꾸는 reframe 하나 — 을 `trigger → reframe`
카드로 잡아두고, *실전에서 발현(deployment)되도록* 적대 검증으로 훈련시키는 개인 도구.
**recall(기억) 도구가 아니라 deployment(발현) 도구다.**

## 왜 이렇게 만들었나 (이거 모르면 Anki 클론으로 오해한다)
사용자는 천천히 읽고 디테일을 빨리 잊는다. 목표는 *외워서 꺼내기*가 아니라 *그 순간에
써먹기*다(transfer-appropriate processing). 그래서:
1. 아이디어를 **명제가 아니라 `trigger→reframe` 한 수**로 저장한다.
2. 복습을 퀴즈가 아니라 **"이런 상황이 왔다, 받아쳐봐"**(TAP)로 띄운다.
3. 응답하면 **회의론자(Claude)가 한 합 후벼판다** — 남 앞이 아니라 혼자 미리 털려본다
   (Feynman / 설명깊이 착각 깨기). 이게 핵심 차별점.

기존 도구(Anki=유지만, Readwise=저자 말 재노출, Blinkist=대신 씹어줌)는 아무도
deployment+적대검증을 안 한다. 거기가 이 PLAY가 노리는 빈틈.

## 실행법
```powershell
# 의존성: 없음. Python 3.9+ 표준 라이브러리만. (3.11에서 검증)

cd PLAY34_book_embodiment

# 1) 오늘 발현 훈련할(만기) 카드 보기  — novel은 여기 안 뜬다(SRS 외)
python scripts/review.py due

# 2) 카드를 '상황'으로 띄우기 (정답 reframe은 숨김 → 직접 생성해야 함)
python scripts/review.py present B001

#   → 네 응답을 적고, prompts/sparring.md 를 Claude에게 줘서 '적대 한 합'을 받는다.
#     (LLM = 외부 API 아님. 메인 Claude/subagent가 직접 회의론자 역할.)

# 3) 발현 결과 채점 → SM-2가 다음 복습일 재계산 + log/review_log.jsonl 기록
python scripts/review.py grade B001 4 --note "이번에 깨진 관절 한 줄"

# 4) 모든 카드 뷰어로 보기 (더블클릭으로 열리는 자체완결 HTML)
python viewer/build_viewer.py
#   → viewer/cards.html 을 브라우저에서 연다.

# 새 카드 추가(캡처): 발췌를 prompts/extract_cards.md 로 카드 JSON 합성 후
python scripts/add_card.py path\to\new_card.json

# 카드 품질 감사(trigger 누락·보일러플레이트·범주오류 검출)
python scripts/audit_cards.py
```

### 발췌→카드→복습 한 흐름 데모 (동봉 샘플로 실제 굴러감)
- `samples/mill_on_liberty.txt`(idea) → 카드 **B001**.
- `samples/kafka_metamorphosis.txt`(novel) → 카드 **B002**.
- 이 둘이 이미 `data/cards.jsonl`에 들어 있다. `review.py due` → `present B001` →
  (적대 한 합) → `grade B001 <0-5>` → `build_viewer.py` 까지 그대로 돌아간다.

## 입력 / 출력
- **입력:**
  - 발췌 텍스트(`samples/*.txt` 또는 사용자가 붙여넣는 하이라이트).
  - 카드 추출/적대검증은 `prompts/extract_cards.md` · `prompts/sparring.md`를 Claude에 전달.
  - CLI 인자: `due|present|grade`, `add_card <json>`.
- **출력:**
  - `data/cards.jsonl` — 카드 저장소(append/갱신).
  - `log/review_log.jsonl` — 발현/복습 기록(append-only). 비어 있으면 아직 채점 0회.
  - `viewer/cards.html` — 자체완결 카드 뷰어(재생성됨).

### 카드 스키마
```jsonc
{
  "card_id": "B001",
  "book": {"title": "", "author": "", "type": "idea|novel"},
  "trigger_when": "발동 상황/단서 (idea 필수, novel은 \"\")",
  "reframe": "사고 기본값 바꾸는 한 줄(idea) / 나에 대한 felt-shift(novel)",
  "why_it_matters": "왜 참인지·왜 나에게 중요한지 (사용자 자기 말)",
  "evidence": "책 직접 인용(idea) 또는 장면(novel)",
  "verification_questions": ["자가점검 1~3 (novel은 0개 가능)"],
  "anti_signal": "이 reframe를 오용/남용하는 신호",
  "cross_links": [],                       // C단계용, 지금은 빈 배열
  "review": {"due":"YYYY-MM-DD","ease":2.5,"interval_days":1,"reps":0}  // novel은 null
}
```

## 가정 & 제약
- **철학: deployment > recall.** 복습은 상황 제시(TAP)이고, '정답 reframe'은 `present`에서
  일부러 숨긴다 — 사용자가 직접 생성해야 발현 훈련이 된다. 단순 회상 퀴즈로 바꾸지 말 것.
- **idea / novel 분기는 코드에 박혀 있다:**
  - idea = SRS에 태움(`review` 채워짐). trigger_when **필수**(없으면 `add_card`/`audit`가 거부).
  - novel = `review: null`로 SRS **영구 제외**(`srs.is_due`/`review.py`/`audit`가 강제).
    소설을 간격반복·명제추출에 태우는 건 범주 오류라 막아놨다. novel은 felt-shift를 다시
    '느끼는' 용도로 뷰어에서만 본다.
- **"LLM"은 외부 API가 아니다.** 카드 추출과 적대 검증은 메인 Claude(또는 subagent)가
  프롬프트(`prompts/*.md`)로 직접 수행한다. API 키·시크릿 없음, 네트워크 호출 없음.
- **SM-2 변형:** quality 0~2 = 발현 실패(간격 리셋, 내일 다시), 3~5 = 성공(간격 확장).
  `deployed` 플래그는 quality≥3 기준. 표준 SM-2 ease 공식, 하한 1.3.
- **적대 검증은 코드가 아니라 모델이 한다.** `review.py`는 상황 제시·채점·기록(plumbing)만
  하고, '한 합' 자체는 사람+Claude의 대화다. 자동화 안 했음(그게 핵심이라 자동화하면 죽는다).
- **검증 범위:** Windows PowerShell·Python 3.11에서 `due/present/grade/add_card/audit/
  build_viewer` 전부 실행 확인. 콘솔 cp949 크래시 방지로 stdout을 UTF-8로 강제(`reconfigure`).
- **미구현 (의도적 — 다음 회전):**
  - **C단계 cross-book** — 서로 다른 책 카드 강제 연결/충돌(interleaving) + 에코챔버 감지.
    `cross_links` 필드만 자리 잡아뒀고 로직은 없음.
  - **epub/pdf 파서** — 지금은 발췌 텍스트 붙여넣기만. 무거운 의존성 실행경로 금지(CLAUDE.md).
  - 카드 추출의 *완전 자동화* — 의도적으로 모델 판단에 맡김(잔여물은 룰로 못 뽑는다).
- **확장성:** `cards.jsonl`을 통째로 읽고 다시 쓴다. 카드 수백 장까진 무방, 수만 장이면 비효율.

## 변경 이력
- 2026-05-31 — 최초 생성. A(Residue 카드+SM-2 스케줄러)+B(적대 deployment 루프) 척추 구현.
  샘플 2개(Mill 자유론=idea, Kafka 변신=novel)로 발췌→카드→복습→뷰어 end-to-end 데모.
  idea/novel 분기를 srs/review/add_card/audit/viewer 전반에 강제. C단계(cross-book)는 미구현.
