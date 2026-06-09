# PLAY40_osint_self_check

## 목적
본인 소유 이메일/닉네임이 인터넷 사이트·SNS에 어디에 노출/가입돼 있는지 OSINT 도구(holehe, maigret)로 점검하고 마크다운 보고서로 정리하는 자가 보안점검.

## 실행법
```powershell
# 1) 의존성 설치 (사전 1회) — 무거우니 코드 실행 경로 밖에서 미리 설치
python -m pip install --user holehe maigret

# 2) 이메일 가입 여부 검사 (holehe)
holehe fivepeople201@gmail.com --only-used
holehe fourpeople201@gmail.com --only-used

# 3) 닉네임 SNS 계정 탐색 (maigret) — 상위 500개 사이트, 수 분 소요
#    Windows 콘솔(cp949)에선 진행바 블록문자가 UnicodeEncodeError로 죽으니
#    아래처럼 utf-8 + --no-progressbar 필수.
$env:PYTHONIOENCODING="utf-8"; maigret fivepeople201 --html --no-progressbar
$env:PYTHONIOENCODING="utf-8"; maigret fourpeople201 --html --no-progressbar

# 4) 전체를 한 번에 돌리는 러너 (위 2~3을 순서대로 실행하고 로그를 results/에 저장)
#    holehe/maigret 콘솔 스크립트가 PATH에 없으면 run.sh가 PATH를 직접 잡아준다.
bash run.sh
```

생성된 원시 로그/리포트는 `results/`에 저장된다. 최종 정리는 `REPORT.md`.

## 입력 / 출력
- **입력:** 이메일 2개(fivepeople201@gmail.com, fourpeople201@gmail.com), 닉네임 추정값 2개(fivepeople201, fourpeople201)
- **출력:**
  - `results/holehe_*.txt` — holehe 콘솔 출력
  - `results/maigret_*` — maigret HTML/콘솔 리포트
  - `REPORT.md` — 사람이 읽는 최종 보고서(가입 확인 표 + SNS URL 목록 + 도구 한계 + 보안 대응 가이드)

## 가정 & 제약
- **닉네임은 사용자가 "이메일 앞부분으로 추정"을 선택**해서 `fivepeople201`, `fourpeople201`을 핸들로 간주하고 maigret을 돌렸다. 실제 SNS에서 쓰는 핸들이 다르면 오탐/누락이 생긴다. 실제 핸들이 확정되면 그 값으로 다시 돌릴 것.
- holehe/maigret은 **해외 서비스 위주**. 국내 서비스(카카오, 네이버, 토스, 당근 등)는 검사 범위 밖 — "검사 안 됨"이지 "가입 안 됨"이 아니다.
- **레이트리밋/타임아웃/네트워크 오류로 응답을 못 받은 사이트는 "가입 안 됨"이 아니라 "판단 불가"로 분류**한다. 보고서에서 별도 표기.
- holehe는 사이트별 API 동작 변화로 **오탐(false positive)·미탐(false negative)** 가능. maigret도 동명이인/유사 핸들을 잡을 수 있어 URL은 사용자가 직접 눈으로 확인 필요.
- maigret 전체 실행은 상위 500개 사이트를 돌아 **수 분** 걸린다. 디스패치(Bash ~45초)에선 잘릴 수 있어 백그라운드+폴링으로 실행. README "실행법"의 사전 설치도 같은 이유로 코드 경로 밖에 둠.
- **maigret은 DB 3,159개 중 상위 500개만 검사**했다(`--top-sites 500`). 전수 검사하려면 `--top-sites 3159` 또는 `-a`로 재실행(수십 분).
- **Windows cp949 인코딩 이슈:** maigret 진행바의 블록문자(▁█)가 cp949에서 `UnicodeEncodeError`로 죽는다 → 스캔은 끝나도 HTML/JSON 리포트가 안 써진다. `PYTHONIOENCODING=utf-8` + `--no-progressbar`로 해결(run.sh에 반영됨).
- holehe/maigret 콘솔 스크립트는 `%APPDATA%\Python\Python311\Scripts`에 설치되며 기본 PATH에 없다. run.sh가 PATH를 직접 추가한다. 수동 실행 시 PATH 추가 또는 전체 경로 사용 필요.
- 본인 소유 계정에 대한 자가 점검 용도. 타인 대상 사용 금지.

## 변경 이력
- 2026-06-06 — 최초 생성. holehe(이메일 2개) + maigret(닉네임 추정 2개) 실행, 결과 `REPORT.md`로 정리. cp949 인코딩 이슈로 maigret을 utf-8 + `--no-progressbar`로 재실행해 HTML/JSON 리포트 확보.
