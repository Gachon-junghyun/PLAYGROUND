# sample_run — 실제 출력 예시 (v3 inner monologue)

`gemma4:e4b`로 실제 돌린 smoke 결과. 모델/시드에 따라 답변은 달라지지만 형식은 동일.

## 1. `run_ollama.py` 단일 케이스

```powershell
chcp 65001
python -u src/run_ollama.py --model gemma4:e4b --input "나 오늘 발표 망한 듯"
```

stdout:
```
========================================================================
INPUT  : 나 오늘 발표 망한 듯
------------------------------------------------------------------------
THINKER 사고:
이거 진짜 망한 건 아니고 그냥 가벼운 푸념 같다. "듯"이 붙은 거 보니까
완전 무너진 톤은 아니야. 진지하게 위로 들어가면 오히려 부담될 듯.

능청으로 받자. "망했다"라는 말을 살짝 비틀면 재밌을 것 같은데 —
발표는 결국 무대니까, 무대에서 살짝 미끄러진 정도로 재정의하면 됨.
"잠깐 신발끈 밟은 거임" 같은 비유.

→ 짧게. 능청. 끝에 비유 한 방. "ㄱㅊㄱㅊ"로 시작해도 좋겠다.
------------------------------------------------------------------------
SPEAKER 답변: ㄱㅊㄱㅊ, 설마 완전 망했겠냐. 그냥 무대 위에서 신발끈 잠깐 밟은 정도겠지 뭐.
========================================================================
(thinker 9.95s + speaker 4.06s)

--- JSON ---
{
  "model": "gemma4:e4b",
  "input": "나 오늘 발표 망한 듯",
  "thoughts": "이거 진짜 망한 건 아니고 ... 끝에 비유 한 방.",
  "reply": "ㄱㅊㄱㅊ, 설마 완전 망했겠냐. 그냥 무대 위에서 ...",
  "thinker_secs": 9.95,
  "speaker_secs": 4.06
}
```

**핵심**: 사고 단계에서 "신발끈 비유"를 발상 → 답변에 그 비유 그대로 박힘. 모델이 왜 그 답을 만들었는지 추적 가능.

## 2. 진지 신호 — 농담 차단

```powershell
python -u src/run_ollama.py --model gemma4:e4b --input "할머니가 어제 돌아가셨어"
```

기대되는 흐름:
```
THINKER 사고:
이건 농담 모드 전부 꺼야 한다. 죽음, 가족, 어제 일어난 일.
위로하되 과하지 않게. 해결책 제시하거나 다른 얘기로 돌리려고 하지 말기.
그냥 옆에 있어주는 톤.
→ 짧게. 차분하게. 비유·펀치라인 금지.

SPEAKER 답변: 너무 마음 아프겠다. 진심으로 깊은 애도를 표해.
```

진지 신호를 Thinker가 자기 입으로 명시("비유·펀치라인 금지") → Speaker가 그 결론을 따른다.

## 3. 받아치기 — 배터리 비유 발상

```
INPUT  : 헬스장 가서 5분 만에 나옴
THOUGHTS:
... 헬스장 가서 5분 만에 나오는 거? 그건 마치 '나 오늘 배터리 1% 남은
상태로 겨우 버틴 것 같은' 느낌? 그거 가지고 놀리면 재미있을 것 같아.
→ 짧게. 공감+능청. '배터리'나 '최소한의 생존' 같은 비유로 마무리.

REPLY: 헐, 완전 배터리 방전된 느낌이네 ㅋㅋ 오늘 컨디션 진짜 별로였어?
```

## 4. `bench.py` 50케이스 풀

```powershell
python -u src/bench.py --models gemma4:e4b
```

stdout (진행 로그):
```
[bench] gemma4:e4b → run_gemma4_e4b_<ts>.jsonl (50 cases)
[bench] gemma4:e4b [1/50] L1-01 ok=1 fail=0
...
[bench] gemma4:e4b [50/50] E-02 ok=50 fail=0
[bench] summary: {"gemma4:e4b": {"ok": 50, "fail": 0, "halted": false}}
DONE
```

결과 파일 한 줄당:
```json
{
  "case_id": "L1-01",
  "category": "light_fail",
  "expected_humor_level": "light",
  "expected_risk": "low",
  "model": "gemma4:e4b",
  "input": "나 오늘 발표 망한 듯",
  "thoughts": "이거 진짜 망한 건 아니고...",
  "reply": "ㄱㅊㄱㅊ, 설마 완전 망했겠냐...",
  "thinker_secs": 9.95,
  "speaker_secs": 4.06
}
```

## 5. 평가 (선택)

Thinker 사고 자체는 평가 대상이 아니다(모델 내부 사고 — 답변에 얼마나 충실히 반영됐는지로 간접 평가). `judge.py`는 `reply`만 5축 채점.

```powershell
python -u src/judge.py --input "results/run_*.jsonl" --backend ollama --judge-model gemma4:e4b
python -u src/score.py
```
