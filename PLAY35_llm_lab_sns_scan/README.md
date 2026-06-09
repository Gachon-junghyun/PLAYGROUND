# PLAY35_llm_lab_sns_scan

## 목적
LLM 연구소(Anthropic·OpenAI·xAI·Google DeepMind·Meta·Mistral 등)의 **핵심 인물·공식 SNS 계정과 최근 발언**을, Claude Code 세션이 lab별 subagent를 띄워 웹서치로 조사하고 파이썬이 합쳐 리포트로 떨구는 실험.

## 실행법
이건 "파이썬 데몬"이 아니라 **Claude Code 세션에 말로 트리거하는 프로토콜**이다. anthropic SDK/API도, `claude -p` 서브프로세스도 안 쓴다 — 오케스트레이터가 이 세션 자체다.

```text
# Claude Code 세션에서 이렇게 말하면 발동:
"PLAY35 프로토콜로 LLM 엔지니어 SNS 조사 돌려줘"
"PLAY35 Anthropic, OpenAI만 소규모로 스캔해줘"
```
그러면 세션이 PROTOCOL.md를 읽고 → lab마다 Agent subagent 띄워 조사 → 결과 JSON을 `results/`에 저장 → 아래 파이썬으로 합친다.

파이썬 플러밍(표준 라이브러리만, Python 3.8+ / 설치 불필요):
```powershell
cd PLAY35_llm_lab_sns_scan
python scan.py labs        # lab 설정(JSON) 출력 — subagent 입력
python scan.py validate    # results/*.json 스키마 점검
python scan.py collect     # results/*.json -> report.md 렌더
```

## 입력 / 출력
- **입력:**
  - `labs.json` — 조사 대상 lab 목록(이름/slug/공식계정 힌트/찾을 인물 범주). 자유 편집.
  - subagent가 반환하는 lab별 조사 JSON (스키마는 PROTOCOL.md).
- **출력:**
  - `results/{slug}.json` — lab 한 개 조사 결과(오케스트레이터가 저장).
  - `report.md` — 전체 합본 리포트(파이썬이 렌더). lab별 공식계정/인물/최근 발언/출처.

## 가정 & 제약
- **오케스트레이션 주체는 Claude Code 세션이다.** `scan.py`만 단독으로 돌리면 조사는 안 되고 플러밍(labs/validate/collect)만 된다. 실제 조사는 세션이 PROTOCOL.md를 실행해야 채워진다. (의도된 분리 — "claude code에게 말하면 도는" 구조.)
- **SNS = 주로 X(트위터).** X는 로그인 월이라 직접 스크랩이 어렵다 → subagent는 **공개 웹서치·뉴스·집계 사이트**에서 모은다. 따라서 "최근 발언"은 라이브 트윗이 아니라 **secondhand이거나 시점이 어긋날 수 있음**. 핸들도 옛것/오기 가능 → 신뢰 전 직접 확인.
- **핸들 환각 금지를 프롬프트에 명시**했지만, 작은 lab/덜 알려진 인물은 subagent가 못 찾고 빠질 수 있다. 빠진 게 "계정 없음"을 뜻하진 않는다.
- **토큰 비용**: lab 1개 = subagent 1개 = 실제 웹서치 추론. 6개 전체면 그만큼 비용. "소규모"는 1~2개로 먼저 검증하라고 PROTOCOL에 박아둠.
- **시점성**: 결과는 스냅샷. `scanned_at` 날짜 기준이며 인물 이동/계정 변경은 반영 안 됨.
- **결정론 분리**: `scan.py`는 LLM을 안 부른다. 같은 `results/`면 항상 같은 `report.md`. 재현성 위해 의도적으로 그렇게 둠.
- **PLAY 독립 규칙 준수**: HAN_LAB의 browser_agent / core.ai.claude 등 외부 코드를 import하지 않는다. 이 PLAY는 자기완결.

## 변경 이력
- 2026-06-03 — 최초 생성. labs.json + scan.py(labs/validate/collect) + PROTOCOL.md. Claude Code 세션이 subagent로 조사하고 파이썬이 합치는 구조. (소규모 라이브 1회 검증은 같은 날 수행 — Anthropic/OpenAI.)
