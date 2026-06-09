# 발췌 → Residue 카드 추출 프롬프트

> 메인 Claude 또는 격리 subagent 컨텍스트에 **이 본문을 그대로** 준다.
> 외부 LLM API 금지 — 추출은 너(Claude/subagent)가 직접 한다.
> 메인이 `EXCERPT`(발췌 텍스트)와 `BOOK_META`(title/author/추정 type)를 채워서 준다.

---

## 목표 — recall이 아니라 deployment

이건 요약/플래시카드가 **아니다**. 목표는 책에서 얻은 **잔여물(residue)** — 사고 기본값을
바꾸는 reframe 하나 — 을 잡아, *실전에서 발현되도록* 만드는 것이다. 그래서 명제 더미가
아니라 **발동 조건(trigger)이 붙은 한 수**를 뽑는다.

## ⚠️ 가장 먼저: 책 종류 분기

`BOOK_META.type` 을 확정하라(애매하면 발췌를 읽고 판단). **이 분기에 따라 추출 방식이 갈린다.**

### A) idea-book (총균쇠·정의란 무엇인가·자유론 등 — 논증이 *압축 가능*)
공격적으로 추출. 풀세트:
- `trigger_when` **(필수, 비우면 안 됨)**: 이 reframe가 발동돼야 할 *실전 상황/단서*.
  "상대가 매몰비용을 들이밀면", "내 의견이 명백히 옳다고 느껴 상대를 닫고 싶을 때" 처럼
  **뉴스/대화/내 머릿속에서 실제로 감지 가능한 신호**로. 추상론 금지.
- `reframe` (필수): 그 순간 *사고 기본값을 바꾸는 한 줄*. 저자 요약이 아니라 무브.
- `why_it_matters`: 왜 참인지 + **왜 나에게** 중요한지. 사용자 자기 말로(generation effect).
- `evidence`: 책 **직접 인용**(발췌에 있는 것만).
- `verification_questions`: 진짜 이해했는지 자가점검 1~3개. (상대주의와 뭐가 다른가? 오용 함정은?)
- `anti_signal`: 이 reframe를 **오용/남용**하는 신호.

### B) novel (데미안·인간실격·싯다르타·변신 등 — 가치가 *경험*이라 압축 불가)
**명제 추출 금지. SRS 금지(범주 오류).** 대신:
- `trigger_when`: **비운다(`""`)**. 소설은 발동 조건으로 관리하지 않는다.
- `reframe`: "이 책이 *나에 대해* 뭘 깨닫게 했나 / 어떻게 움직였나" — **felt-shift 한 줄**.
  교훈·격언으로 박제하지 마라. 명치에 남은 불편함을 그대로.
- `why_it_matters`: 그 felt-shift가 나에게 왜 박혔는지.
- `evidence`: 장면·구절(발췌 기반).
- `verification_questions`: **0개 가능**(빈 배열). 소설은 자가검증 대상이 아니다.
- `anti_signal`: 이 felt-shift를 깔끔한 교훈으로 박제하려는 충동 = 오용 신호.
- `review`: **`null`** 로 둔다(add_card.py가 강제하지만 카드 JSON에도 명시 권장).

## 출력 — 카드 1장 스키마 (그대로)

```jsonc
{
  "card_id": "B003",                 // 생략하면 add_card.py가 자동 부여
  "book": {"title": "", "author": "", "type": "idea"},   // 또는 "novel"
  "trigger_when": "",                // idea 필수 / novel은 ""
  "reframe": "",
  "why_it_matters": "",
  "evidence": "",
  "verification_questions": [],      // idea 1~3 / novel 0~
  "anti_signal": "",
  "cross_links": [],                 // 지금은 빈 배열(C단계용)
  "review": null                     // idea면 생략(add_card가 채움) / novel은 null
}
```

## 절차

1. `EXCERPT`를 끝까지 읽는다. 큰 발췌면 offset/limit으로 분할.
2. type 확정.
3. **잔여물 1~2개**만 뽑는다. 발췌 전체를 카드화하지 마라 — 사고 기본값을 *진짜로* 바꾸는
   한 수만. 욕심내서 5장 만들지 말 것(저장은 쉽고 발현은 어렵다).
4. 위 스키마로 JSON 1장씩 합성.
5. 저장: 카드 JSON을 파일로 쓰고 `python scripts/add_card.py <file>` 또는
   stdin으로 흘려넣는다. (review 초기화/ID 부여는 add_card가 처리.)
6. `python scripts/audit_cards.py` 로 보일러플레이트/trigger 누락 검사.

## 하지 마라
- **trigger 없는 idea 카드** (발동 불가 = 쓸모 없음).
- 발췌에 없는 인용·사실 **창작**.
- novel을 명제로 압축하거나 SRS에 태우기.
- 동기부여 상투구("열심히 하면 된다")를 reframe에 박기.
- 한 발췌에서 카드 5장씩 양산(잔여물은 희소하다).
