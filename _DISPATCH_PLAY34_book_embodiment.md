# 디스패치 브리프 — PLAY34: 책 체화(embodiment) 시스템

> 이 파일을 새 Claude에게 그대로 주면 PLAY34를 만든다. 너는 이 대화 기억이 없는 fresh 상태라고 가정하고 썼다.
> 먼저 루트의 `CLAUDE.md`(PLAYGROUND 규칙)를 읽어라. 아래는 그 위에 얹는 PLAY34 전용 설계 지시다.

---

## 한 줄
책에서 얻은 **잔여물(residue)** — 사고 기본값을 바꾸는 reframe 하나 — 을 잡아두고, *실전에서 발현되도록* 훈련시키는 개인 도구.

## ⚠️ 왜 (design intent — 이거 안 읽으면 엉뚱한 걸 만든다)

사용자는 천천히 읽고 디테일을 빨리 잊는다. 그래서 목표는 **기억(recall)이 아니라 발현(deployment)**이다.

**이건 Anki/플래시카드/요약 클론이 절대 아니다.** 리서치 결론(transfer-appropriate processing): 기존 도구는 전부 *recall*을 최적화하는데 체화엔 *deployment*가 필요하다 — 꺼내는 연습이 아니라 *써먹는 연습*을 해야 그 순간에 발동한다. Anki는 이미 이해한 사실을 *유지*만 하고(이해를 만들지 못함), Readwise는 저자 말을 다시 보여줄 뿐(네 사고가 아님), Blinkist는 대신 씹어준다(네가 생성 안 함). **아무도 deployment + 적대 검증 + cross-book 연결을 안 한다. 거기가 빈틈이고 PLAY34가 노릴 자리다.**

그래서 핵심 세 가지:
1. 아이디어를 **`trigger → reframe` 쌍**으로 저장한다 (예: "상대가 매몰비용 들이밀면 → 기회비용으로 되받기"). 명제 더미가 아니라 *발동 조건이 붙은* 무브.
2. 복습은 **퀴즈가 아니라 "이런 상황이 왔다, 받아쳐봐"** 로 띄운다 (TAP). 카드를 *상황*으로 부활시킨다.
3. **사적 적대 테스트** — 사용자가 응답하면 회의론자(=너 Claude/subagent)가 그 설명을 공격해 약점 관절이 깨질 때까지 후벼판다. *남 앞이 아니라 혼자 있을 때* 무너져보는 것(Feynman / 설명깊이 착각 깨기). **이게 핵심 차별점이자, 사용자가 "남 앞에서 털리는" 공포를 없애는 장치다.** 미리 사적으로 털려봐서 실전에선 안 털린다.

**책 종류로 분기 (중요):**
- **idea-book** (총균쇠·정의란 무엇인가·자유론): 논증이 *압축 가능*하다. 공격적으로 추출 — trigger→reframe + self-explain + 적대 검증 풀세트.
- **novel** (데미안·인간실격·싯다르타·변신): 가치가 *경험*이라 압축 불가. **명제 추출 금지. SRS 금지(범주 오류).** 대신 "이 책이 *나에 대해* 뭘 깨닫게 했나 / 어떻게 움직였나" 감정 reframe 한 줄만 잡는다.

## 이번에 만들 척추 (A+B. C는 다음 회전)

- **A. Residue Cards** — 책/하이라이트/장 텍스트 → trigger→reframe 카드 추출(너+subagent가 직접, 외부 API 금지) → JSONL 저장 → 뷰어로 봄. + SM-2 복습 스케줄러(새로).
- **B. Sparring (deployment 루프, ⭐핵심)** — 만기 카드를 *상황*으로 띄움 → 사용자 응답 → 적대 검증 한 합(약점 관절 지적) → self-explain 갱신 → 다음 복습일 재계산.
- **C(나중)** — cross-book: 서로 다른 책 카드 2장 강제 연결/충돌(interleaving) + 에코챔버 감지("내 책들이 다 한 렌즈만 민다").

## 카드 스키마 (PLAY13 r5 패턴 차용, 자체 포함)
```jsonc
{
  "card_id": "B001",
  "book": {"title": "", "author": "", "type": "idea|novel"},
  "trigger_when": "이 reframe가 발동돼야 할 상황/단서 (deployment의 핵심. novel이면 비워도 됨)",
  "reframe": "사고 기본값을 바꾸는 한 줄 (idea) / 나에 대해 깨달은 felt-shift (novel)",
  "why_it_matters": "왜 참인지·왜 나에게 중요한지 — 사용자가 자기 말로 (generation effect)",
  "evidence": "책 직접 인용(idea) 또는 장면·구절(novel)",
  "verification_questions": ["진짜 이해했는지 자가점검 1~3개 (novel은 0개 가능)"],
  "anti_signal": "이 reframe를 오용/남용하는 신호",
  "cross_links": ["연결되는 다른 card_id (C단계용, 지금은 빈 배열)"],
  "review": {"due": "YYYY-MM-DD", "ease": 2.5, "interval_days": 1, "reps": 0}
}
```

## 재사용할 PLAYGROUND infra (패턴/스키마만 베껴 PLAY34 안에 자체 포함 — ⚠️ CLAUDE.md대로 PLAY 간 import 금지)
- **PLAY13_insight_distill** — `prompts/r4_reverse_distill.md`(원문 인용 → 사고 무브, 보일러플레이트 금지 anti-template) + `data/r5_thinking_functions.json` 스키마(`abstract_form`/`trigger_when`/`verification_questions`/`anti_signal`/`example`) = 거의 그대로 카드 포맷. + `scripts/r4_audit_templates.py`(카드가 뻔한 말인지 regex 감사).
- **PLAY33_yt_career_harvest** — `viewer/build_viewer.py`(카드 JSONL → 자체완결 HTML, file:// 더블클릭, 필터·검색·다크) = 카드 뷰어 그대로. `prompts/orchestrator.md`+`subagent_distill.md` = subagent 병렬 추출 엔진.
- **PLAY23_card_hitrate** — 카드↔CSV id 조인 채점 CLI = **복습/발현 로그**의 골격(가격 움직임 대신 "발현/회상 성공" 기록).
- **PLAY22_corpus_drift** — HHI/다양성 지표 = C단계 에코챔버 감지.
- **PLAY24_block_writer** — SQLite+REST+CLI 블록 스토어 = 쓰기 가능한 카드 DB + 브라우저 편집 원하면.
- 참고: 사용자가 예전에 "독서토론 프롬프트(recall·검증·연결)"를 만들었다는데 **이 repo엔 없다**(다른 데 있나봄). 있으면 좋지만 없다고 가정하고 진행.

## 새로 만들 것 (repo에 선례 없음)
- **SM-2(또는 Leitner) 복습 스케줄러** — stdlib만, 카드 `review` 필드 갱신.
- **캡처 플로우** — 우선 단순하게: 발췌 텍스트/하이라이트 붙여넣기 → 카드. (epub/pdf 파서는 나중. 무거운 의존성 실행경로 금지 — CLAUDE.md.)
- **적대 deployment 루프** — "LLM"은 외부 API가 아니라 **너(메인 Claude)+subagent가 직접** 회의론자 역할 (외부 API 금지 룰 자동 충족). 한 합이면 충분.

## 샘플 입력 동봉 (CLAUDE.md: 데이터 읽는 PLAY는 샘플 필수)
짧은 발췌 1~2개를 `samples/`에 넣어라 — 예: 밀 자유론 핵심 단락(idea), 카프카 변신 한 장면(novel). 그걸로 **카드 1~2장 생성 → 복습 1회(상황+적대 한 합) → 뷰어 표시**를 end-to-end로 데모할 것. 사용자가 검증 못 해도 README 안의 실행 예시로 굴러가야 한다.

## 완료 기준
1. 발췌 → 카드 → 복습 1회(상황 제시 + 적대 한 합) → 뷰어, 가 *한 흐름으로 실제로 굴러간다*.
2. idea/novel 분기가 코드에 있다.
3. README 작성: 목적·실행법·입출력·**가정&제약**(deployment>recall 철학, idea/novel 분기, 미구현 부분 명시)·변경이력.

## 하지 마라
- 플래시카드/Anki/요약 클론. **recall만 최적화하면 실패.**
- 소설을 SRS·명제추출. 외부 LLM API 호출. 다른 PLAY 디렉토리 import/수정.
- 무거운 의존성을 코드 실행경로에. README 없이 끝. trigger 없는(=발동조건 없는) 카드.
