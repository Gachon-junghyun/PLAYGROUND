# PLAY33 토론 카드 뷰어

## 목적
PLAY33가 추출한 **토론/말싸움 무브 카드(JSONL)**를 브라우저에서 필터·검색하며 보는 한 장짜리 앱.

## 실행법
```powershell
cd PLAY33_yt_career_harvest
python viewer/build_viewer.py      # 카드 JSONL → viewer/cards.html 한 장으로 구움
# 그다음 viewer/cards.html 더블클릭 (오프라인·서버 불필요)
```
카드가 바뀌면 `build_viewer.py`를 다시 실행하면 된다.

## 입력 / 출력
| | |
|---|---|
| 입력 | `../data_argue_en/cards/E_b[1-9].jsonl` (영어 토론 99장) + `../data_debate/cards/D_b[1-9].jsonl` (한국 설득 64장) + `../data_argue_en/cards/E_b[1-9].ko.jsonl` (영어 카드 한글 번역 사이드카, card_id로 병합) |
| 출력 | `viewer/cards.html` (카드 데이터가 JS 상수로 박힌 자체완결 HTML, 총 163장) |

## 기능
- **한/영 토글:** 영어 카드를 한글 번역(기본) ↔ 영어 원문 전환. 인용(evidence_quote)은 *진짜 발언*이라 양쪽 모드 다 영어 유지 + 한글 글로스(`↳`) 병기. KR 카드는 항상 한글.
- **필터:** 코퍼스(EN/KR) · 축(axis) · 채널 · 효과(won/neutral/lost)
- **검색:** 무브·근거·인용·counter·채널·축·ID·applies_to + **한글 번역 필드**까지 전체 텍스트
- **카드 표시:** 축 색칩 · 무브(헤드라인) · 화자(who) · 메커니즘 · 인용(evidence) · 🛡막는 법(counter) · 효과/적용/confidence · ▶원본(유튜브 링크)

## 가정 & 제약
1. **데이터를 HTML에 굽는 방식**(fetch 아님) — `file://`로 더블클릭해도 CORS 문제 없이 열리게. 대신 카드 변경 시 재빌드 필요.
2. **두 코퍼스 스키마가 조금 다름** — EN은 `who`/`effectiveness`, KR은 `applies_to`. 없는 필드는 카드에서 자동 생략.
3. stdlib만 사용(외부 의존 0). Python 3.x. 163장 기준 빌드 1초 미만.
4. 브라우저 기능 검증 완료(렌더·5개 필터·양 스키마). `backdrop-filter` 때문에 헤드리스 *스크린샷*만 안 찍혔을 뿐 실제 브라우저 표시는 정상.

## 변경 이력
- 2026-05-30 — 최초 생성. `build_viewer.py`가 E/D 카드 163장을 `cards.html`로 구움. 필터(코퍼스·축·채널·효과)+전체검색+카드 렌더(인용/막는법/원본링크). 다크테마·반응형 그리드.
- 2026-05-30 — 영어 카드 한글화. subagent 6개가 EN 99장의 move/how/counter를 번역 + 인용 1줄 글로스 → 사이드카 `E_b[1-9].ko.jsonl`(원본 불변). 빌드가 card_id로 병합, **한/영 토글** 버튼 추가(기본 한글, 인용은 항상 영문+글로스). card glob을 `[1-9]`로 좁혀 `.ko.jsonl`이 카드로 안 잡히게 수정.
