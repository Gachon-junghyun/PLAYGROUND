# OSINT 디지털 발자국 자가점검 보고서

- **점검일:** 2026-06-06
- **대상(본인 소유):** 이메일 `fivepeople201@gmail.com`, `fourpeople201@gmail.com` / 닉네임(추정) `fivepeople201`, `fourpeople201`
- **도구:** holehe 1.61 (이메일→사이트 가입여부), maigret 0.x (닉네임→SNS 계정 탐색, 사이트 DB 3,159개 중 상위 500개 검사)
- **용도:** 본인 계정 자가 보안점검 전용

> ⚠️ **먼저 읽을 것:** 닉네임은 사용자가 *"이메일 앞부분으로 추정"* 을 선택해 `fivepeople201`/`fourpeople201`을 핸들로 가정하고 돌린 결과다. **실제 SNS에서 쓰는 핸들이 다르면 아래 SNS 결과는 오탐(남의 계정)·누락이 섞일 수 있다.** URL은 반드시 직접 열어 본인 것인지 확인하라.

---

## 1. 이메일 가입 확인 (holehe) — "가입 확인됨"

holehe는 비밀번호 재설정/가입 API 응답으로 **해당 이메일이 그 사이트에 등록돼 있는지**를 판별한다. 각 이메일당 121개 사이트 검사, 레이트리밋(`[x]`)으로 판단 불가한 사이트는 **0건**이었다.

| 이메일 | 가입 확인된 사이트 | 의미 |
|---|---|---|
| `fivepeople201@gmail.com` | **firefox.com** (Mozilla 계정) | Firefox/Mozilla 동기화 계정 존재 |
| | **office365.com** (Microsoft) | Microsoft/Office365 계정 존재 |
| | **twitter.com** (X) | Twitter/X 계정 존재 |
| `fourpeople201@gmail.com` | **office365.com** (Microsoft) | Microsoft/Office365 계정 존재 |

- 위 표에 **없는** 116개 사이트는 holehe 기준 "가입 안 됨" 또는 holehe가 더 이상 정확히 판별 못 하는(모듈 노후화) 사이트다. holehe는 사이트 API 변화로 **미탐(있는데 못 잡음)이 흔하다** — "없음"을 100% 신뢰하지 말 것.

---

## 2. SNS 계정 탐색 (maigret) — 발견된 계정 URL

상위 500개 사이트 검사. maigret 자체 집계로 `fivepeople201` = **5개 계정**, `fourpeople201` = **4개 계정** 매칭.

### 2-1. `fivepeople201`
| 신뢰도 | 서비스 | URL | 비고 |
|---|---|---|---|
| 확인필요 | Instagram | https://www.instagram.com/fivepeople201/ | |
| 확인필요 | Threads | (없음) | |
| 확인필요 | HuggingFace | https://huggingface.co/fivepeople201 | |
| 확인필요 | TradingView | https://www.tradingview.com/u/fivepeople201 | |
| 확인필요 | Velog | https://velog.io/@fivepeople201/posts | 국내 개발 블로그 |
| **저신뢰(오탐의심)** | OnlyFans | https://onlyfans.com/fivepeople201 | OnlyFans는 임의 핸들에도 200 응답 → **오탐 가능성 높음**, 직접 확인 |
| **비계정(무시)** | Google Scholar | scholar.google.com/...q=fivepeople201 | 프로필이 아니라 **검색쿼리 URL**. maigret이 계정으로 안 셈. 무시 |

### 2-2. `fourpeople201`
| 신뢰도 | 서비스 | URL | 비고 |
|---|---|---|---|
| 확인필요 | Instagram | https://www.instagram.com/fourpeople201/ | |
| 확인필요 | Threads | https://www.threads.net/@fourpeople201 | |
| 확인필요 | HuggingFace | https://huggingface.co/fourpeople201 | |
| **저신뢰(오탐의심)** | OnlyFans | https://onlyfans.com/fourpeople201 | 위와 동일, 오탐 가능성 높음 |

> 두 핸들 모두에서 Instagram·HuggingFace·OnlyFans가 똑같이 잡혔다. 본인이 양쪽 다 만든 게 아니라면 **공통 매칭은 오탐 신호**일 수 있다. 특히 OnlyFans는 maigret에서 흔한 false positive다.

---

## 3. 판단 불가 (레이트리밋·접근거부)

> 주의사항대로 응답을 못 받은 사이트는 "가입 안 됨"이 아니라 **"판단 불가"** 로 분류한다.

- **maigret:** 두 핸들 모두 `Too many errors of type "Access denied" (13.0%)` 경고 발생. 즉 검사한 500개 중 **약 13%(≈65개 사이트)가 접근 거부/차단으로 판단 불가**. 이 사이트들에 계정이 있을 수도, 없을 수도 있다 — 결과에 안 나왔다고 "없음"이 아니다. (재시도 1회 후에도 8~9개 사이트는 끝내 실패.)
- **holehe:** 레이트리밋(`[x]`) **0건**. 단 holehe는 노후 모듈이 많아 차단이 아니라 **조용히 미탐**하는 경우가 있다(에러로도 안 잡힘).

---

## 4. 도구의 한계 (반드시 감안)

1. **오탐(false positive):** maigret은 "그 핸들 페이지가 200을 반환"하면 매칭으로 본다. 동명이인·플레이스홀더 페이지·임의 핸들 200응답(OnlyFans 등)을 본인 계정으로 잘못 잡는다. → URL 직접 확인 필수.
2. **미탐(false negative):** holehe는 사이트 API가 바뀌면 가입돼 있어도 못 잡는다. 결과에 없다고 안전한 게 아니다.
3. **검사 범위 제한:** maigret은 DB 3,159개 중 **상위 500개만** 검사했다(속도/안정성 위해). 나머지 2,659개는 아예 안 봤다. 전수 검사하려면 `--top-sites 3159` 또는 `-a`로 재실행(수십 분 소요).
4. **판단 불가 ≠ 없음:** 위 3절의 접근거부/레이트리밋 사이트는 결론을 못 내린 것이다.
5. **핸들 가정의 한계:** 실제 사용 핸들이 이메일 앞부분과 다르면 이 SNS 섹션 전체가 빗나간다.

---

## 5. 국내 서비스는 검사 범위 밖

holehe·maigret은 **해외 서비스 위주**다. 아래 국내 서비스는 **이 도구들이 검사하지 않았다 → "가입 안 됨"이 아니라 "검사 안 됨"**:

- 카카오(카카오톡/카카오계정), 네이버(블로그/카페/메일), 토스, 당근마켓, 쿠팡, 배달의민족, 11번가, 다음, 티스토리 등 대부분의 국내 플랫폼.
- 이쪽은 각 서비스의 **계정 설정 → 로그인 기록/연결된 앱**에서 직접 확인해야 한다. (Velog 정도만 maigret DB에 포함돼 잡혔다.)

---

## 6. 보안 대응 가이드

### 6-1. 비밀번호 재사용 점검 — 최우선
- 위에서 **확인된 계정(Mozilla, Microsoft, Twitter/X, 그리고 본인 것으로 확인된 SNS)** 의 비밀번호가 **서로 같거나 비슷하면 즉시 다르게 변경**. 한 곳이 털리면 크리덴셜 스터핑으로 줄줄이 뚫린다.
- **비밀번호 관리자**(Bitwarden, 1Password, 브라우저 내장 등) 도입 → 사이트마다 무작위·고유 비밀번호.

### 6-2. 2FA(2단계 인증) 활성화
- 우선순위: **이메일 계정(Gmail) → Microsoft → Twitter/X → 나머지**. 이메일이 모든 계정의 재설정 통로라 가장 중요.
- SMS보다 **인증 앱(Authenticator/TOTP)** 또는 **패스키/보안키** 권장.

### 6-3. 유출 이력 확인 (haveibeenpwned)
- https://haveibeenpwned.com 에 두 이메일을 각각 넣어 **과거 데이터 유출에 포함됐는지** 확인.
  - `fivepeople201@gmail.com`
  - `fourpeople201@gmail.com`
- 유출 목록에 뜨면 → 해당 서비스 **비밀번호 즉시 변경 + 같은 비번 쓰던 다른 곳도 전부 변경**.
- 비밀번호 단위 점검은 https://haveibeenpwned.com/Passwords (입력값은 해시 일부만 전송됨).
- 상시 알림: HIBP의 **Notify me**에 이메일 등록해두면 향후 유출 시 통보받음.

### 6-4. 안 쓰는 계정 정리
- 위 결과 중 **더 이상 안 쓰는 계정은 탈퇴/삭제** (공격 표면 축소, 과거 유출 노출 감소).
  - 예: 본인 것이 맞는데 안 쓰는 HuggingFace/TradingView/Velog 등 → 삭제 또는 비공개 전환.
- **본인 게 아닌데 잡힌 핸들**(특히 OnlyFans 오탐의심)은 → 무시하되, 진짜 본인 핸들을 도용당했는지 한 번은 열어볼 것.
- 정리 시 순서: ① 유출 이력 있는 곳 → ② 안 쓰는 곳 → ③ 민감정보 들어간 곳.

### 6-5. 추가 점검(선택)
- 실제 자주 쓰는 SNS 핸들이 따로 있으면 그 핸들로 maigret 재실행:
  `maigret <진짜핸들> --top-sites 3159 --html --no-progressbar`
- Google 계정: https://myaccount.google.com/security 에서 **연결된 서드파티 앱**·**로그인된 기기** 점검.

---

## 부록: 원시 결과 파일
- `results/holehe_fivepeople201.txt`, `results/holehe_fourpeople201.txt`
- `results/maigret_fivepeople201.txt`, `results/maigret_fourpeople201.txt`
- `results/report_*_plain.html` (브라우저로 열어볼 수 있는 maigret 시각 리포트)
- `results/report_*_simple.json` (구조화 데이터)
