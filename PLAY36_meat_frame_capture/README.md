# PLAY36_meat_frame_capture

## 목적
mp4 영상을 Whisper로 전사한 뒤, **나레이션이 '고기'를 설명하는 구간의 타임스탬프에서 영상 프레임을 캡처**해 저장한다 — "그때 고기가 어떻게 생겼나"를 이미지로 모아본다.

## 실행법
```powershell
# 사전 설치 (한 번만 — 무거우니 코드 실행 경로 밖)
pip install faster-whisper yt-dlp
# ffmpeg 필요 (프레임 추출). 없으면: winget install Gyan.FFmpeg
# GPU(CUDA) 전사를 쓰려면 그에 맞는 PyTorch/CUDA 환경이 이미 있어야 함.

cd PLAY36_meat_frame_capture

# (A) 로컬 mp4
python capture_meat.py --video "C:\path\to\meat.mp4"

# (B) URL에서 다운로드부터 (영상 스트림 포함 mp4를 받음)
python capture_meat.py --url "https://youtu.be/xxxx"

# GPU 없을 때
python capture_meat.py --video meat.mp4 --device cpu --compute-type int8 --model small

# 옵션 튜닝
python capture_meat.py --video meat.mp4 `
    --keywords "고기,삼겹살,마이야르,단면" `   # 캡처 트리거 키워드 교체
    --min-gap 8 `                              # 비슷한 프레임 폭증 방지(초)
    --pad 1.5 `                                # 캡처 시점 보정(+초, 설명 직후 화면)
    --out out_test

# 긴 영상은 background 권장 (디스패치 45초 초과 방지)
python -u capture_meat.py --video meat.mp4 > run.log 2>&1   # run_in_background
#   그 뒤 run.log 의 DONE / FAILED 폴링
```

## 입력 / 출력
- **입력:** `--video` 로컬 mp4 **또는** `--url` (yt-dlp 다운로드). 옵션: `--model/--device/--compute-type/--lang/--keywords/--min-gap/--pad/--max-frames`.
- **출력:** `out_<이름>/` 폴더
  - `frames/NNN_<mmss>_<자막슬러그>.jpg` — 캡처된 고기 프레임
  - `index.md` — 타임스탬프 + 자막 + 이미지가 함께 보이는 사람용 인덱스
  - `captures.jsonl` — `{t, start, end, text, matched, frame}` 한 줄당 캡처
  - `transcript_timed.txt` — 전체 전사 (`[mm:ss] 자막`)
  - `source.mp4` — (`--url` 사용 시) 다운로드된 원본

## 가정 & 제약
1. **"고기 이미지 추측" = 키워드 트리거 캡처로 해석.** 자막에 고기 관련 키워드가 들어간 구간의 **세그먼트 중간 시점**에서 프레임을 뽑는다. 발화자가 고기를 설명할 때 보통 그 고기를 비춘다는 전제. AI 비전으로 "프레임에 고기가 실제로 있는지" 확인하는 단계는 **없음** — 필요하면 후속 PLAY로 분리.
2. **타임스탬프 정확도는 Whisper 세그먼트 단위**(문장 수준). 설명과 화면이 어긋나면 `--pad`로 시점을 보정하라(예: 설명 끝난 직후 클로즈업이면 `+1.5~3`).
3. **프레임은 세그먼트 중간 1장만.** 한 구간에서 여러 장을 원하면 키워드/`--min-gap`을 조절하거나 코드의 대표 시점 로직을 늘려야 함.
4. **`--min-gap`(기본 6초)** 로 인접 캡처를 솎아 비슷한 프레임 폭증을 막는다. 짧은 클립이면 줄이고, 긴 영상이면 키워라.
5. **`--url` 다운로드는 영상 스트림 포함 mp4**(bestvideo+bestaudio merge). 오디오만 받으면 프레임을 못 뽑으므로 음성전용 포맷은 쓰지 않음.
6. **무거운 단계(Whisper)는 디스패치 45초를 넘을 수 있다.** 긴 영상은 README의 background 패턴으로. 짧은 영상(수 분)은 GPU로 보통 1분 이내. ⚠️ **실측 함정:** 4K·10분+ 영상은 (a) `--url` 다운로드가 수백 MB라 오래 걸리고(그래서 다운로드 화질을 1080p로 cap함) (b) 그래도 전사가 10분 background 한도를 넘을 수 있다. 긴 영상은 `ffmpeg -i in.mp4 -t 180 -c copy clip.mp4` 로 **앞부분만 잘라 테스트**하거나, foreground에서 넉넉한 timeout으로 돌려라. 다운로드된 원본이 4K면 전사가 느리니 필요시 `ffmpeg`로 720p 다운스케일 후 입력.
7. **PLAY 독립.** 다른 PLAY(예: PLAY33) 코드를 import 하지 않음. faster-whisper/yt-dlp/ffmpeg 호출을 이 파일 안에 자체 포함.
8. **기본 언어 ko.** 영어 영상은 `--lang en`(또는 빈값으로 자동감지).
9. **검증:** 문법/`--help` 파싱 확인됨. 실제 전사+프레임 추출 end-to-end는 GPU·네트워크가 필요. 짧은 샘플 mp4로 확인 권장.
10. **Windows(PowerShell) 기준.** 콘솔 한글 깨짐 방지로 stdout/stderr utf-8 재설정. 경로에 공백 있으면 따옴표로 감쌀 것.

## 변경 이력
- 2026-06-04 — 최초 생성. mp4(로컬/URL) → faster-whisper 타임스탬프 전사 → 고기 키워드 구간 탐지 → ffmpeg로 해당 시점 프레임 캡처 → `frames/` + `index.md` + `captures.jsonl` + `transcript_timed.txt`. 키워드 내장 기본셋, `--min-gap` dedup, `--pad` 시점 보정.
- 2026-06-04 — end-to-end 검증 완료. 고기남자 통삼겹(4K·11.7분) 앞 180초 클립으로 실행 → 8세그먼트 중 고기 설명 4구간 매칭 → 프레임 4/4 캡처 성공(`out_demo180/`, 자막-화면 일치 확인). 교훈 반영: ① 다운로드 화질 1080p cap(4K 479MiB 다운로드가 background 10분 한도 잠식) ② 긴 4K 전사가 한도 초과 → README에 "앞부분 잘라 테스트/720p 다운스케일" 함정 명시. `.gitignore`로 mp4 커밋 방지(원본은 무거움). 데모 산출물 `out_demo180/`(프레임 4장+index.md+전사)만 경량 보존.
