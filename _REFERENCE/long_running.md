# REFERENCE: 긴 작업은 background로

Bash는 디스패치에서 ~45초 제약. 그보다 오래 걸리는 작업이 꼭 필요하면 **이 패턴을 써라.**

## 핵심 구조

1. PY 스크립트를 진행 로그가 잘 나오게 작성한다 (아래 §스크립트 작성 규칙).
2. Bash 툴을 `run_in_background: true`로 호출해서 띄운다 — 즉시 리턴, 45초 제약 안 받음.
3. 끝났는지 폴링하거나, 출력 파일을 Read로 확인한다.

---

## 스크립트 작성 규칙 (PY)

- **stdout 버퍼링 끄기.** 둘 중 하나:
  - 실행할 때 `python -u xxx.py`
  - 또는 코드 안에서 `print(..., flush=True)` 일관되게 사용
  - 안 끄면 출력이 메모리에 고였다가 끝날 때 한 번에 나옴 → 진행 추적 불가능, 폴링도 못 함.
- **진행 라인을 명시적으로 찍기.** `[step 3/10] loss=0.42` 같은 한 줄짜리 상태 라인.
- **종료 표시(sentinel) 출력.** 정상 끝날 때 `DONE`, 실패면 `FAILED: <이유>` 같은 고정 문자열을 마지막 줄에 찍어라. 폴링 측이 이걸 보고 멈춘다.
- **stderr도 같이 흘리기.** 실행 명령에서 `2>&1`로 합쳐서 한 파일에 모은다.

최소 예시:
```python
# play.py
import sys, time
print("[start]", flush=True)
try:
    for i in range(1, 11):
        time.sleep(0.5)
        print(f"[step {i}/10]", flush=True)
    print("DONE", flush=True)
except Exception as e:
    print(f"FAILED: {e}", flush=True)
    sys.exit(1)
```

---

## 띄우는 법

Bash 툴 호출 시 `run_in_background: true`, command는:
```bash
python -u play.py > run.log 2>&1
```
- `> run.log 2>&1` — stdout/stderr를 한 파일로. 나중에 Read 가능.
- `python -u` — 코드에 `flush=True` 안 박았어도 보험.
- 즉시 리턴됨. 45초 카운터 안 돌아감.

---

## 끝났는지 확인하는 법

### A. "끝나면 한 번 알림" — 권장 패턴

이걸 다시 Bash 툴에 `run_in_background: true`로 띄운다:
```bash
until grep -qE "^(DONE|FAILED)" run.log; do sleep 1; done
```
조건 맞을 때 자동 종료 → 완료 알림 한 번 옴. 그때 Read로 `run.log` 확인.

> **중요:** sentinel을 `DONE`과 `FAILED` 둘 다 잡아야 한다. 성공만 보면 크래시 났을 때 폴링이 영원히 안 멈춤.

### B. 중간 상태 직접 보기

포그라운드 Bash(45초 안에 끝남)로:
```bash
tail -n 30 run.log
```

---

## 흔한 함정

- **flush 안 하고 띄움** → log 파일이 비어 있어서 폴링이 영영 안 멈춘다.
- **`FAILED`/sentinel 안 찍고 `sys.exit(1)`만** → 폴링 grep이 못 잡아서 그냥 멈춤. 무조건 sentinel 라인을 찍어라.
- **`2>&1` 빠뜨림** → 트레이스백이 다른 데로 가서 디버깅 불가.
- **상대경로 출력** → 작업 디렉토리 헷갈리면 파일을 못 찾는다. PLAY 디렉토리 기준 명확히 (가능하면 절대경로).
- **타임아웃 없는 sleep 루프** → 폴링 자체에 max wait 두지 않으면 죽은 프로세스 기다리며 시간 낭비. 의심되면 `tail -n 5 run.log`로 마지막 라인 시간이 멈췄는지 확인.

---

## 한계

- background 프로세스의 생존을 매번 보장할 수는 없음 — sentinel이 한참 안 찍히면 죽었다고 가정하라.
- 진짜 오래 걸리는 작업(수십 분~)은 디스패치 세션 자체 한계에 부딪힐 수 있다. 그런 작업은 PLAY 단위로 적합하지 않으며, README "가정 & 제약"에 "사용자가 미리 결과를 만들어둬야 함"이라고 명시하는 게 옳다.
- 줄 단위 실시간 푸시가 필요하면 Monitor 툴이 별도로 있다 (이 ref 범위 밖).
