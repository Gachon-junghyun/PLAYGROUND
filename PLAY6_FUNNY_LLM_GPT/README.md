# PLAY6_FUNNY_LLM_GPT

## 목적
유튜브 전사 텍스트를 한국어 마이크로스타일 LLM용 후보 데이터베이스로 변환한다.

## 실행법
```powershell
# Python 3.11 이상 권장. 기본 DB 생성은 외부 의존성 없음.
cd C:\Users\fivep\OneDrive\Desktop\PLAYGROUND\PLAY6_FUNNY_LLM_GPT
python build_microstyle_db.py

# 후보 조회
python query_db.py --limit 10
python query_db.py --type micro_reaction --limit 10
python query_db.py --search 센스 --limit 10

# 초벌 entry와 annotator batch 생성
python make_seed_entries.py
python batch_annotator_tasks.py --batch-size 25

# Ollama gemma4:e4b로 실제 annotator 실행 (기본 20개씩)
python ollama_annotate.py --model gemma4:e4b --limit 20
python inspect_ollama_entries.py --limit 5
```

Whisper 재전사나 유튜브 다운로드를 다시 할 때만 별도 의존성이 필요하다.

```powershell
pip install faster-whisper yt-dlp
python youtube_whisper\pipeline.py -r youtube_whisper\list.txt --language ko
```

## 입력 / 출력
- **입력:** `youtube_whisper/transcripts/**/*.txt` 전사 텍스트.
- **출력:**
  - `data/sources.jsonl`: 중복 제거된 원천 파일 목록.
  - `data/raw_chunks.jsonl`: annotator 모델에 넣기 좋은 전사 chunk.
  - `data/microstyle_candidates.jsonl`: 휴리스틱으로 뽑은 말맛 후보.
  - `data/annotator_tasks.jsonl`: LLM annotator에 바로 넣을 작업 단위.
  - `data/annotator_batches/*.json`: 작업 단위를 25개씩 묶은 batch 파일.
  - `data/seed_microstyle_entries.jsonl`: 휴리스틱 기반 초벌 microstyle entry.
  - `data/ollama_microstyle_entries.jsonl`: Ollama 모델이 생성한 실제 microstyle entry.
  - `data/ollama_rejects.jsonl`: 모델 출력 파싱 실패/호출 실패 로그.
  - `data/microstyle.db`: SQLite 검색용 DB.
  - `reports/summary.md`: 후보 분포와 상위 예시 리포트.
- **스키마:** `schema_microstyle_entry.json`
- **프롬프트:** `annotator_prompt.md`

## 가정 & 제약
- 이 PLAY는 `PLAY6_FUNNY_LLM_GPT` 안에 들어 있는 자료만 사용한다. 다른 PLAY 코드를 import하지 않는다.
- 기본 빌드는 LLM/API를 호출하지 않는다. 비용이 드는 annotator 단계 전, 로컬에서 후보를 정리하는 전처리용이다.
- `ollama_annotate.py`는 로컬 Ollama 서버(`http://localhost:11434`)와 `gemma4:e4b` 모델이 설치되어 있다고 가정한다.
- Ollama annotator는 task 1개당 모델 호출 1회다. 995개 전체 실행은 오래 걸릴 수 있으므로 `--limit`로 나눠 돌리는 것을 기본으로 한다.
- 자동 전사 텍스트에는 오탈자와 화자 분리 누락이 있다. `microstyle_candidates.jsonl`은 최종 학습 데이터가 아니라 annotator/사람 검수 전 후보 목록이다.
- 유튜브 전사 원문은 저작권 이슈가 있을 수 있으므로, 최종 학습 DB에는 긴 원문 복사보다 상황/기능/템플릿 추출물을 쓰는 것을 가정한다.
- `youtube_whisper` 파이프라인은 `faster-whisper`, `yt-dlp`, GPU/FFmpeg 환경에 의존할 수 있고 45초를 넘길 수 있다. 디스패치 기본 검증은 `build_microstyle_db.py`만 대상으로 한다.
- 현재 폴더명은 사용자가 만든 `PLAY6_FUNNY_LLM_GPT`를 유지했다. 루트 규칙의 snake_case와는 다르지만 기존 디렉토리를 임의로 변경하지 않았다.
- `seed_microstyle_entries.jsonl`의 rewrite 템플릿은 원문을 베끼지 않는 초벌 예시다. 품질 좋은 학습 데이터로 쓰려면 annotator 결과나 사람 검수가 필요하다.

## 변경 이력
- 2026-05-11 — Ollama `gemma4:e4b` annotator와 결과 조회 도구 추가.
- 2026-05-11 — 초벌 microstyle entry 생성기, annotator batch 생성기, JSON 스키마 추가.
- 2026-05-11 — 전사 텍스트를 chunk/candidate/task/SQLite DB로 변환하는 기본 파이프라인 추가.
