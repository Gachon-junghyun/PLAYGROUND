# PROTOCOL — LLM Lab SNS 스캔

> 이 파일은 **Claude Code 세션이 읽고 실행하는 절차서**다.
> 사용자가 "PLAY35 프로토콜로 조사 돌려줘" 류로 트리거하면, 이 세션(=오케스트레이터)이
> 아래 단계를 그대로 수행한다. 파이썬(`scan.py`)은 데이터 플러밍만, 조사는 subagent가 한다.

## 역할 분담
- **오케스트레이터 = Claude Code 세션(너).** lab 목록을 읽고, lab마다 subagent를 띄우고,
  결과 JSON을 `results/`에 쓰고, 마지막에 `scan.py collect`를 호출한다.
- **subagent = Agent 툴(general-purpose).** WebSearch/WebFetch로 한 lab의 SNS 계정과
  최근 발언을 조사해 **아래 스키마의 JSON만** 반환한다.
- **scan.py = 파이썬 플러밍.** subagent 결과를 읽어 합치고 `report.md`로 렌더. LLM 호출 없음.

## 실행 단계

### 0. lab 목록 로드
```
python scan.py labs
```
→ `labs.json`의 lab 배열(JSON)을 받는다. 사용자가 특정 lab만 지정하면 그걸로 필터.

### 1. lab마다 subagent 1개 띄우기 (병렬)
독립 작업이므로 **한 메시지에 Agent 호출을 여러 개** 넣어 동시에 굴린다.
각 subagent에 줄 프롬프트 템플릿:

```
너는 한 AI 연구소의 SNS 정황을 조사하는 리서처다.
대상 lab: "{lab}"  (공식계정 힌트: {official_hint})
찾을 인물 범주: {roles}

WebSearch / WebFetch 로 다음을 조사하라 (검색 8회 이내로 효율적으로):
1. 이 lab의 공식 SNS 계정(X 우선, 있으면 LinkedIn/Threads/Mastodon).
2. 핵심 인물들(창업자/CEO, 리서치 리드, 주목할 엔지니어·연구자)의 개인 SNS 계정.
3. 각 인물이 최근(가능하면 2025~2026) SNS에서 무엇을 말했는지 — 주제와 구체적 발언.

제약:
- X 등은 로그인 월이 있어 직접 스크랩이 어렵다. 공개 검색 결과·뉴스·집계 사이트에서 모아도 된다.
  단, 추측으로 핸들을 지어내지 마라. 못 찾으면 그 인물은 빼거나 accounts를 빈 배열로.
- 발언은 출처 URL을 같이 남겨라. 확인 안 되면 notable_posts에 넣지 마라.

반드시 아래 JSON "한 덩어리만" 반환(코드블록/설명 없이):
{
  "lab": "{lab}",
  "scanned_at": "YYYY-MM-DD",
  "official_accounts": [
    {"platform": "X", "handle": "@...", "url": "https://...", "verified": true}
  ],
  "people": [
    {
      "name": "...",
      "role": "CEO / Co-founder 등",
      "accounts": [{"platform": "X", "handle": "@...", "url": "https://...", "verified": true}],
      "recent_themes": ["주제1", "주제2"],
      "notable_posts": [
        {"summary": "무슨 발언을 했는지 1~2문장", "approx_date": "2026-05", "source_url": "https://..."}
      ]
    }
  ],
  "notes": "조사 한계/주의(예: X 직접 확인 불가, 일부 secondhand)",
  "sources": ["https://...", "https://..."]
}
```

### 2. 결과 저장
각 subagent가 반환한 JSON을 파싱해 `results/{slug}.json` 로 쓴다 (slug는 labs.json의 값).
JSON 파싱이 깨지면 해당 lab만 재시도하거나 스킵하고 로그를 남긴다.

### 3. 점검 + 렌더
```
python scan.py validate     # 스키마 점검 (필수 키/개수)
python scan.py collect      # results/*.json → report.md
```

### 4. 사용자에게 보고
`report.md` 경로와 핵심 요약(찾은 공식계정 수, 인물 수, 눈에 띄는 발언 몇 개)을 전달.

## 스코프 조절
- "소규모 라이브"면 lab 1~2개만(예: Anthropic, OpenAI) 먼저 돌려 동작/출력을 확인.
- 전체를 돌릴 땐 6개 lab subagent 병렬. 토큰 비용이 lab 수에 선형으로 든다는 걸 사용자에게 고지.
