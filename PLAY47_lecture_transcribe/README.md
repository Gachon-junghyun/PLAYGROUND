# PLAY47_lecture_transcribe

## 목적
로컬 강의 영상/오디오 폴더를 Whisper(faster-whisper)로 전사해 `<원본명>.txt` 로 떨궈주는 단일 스크립트. PLAY33의 전사 방식을 로컬 파일용으로 자체 포함(다운로드 단계 없음).

## 실행법
```powershell
# 사전 설치 (한 번만 — 무거우니 실행 경로 밖)
pip install faster-whisper
# ffmpeg 필요 (미디어 디코드). 없으면: winget install Gyan.FFmpeg
# GPU(CUDA) 전사를 쓰려면 그에 맞는 PyTorch/CUDA 환경이 이미 있어야 함.

cd PLAY47_lecture_transcribe

# 폴더 전체 전사 (기본: large-v3 / cuda / ko / 타임스탬프 ON)
python transcribe.py "C:\Users\fivep\OneDrive\Desktop\PLAYGROUND\디지털마케팅"

# 무거워서 길어지면 background + run.log 폴링 (디스패치/긴 입력 권장)
python -u transcribe.py "....\디지털마케팅" > run.log 2>&1
#   → run.log 의 DONE / FAILED 를 확인

# GPU 없을 때
python transcribe.py "....\디지털마케팅" --device cpu --compute-type int8 --model small

# 단건 / 본문만(타임스탬프 제거) / 강제 재전사
python transcribe.py "....\one_file.mp4"
python transcribe.py "....\folder" --no-timestamps
python transcribe.py "....\folder" --overwrite
```

## 입력 / 출력
- **입력:** 폴더 경로 또는 단일 파일 경로(첫 인자). 폴더면 그 안의 미디어 파일
  (`.mp4 .mkv .mov .avi .webm .ts .m4a .mp3 .wav .flac .ogg .aac`)을 이름순으로 전부.
- **출력:** 각 미디어 **옆에** `<원본명>.txt` (기본). `--outdir` 로 다른 폴더 지정 가능.
  - 줄 형식(기본): `[hh:mm:ss] 전사된 문장` — 강의 구간 찾기 쉽게 세그먼트 시작 시각 표기.
  - `--no-timestamps` 면 본문만.
  - 진행 로그는 stdout(`[work n/N]`, `... segs`, `[ok]`, 끝에 `DONE`).

## 가정 & 제약
1. **PLAY 독립.** PLAY33을 import 하지 않고 faster_whisper 래퍼를 자체 포함.
2. **기본값 = `large-v3` + `cuda` + `float16` + `--language ko`.** 대상이 한국어 강의라 ko 고정.
   영어/혼합이면 `--language ""`(자동감지) 또는 `--language en`. GPU 없으면 모델 로드에서
   `FAILED` 찍고 종료 → `--device cpu --compute-type int8 --model small` 로 내려라.
3. **이미 `.txt` 있으면 skip**(중단 후 재실행 = 이어받기). 다시 하려면 `--overwrite`.
   전사 중에는 `.txt.partial` 로 쓰다 완료 시 rename → 중간에 끊겨도 깨진 `.txt` 안 남김.
4. **무거운 작업이라 길어진다.** 실측(RTX 3080): 169분 분량 4편 ≈ 25~40분(모델 로드 ~30s 포함).
   디스패치 45초·Bash 10분 한도를 넘으니 **background + run.log 폴링** 필수.
5. **화자 분리 없음.** 한 줄에 누가 말했는지는 안 나옴(강의=단일 화자라 영향 적음).
   고유명사·영어 용어는 Whisper 음차 오타가 섞일 수 있음(예: 마케팅 전문용어).
6. **검증:** 임포트/문법/도움말은 확인. 실제 4편 전사는 GPU 백그라운드로 별도 실행
   (이 PLAY를 만든 회전에서 `디지털마케팅` 폴더 4편에 적용).

## 변경 이력
- 2026-06-15 — 최초 생성. 로컬 폴더/파일 → faster-whisper 전사 → `<원본명>.txt`(타임스탬프 포함).
  `디지털마케팅` 강의 4편(64.5/50.6/39/15.3분, ko/large-v3/cuda)에 적용.
