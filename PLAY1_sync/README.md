# PLAY1_sync — PLAYGROUND MD → Google Drive 미러

## 목적
PLAYGROUND 트리의 모든 `*.md`를 Google Drive `PLAYGROUND/` 폴더에 그대로 미러 업로드. 외부(휴대폰/노트북)에서 Drive로 PLAY 진행 상황을 읽기 위함. 단방향 (local → Drive).

## 실행법

### 최초 셋업 (이 PC에서 한 번만)

1. **GCP에서 OAuth Desktop client 받기 → `credentials.json` 저장**
   - https://console.cloud.google.com/ → 프로젝트 선택/생성
   - APIs & Services → Library → "Google Drive API" → **Enable**
   - APIs & Services → OAuth consent screen → User Type **External**, Testing 모드, test user에 본인 Gmail 추가
   - Credentials → Create Credentials → **OAuth client ID** → Application type **Desktop app** → DOWNLOAD JSON
   - 받은 파일을 이 디렉토리에 `credentials.json`으로 저장
   - (이미 다른 OAuth client에서 받아둔 게 있으면 그걸 그대로 써도 됨 — drive.file scope는 client별로 격리)

2. **의존성 설치**
   ```powershell
   pip install -r requirements.txt
   ```

### 매번 (MD 변경 후)

```powershell
python -u sync_md.py
```
- 첫 실행에서 브라우저 OAuth 1회 → `token.json` 자동 저장.
- 변경된 MD만 업로드 (md5 비교). 처음엔 전부 올림.
- Drive에 `PLAYGROUND/` 폴더가 자동 생성되고, 그 안에 PLAY 디렉토리 트리 그대로 미러됨.

### 옵션

```powershell
python -u sync_md.py --dry-run    # 뭐 올릴지만 출력 (OAuth는 진행됨)
python -u sync_md.py --reset      # config.json 백업 후 초기화 (Drive 폴더는 그대로 재사용, 단 file_id 매핑은 잃음)
python -u sync_md.py auth         # token.json 삭제하고 재인증
```

## 입력 / 출력
- **입력:** `PLAYGROUND/**/*.md` (단 `__pycache__`, `.git`, `.venv`, `node_modules`, `.idea`, `.vscode`, `output` 디렉토리는 제외)
- **출력 (Drive):** `PLAYGROUND/<상대경로>/<파일명>.md` 구조 그대로
- **출력 (로컬):** `config.json` — `{ root_folder_id, folders: {rel_dir: id}, files: {rel_path: {file_id, md5}} }`. 다음 실행 때 변경분만 올리기 위한 메타.
- **콘솔:** `[push] / [skip] / [folder] / [retry]` 줄 단위 로그

## 가정 & 제약
- **drive.file scope.** 이 OAuth client가 만든 폴더/파일만 보임. 사용자가 Drive에서 수동으로 만든 동일 이름 폴더와 충돌 안 함. 반대로, 만약 Drive에서 `PLAYGROUND` 폴더를 *수동으로* 만들었다면 이 스크립트는 그걸 못 찾아서 별도의 `PLAYGROUND` 폴더를 새로 만든다 (이름 중복 가능). 항상 이 스크립트로만 만들 것.
- **파일 이름·디렉토리 변경 추적 안 됨.** 로컬에서 MD를 옮기거나 이름 바꾸면 Drive에 새 위치로 업로드되고 옛 파일은 Drive에 남는다 (수동 정리 필요). `--reset` 후 재업로드해도 마찬가지로 중복이 남을 수 있음.
- **삭제 동기화 없음.** 로컬에서 MD 지워도 Drive 파일은 남는다 (단방향 미러). 정리하려면 Drive에서 직접.
- **첫 OAuth는 브라우저 필요.** 디스패치(헤드리스) 환경에서 첫 인증 불가능. 사용자가 이 PC에서 직접 한 번 실행해 `token.json`을 만들어둬야 함. 이후 토큰은 자동 갱신.
- **`credentials.json`, `token.json`, `config.json`은 비밀.** 절대 커밋·공유 금지. 이 스크립트가 `*.md`만 업로드하므로 자기 자신의 PY/json은 Drive로 안 새어나가지만, git이나 다른 sync 도구로 새지 않게 주의.
- **MD 외 파일은 무시.** PLAY가 산출물(이미지, 데이터)을 같이 보여주고 싶으면 README에 인라인으로 박거나 별도의 sync 도구 사용.
- **큰 파일 가정 없음.** chunked/resumable 처리 안 들어 있음. MD니까 다 작다는 가정. 1MB 넘는 MD가 있으면 업로드는 되지만 시간 들 수 있음.

## 변경 이력
- 2026-05-07 — 기존 SQLite DB sync 코드(`sync_db.py`, `chunked_push.py`, diag bat들)를 PLAYGROUND MD 미러 코드(`sync_md.py`)로 리팩토링. drive.file scope·OAuth 흐름·`drive_client.py`는 그대로 재사용. config.json 스키마는 새로 정의 (root_folder_id + folders + files).
