# PLAY24_block_writer

블럭(명제·가이드라인)을 우측 스크래치에 쌓아두고 캔버스로 끌어와 조립하듯 글을 쓰는 에디터.
프론트엔드는 단일 HTML, 백엔드는 Python stdlib만 쓰는 미니 서버 + SQLite.

## 구조
```
PLAY24_block_writer/
├── index.html      # 프론트엔드 (UI + 드래그/슬래시/Undo)
├── serve.py        # 로컬 HTTP 서버 (stdlib http.server, 외부 의존성 0)
├── db.py           # SQLite 레이어 (스키마, get/set/merge state, 검색)
├── manage.py       # CLI (Claude가 DB 직접 조작할 때 사용)
├── inbox.json      # 샘플 import 페이로드
├── blocks.db       # SQLite DB (서버 첫 실행 시 자동 생성, gitignored)
├── .gitignore
└── README.md
```

## 실행법
```powershell
cd PLAY24_block_writer
python serve.py
```
- 브라우저가 자동으로 `http://127.0.0.1:8765/` 를 엶
- 브라우저 안 열고 싶으면 `python serve.py --no-browser`
- 멈추려면 `Ctrl+C`

**의존성**: 없음. Python 3.8+의 표준 라이브러리(`http.server`, `sqlite3`, `json`)만 씀.

## 입력 / 출력
- **입력:** UI 직접 입력, JSON 파일 import(덧붙이기/전체 불러오기), 또는 `manage.py` CLI.
- **출력:**
  - 자동 저장: SQLite `blocks.db` 단일 파일.
  - 수동 백업: 상단 **"JSON 내보내기"** → `<제목>.json` 다운로드.
  - 또는 `python manage.py export --out backup.json`.

## 사용 흐름 (UI)
1. 우측 패널에서 **+ 명제** / **+ 가이드라인** 생성. 블럭은 기본 collapsed(제목 + 본문 1~2줄). **클릭/포커스하면 expanded**(편집 가능, 파란 보더).
2. **가이드라인 안에 명제를 끌어 놓으면** nesting (점선 구역에 드롭). 다시 스크래치 빈 영역으로 끌면 unnest.
3. 블럭을 캔버스로 드래그:
   - **명제** → 카드 1개 박힘
   - **가이드라인** → 섹션 헤더 + 자기 안의 모든 자식 명제 카드가 한 번에 박힘 (조립 핵심)
4. **캔버스 빈 곳을 클릭**하면 새 단락이 생기고 포커스됨 (docx/md 느낌). 마지막이 이미 빈 단락이면 그 단락에 포커스.
5. 캔버스 단락에 자유 텍스트 (Enter 새 단락, 빈 단락에서 Backspace 삭제).
6. **박힌 카드/섹션은 직접 클릭해서 인-플레이스 편집.** 카드 안의 제목/본문 모두 contenteditable. 카드를 고치든 섹션을 고치든 **스크래치의 원본 블럭은 안 바뀜** (fork 모델). 원본을 수정하려면 우측 스크래치에서 직접.
7. **드롭하자마자 그 뒤에 빈 단락이 생기고 거기로 커서가 감.** 가이드라인을 드롭 → 섹션 헤더 + 자식 카드들 + 새 단락 → 바로 글 이어 쓰기. 다음 항목이 이미 빈 단락이면 그걸 재활용.
8. **`+` 버튼**: 각 항목 좌측에 호버하면 `+` 와 `⋮⋮` 두 개. `+` 누르면 그 항목 바로 아래에 빈 단락이 생기고 포커스.
9. 박힌 카드 호버 → 우측 컨트롤로 **→ 텍스트** 토글 / 삭제.
10. 좌/우 패널 사이 **세로 라인을 드래그**해 너비 조정 (저장됨).
11. **"보기 모드"** 버튼: 카드 박스/태그/배경/핸들 다 제거 → 섹션은 **왼쪽 얇은 가이드 라인**으로만 구분되고 카드는 굵은 제목+본문 텍스트로 흐름. 편집 잠금. 다시 누르면 편집 모드.
12. **전체 선택 후 복사**: 캔버스에 포커스 둔 채 `Ctrl+A` → `Ctrl+C` (마크다운 풍). 또는 상단 **"전체 복사"** 버튼.
13. **여러 줄 붙여넣기**: 단락에 `Ctrl+V` → 줄바꿈마다 새 단락 (노션 스타일).
14. **doc 항목 재정렬**: 좌측 `⋮⋮` 핸들 드래그. 또는 편집 중 `Alt+↑/↓`.
15. **멀티 선택**: 핸들 클릭 / Shift+클릭(범위) / Ctrl+클릭(토글). 하단 플로팅 툴바로 일괄 삭제/이동/해제.
16. **슬래시 커맨드**: 빈 단락에서 `/` → 메뉴 (섹션 헤더 / 인용 / 구분선 / 스크래치 카드).
17. **Undo/Redo**: `Ctrl+Z` / `Ctrl+Y`. 최근 60단계.
18. **블럭 역할 칩**: 스크래치 블럭 옆 동그란 칩 (`주장/근거/반박/정의/사례/인용/함의/감성/질문/가설` 10종). 클릭으로 변경. 글의 *구조적 의도*를 강제하는 핵심 장치.
19. **출처/메모 필드**: 블럭 펼침(focus) 상태에서 `출처`(1차 출처·URL) + `메모`(자기 메타 인지, 캔버스엔 안 보임) 필드. 명제 블럭이 출처 비어있으면 우상단에 주황 점.
20. **진단 패널**: 우상단 📊 (또는 `Ctrl+/`) → 사이드 패널. 가이드라인·명제·역할 분포, 빈 가이드라인, 본문 글자수·예상 읽기 시간, **약점 진단**(주장 0개 / 근거 부족 / 반박 없음 / 출처 부족 / 감성 부족 등). 빨간 뱃지로 심각도 표시.
21. **장르 템플릿**: 새 글 생성 시 1·2·3 선택 → `분석 리포트`(시나리오 보고서 골격) / `오피니언 칼럼` / `개인 에세이`. 가이드라인 자동 박힘.
22. **전환 표현 라이브러리**: 단락에 포커스하면 우측에 `✏︎` 버튼 → 카테고리별(주장 도입 / 근거 제시 / 반박 인정 / 재반박 / 연결·심화 / 조건 명시 / 감성·임팩트 / 결론) 15개 변호사급 표현 → 클릭 한 번에 커서 위치 삽입.

### 단축키 요약
| 키 | 동작 |
| --- | --- |
| `Enter` (단락) | 새 단락 |
| `Backspace` (빈 단락) | 단락 삭제 |
| `Alt+↑/↓` (편집 중) | 현재 항목 이동 |
| `/` (단락 시작) | 슬래시 커맨드 |
| `Ctrl+A` (캔버스) | 캔버스 전체 선택 |
| `Ctrl+C` (전체 선택) | 마크다운 풍 복사 |
| `Ctrl+V` (단락) | 멀티라인 → 멀티 단락 |
| `Ctrl+Z` / `Ctrl+Y` | Undo / Redo |
| `Esc` | 슬래시 닫기 → 선택 해제 |
| `Delete` (비편집, 선택 있음) | 선택 일괄 삭제 |
| 캔버스 빈 곳 클릭 | 새 단락 |

## REST API (프론트엔드 ↔ 서버)
모든 state 엔드포인트는 `?doc=<id>` 파라미터로 대상 글을 지정. 미지정 시 current 문서.

| 메서드 + 경로 | 설명 |
| --- | --- |
| `GET /` | `index.html` 서빙 |
| `GET /api/documents` | 전체 글 목록 + `currentId` |
| `POST /api/documents` | 새 글 생성 (body: `{title}`) → `{id, title}` |
| `PUT /api/documents/:id` | 글 이름변경 (body: `{title}`) |
| `DELETE /api/documents/:id` | 글 삭제 (자식 블럭·캔버스 cascade 삭제) |
| `PUT /api/current` | 현재 글 설정 (body: `{id}`) |
| `GET /api/state[?doc=...]` | 한 글의 state JSON |
| `PUT /api/state[?doc=...]` | 한 글의 state 교체 (자동 저장이 호출) |
| `POST /api/import?mode=replace\|merge[&doc=...\|&new_doc=1]` | import — `new_doc=1`이면 새 글 생성해서 거기로 |
| `GET /api/export[?doc=...]` | state JSON 다운로드 (Content-Disposition) |

## Claude/사용자가 DB를 직접 다루는 법 — `manage.py`
서버 켜져 있든 꺼져 있든 동작. 모든 state 명령은 기본적으로 **current 문서**에 적용. 다른 글을 대상으로 하려면 `--doc <id>` 추가.

### 글(문서) 관리
```powershell
# 모든 글 목록 (* = current)
python manage.py list-docs

# 새 글 생성 (id 반환, --switch로 즉시 current 설정)
python manage.py add-doc --title "투자 리포트 2026Q2" --switch

# 이름 변경
python manage.py rename-doc <id> --title "새 이름"

# current 전환
python manage.py switch-doc <id>

# 글 삭제 (자식 블럭·캔버스 cascade)
python manage.py delete-doc <id> --yes
```

### 한 글의 state 다루기
```powershell
# 현재 글의 state JSON
python manage.py state
python manage.py state --doc <id>          # 다른 글 지정

# 백업
python manage.py export --out backup.json [--doc <id>]

# 전체 교체 (--new-doc 추가하면 JSON.title로 새 글 만들어 거기에 넣음)
python manage.py import backup.json [--doc <id>] [--new-doc]

# 덧붙이기 (ID remap, trailing 빈 단락 자동 제거)
python manage.py merge inbox.json [--doc <id>] [--new-doc]

# 검색 (--all 빼면 current 글만, --all 추가하면 모든 글)
python manage.py search "키워드" [--doc <id> | --all]

# 블럭 목록 (current 글의)
python manage.py list-blocks [--doc <id>]

# 가이드라인/명제 추가
python manage.py add-guideline    --title "1장" --body "도입부 설명" [--doc <id>]
python manage.py add-proposition  --title "핵심 주장" --body "근거" --parent <gid> [--doc <id>]

# 블럭 수정·삭제 (cross-doc — id로 직접 찾음)
python manage.py update-block <id> --title "..."
python manage.py delete-block <id>

# 한 글의 내용만 비우기 (글 자체는 유지)
python manage.py clear --yes [--doc <id>]
```

**워크플로**: 사용자가 "이 주제로 가이드라인 + 명제 만들어줘"라고 하면, Claude는
1. 적절한 JSON을 `inbox.json`에 작성하거나
2. `manage.py add-guideline`/`add-proposition`을 직접 호출

→ 사용자가 브라우저 새로고침하면 반영됨.

## JSON 스키마
```jsonc
{
  "title": "글 제목 (옵션)",
  "blocks": [
    { "id": "g1", "type": "guideline",   "title": "...", "body": "..." },
    { "id": "p1", "type": "proposition", "title": "...", "body": "...", "parentId": "g1" }
  ],
  "doc": [
    { "id": "d1", "kind": "para", "text": "자유 단락" },
    { "id": "d2", "kind": "section", "text": "서론", "blockId": "g1" },   // text 필수, blockId는 출처 추적용
    { "id": "d4", "kind": "card",
      "title": "핵심 주장", "body": "근거 한 줄",
      "blockType": "proposition", "blockId": "p1" },                       // title/body 직접 보유 (fork)
    { "id": "d5", "kind": "text", "text": "발췌", "source": "출처" },
    { "id": "d6", "kind": "divider" },
    { "id": "d7", "kind": "quote", "text": "인용문" }
  ]
}
```

### 규칙
- `parentId`는 **명제 블럭에만**, **같은 파일/DB 내의 guideline `id`**를 가리킴. 가이드라인 중첩 없음.
- `doc[].kind === "card"`는 **자기 `title`/`body`/`blockType`을 가짐** (fork 모델). `blockId`는 추적용 옵션 포인터. 캔버스에서 카드를 편집해도 스크래치 원본은 안 바뀜.
- `doc[].kind === "section"`은 자기 `text`를 가짐. `blockId`는 추적용 옵션 포인터.
- **머지 시 모든 incoming ID는 자동으로 새 ID로 재발급**되며 `parentId`/`blockId` 참조도 함께 remap. 같은 파일을 여러 번 머지해도 안전.
- 머지 시 기존 doc의 trailing 빈 단락은 자동 제거 후 새 doc 항목이 append.
- 빈 incoming title이고 현재 title도 비어 있으면 incoming title 채택.

샘플: [`inbox.json`](./inbox.json).

## localStorage → SQLite 마이그레이션
이전 버전(localStorage 전용)에서 쓰던 데이터가 있는 경우, 서버 켜고 처음 페이지 진입하면 자동으로 마이그레이션 prompt가 뜸. 확인하면 한 번에 옮기고 localStorage는 비움.

## 가정 & 제약
- **단일 문서.** 다중 문서 관리는 export/import + 별도 `blocks.db` 파일 교체로.
- **순수 텍스트.** 굵게/링크 등 인라인 서식 미지원.
- **가이드라인 중첩 없음.** 가이드라인 안에는 명제만.
- **블럭 삭제 정책:** 명제 삭제 시 캔버스 카드는 "(삭제된 블럭)" 표시. 가이드라인 삭제 시 자식 명제는 unnest되어 스크래치에 남음.
- **카드 ↔ 텍스트 토글은 비가역.** 텍스트→카드 변환은 새 명제 블럭을 만들어 붙임.
- **동시 편집 안전성:** 브라우저 + manage.py가 동시에 쓰면 last-write-wins. 브라우저는 `PUT /api/state`로 전체를 덮어쓰므로, 브라우저 열어두고 CLI로 수정하면 브라우저의 다음 저장에 덮일 수 있음. **권장: CLI로 쓸 땐 브라우저 새로고침 먼저, 마치고 새로고침.**
- **포트 8765 고정.** 충돌나면 `serve.py`의 `PORT` 상수 수정.
- **드래그는 마우스만.** 터치 미테스트.
- 디스패치 45초 제약: 빌드/의존성 없음 → 서버 시작/요청 모두 <1초.

## 변경 이력
- 2026-05-25 — 최초 생성. 단일 `index.html` + localStorage. 좌측 캔버스 + 우측 스크래치 + JSON import/export.
- 2026-05-25 — 가이드라인-명제 nesting. 머지 import(`덧붙이기`) 모드, ID 자동 remap. JSON 스키마 명문화 + `inbox.json` 샘플.
- 2026-05-25 — Splitter (드래그 너비 조정). `Ctrl+A` 전체 선택 + 마크다운 풍 복사. 단락 멀티라인 paste → 단락 분리.
- 2026-05-25 — Undo/Redo (60단계). `⋮⋮` 핸들 드래그 재정렬, `Alt+↑↓`. 멀티 선택 + 플로팅 툴바. 슬래시 커맨드 `/` (섹션/인용/구분선/스크래치 카드). doc kind 추가: `divider`, `quote`.
- 2026-05-25 — **백엔드 도입.** `serve.py` (stdlib http.server) + `db.py` (SQLite) + `manage.py` (CLI). 프론트엔드 저장 경로 localStorage → REST `/api/state`. 기존 localStorage 데이터는 진입 시 1회 마이그레이션 prompt. 스크래치 블럭 collapsed → focus 시 expanded(편집 모드 같은 시각 변화). 캔버스 빈 곳 클릭 시 새 단락. **보기 모드** 토글(편집 chrome 다 숨김).
- 2026-05-25 — **카드/섹션 fork 모델 + 인-플레이스 편집.** 캔버스에 박힌 카드와 섹션은 자기 `title`/`body`/`text`를 들고 있고 클릭하면 그 자리에서 contenteditable로 편집됨. 스크래치 원본 블럭과 분리(편집해도 원본 안 바뀜). 드롭 직후 빈 단락이 자동으로 뒤에 붙고 거기로 포커스 이동 → 바로 글 이어 쓰기. 항목 좌측 호버 시 `+` 버튼 추가 (이 항목 아래 새 단락). 카드 내부 키 단축: 제목→본문 Enter/Tab, 본문→제목 Shift+Tab, Ctrl+Enter로 카드 빠져나와 새 단락. DB 스키마: `doc_items.title/body/block_type/level` 컬럼 추가 (기존 DB 자동 마이그레이션). 프론트엔드는 기존 라이브 참조(card.blockId만 있던 형태)를 진입 시 1회 forked shape으로 자동 변환.
- 2026-05-25 — **글(문서) 단위 분리.** `documents` 테이블 추가, `blocks`/`doc_items`에 `document_id` 컬럼 + cascade FK. `meta.current_doc_id`로 마지막 본 글 추적. 기존 단일 DB는 자동으로 "글 1"로 묶여 마이그레이션됨. 툴바에 글 드롭다운(현재 글 표시 + 목록 + 이름변경/삭제/+ 새 글). 전환 시 보류 저장 플러시 후 새 글로 reload. import 시 "새 글로 가져올까?" 프롬프트로 안전한 분리 가능. REST: `/api/documents` CRUD + `/api/current` + 모든 state 엔드포인트 `?doc=` 지원. CLI: `list-docs`/`add-doc`/`rename-doc`/`switch-doc`/`delete-doc` + 모든 명령에 `--doc` 옵션.
- 2026-05-25 — **글쓰기 코칭 6종.** (1) **블럭 역할 칩** 10종(주장/근거/반박/정의/사례/인용/함의/감성/질문/가설). (2) **출처/메모 필드** — 명제는 출처 비면 주황 점. (3) **진단 패널**(`Ctrl+/`) — 역할 분포·약점 자동 진단(주장 vs 근거 비율, 반박 부재, 감성 부재 등)·심각도 뱃지. (4) **장르 템플릿 3종**(분석 리포트/오피니언/에세이) — 새 글 생성 시 prompt로 선택. (5) **전환 표현 라이브러리** 15개 — 단락 ✏︎ 버튼으로 클릭 삽입. (6) DB 스키마: `blocks.role/source/note` 컬럼 추가(기존 DB 자동 마이그레이션). CLI: 모든 add/update 명령에 `--role/--source/--note`.
