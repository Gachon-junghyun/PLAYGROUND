# PLAY37_problem_solving

## 목적
"문제해결능력 키우기"를 유튜브 수확으로 **추상 프레임**으로 뽑은 뒤, subagent 워크플로우로 **보드게임·전시발표·공부·일처리·놀러간자리·위기돌발·인간관계** 7개 현실 시나리오에 적용·현실검증해 **그 자리에서 바로 쓰는 구체 플레이북**으로 구체화하고 .docx로 굽는 연구.

## 실행법
2단계 파이프라인. 1단계 수확 산출물은 PLAY33 안에 격리(`data_problem_solving/`)되고, 2단계 구체화·문서화가 이 PLAY의 본체다.

```powershell
# ── 1단계: 유튜브 수확 (PLAY33 스크립트 운전, youtube-harvest 스킬) ──
#   결과: PLAY33_yt_career_harvest/data_problem_solving/ (전사 20편 + 카드 109장 + 리포트)
#   사전설치: pip install yt-dlp faster-whisper  (+ ffmpeg, CUDA GPU)
#   재현이 필요하면 PLAY33 README의 "문제해결능력 회전" 변경이력 참고.

# ── 2단계: 시나리오 스트레스테스트 워크플로우 (Claude Code Workflow) ──
#   scenario_stress_test.workflow.js — 7 시나리오 × (적용→현실검증) 2단계 = 14 subagent.
#   Claude Code에서 Workflow 툴로 scriptPath 지정해 실행.

# ── 3단계: .docx 빌드 ──
cd PLAY37_problem_solving/docs
node build_docx.js          # problem_solving_playbook.md → problem_solving_playbook.docx
#   의존성(이미 설치됨): npm install docx@9.5.1  (docs/node_modules)
```

## 입력 / 출력
- **입력:** 주제 문자열("문제해결능력 키우기"). 1단계가 유튜브에서 코퍼스를 자동 수집.
- **출력:**
  - `PLAY33.../data_problem_solving/reports/problem_solving_report.md` — 1단계 추상 프레임(6축·5회로·카드 109장 근거).
  - `PLAY37_problem_solving/scenario_findings.json` — 2단계 워크플로우 raw 결과(시나리오별 적용판정+플레이북).
  - `PLAY37_problem_solving/problem_solving_playbook.md` — **최종 구체화 가이드**(5회로 + 7시나리오 플레이북 + 치트시트).
  - `PLAY37_problem_solving/docs/problem_solving_playbook.docx` — Word 문서(포맷 보존, **로컬 전용**).
  - 드라이브: 폴더 `PLAY37_문제해결` 안 **Google Docs** `문제해결능력 현실 플레이북 (PLAY37)` (내용 동일, .docx 바이너리 업로드는 아래 한계 참조).

## 가정 & 제약
- **PLAY 독립 규칙 절충:** 1단계 수확은 PLAY33의 검증된 파이프라인을 재사용하는 게 합리적이라 산출물이 `PLAY33/data_problem_solving/`에 생긴다(코드 import가 아니라 데이터 재사용). PLAY37은 그 리포트를 **연구 입력**으로 읽어 2~3단계를 수행한다. docx 빌더(`docs/`)는 PLAY37 자체 `node_modules`(docx)로 자급 — PLAY33 것을 import하지 않음.
- **코퍼스 편향이 설계 동기:** 1단계 카드의 적용처 집계가 일처리·공부에 쏠리고 보드게임·놀러간자리엔 희박(applies_to 보드게임6·놀러간자리2). 2단계 워크플로우는 *바로 이 빈칸*을 현실 시나리오 subagent로 메우려는 것 — 그래서 "추상 프레임이 놀이·즉흥·사교에서도 살아남나"를 skeptic이 검증하고 안 먹히는 건 잘라낸다.
- **시나리오 7개는 사용자 예시(보드게임·전시·공부·일처리·놀러간자리)에 "등등 광범위하게"를 더해 위기돌발·인간관계 2개를 추가 해석.** 전시는 "내 결과물을 보여주고 질문에 답하는 자리"로 해석(관람보다 발표·응대 쪽).
- **워크플로우 산출은 LLM subagent 판단**이라 "현실에서 진짜 그렇게 하는지"는 경험적 검증이 아니라 추론이다. skeptic 단계가 교과서성을 거르지만, 플레이북은 *합리적 가설*로 받아들일 것.
- **윤리 경계:** 1단계 카드 중 김경일 X108·X113은 설득/조작 기법에 가까워 리포트·플레이북에서 "쓰는 법이 아니라 알아보는 법"으로 표시.
- Windows/PowerShell. node ≥ 18 (docx 빌드). 한글 폰트는 docx에서 Malgun Gothic 지정.

## 변경 이력
- 2026-06-04 — 최초 생성. 유튜브 수확(20편→카드109, PLAY33 `data_problem_solving/`)→추상 프레임 종합(`problem_solving_report.md`)→7시나리오 스트레스테스트 워크플로우(`scenario_stress_test.workflow.js`, 7×2 subagent)→구체 플레이북(`problem_solving_playbook.md`)→`.docx` 빌드(`docs/problem_solving_playbook.docx`, 22KB·표8·검증완료)→드라이브 업로드. **드라이브:** 폴더 `PLAY37_문제해결`(id `1ON_m-8QLRyzJo09Wjl57yYu8F5KvI7UR`)에 **Google Docs 문서로 업로드** (`문제해결능력 현실 플레이북 (PLAY37)`, id `1oxu5IPYbj2oFuFegBhXXO41cnn9A8OK6M1NuIL46tmQ`).
  - ⚠️ **`.docx` 바이너리 자체는 드라이브 미업로드.** create_file MCP는 base64를 인라인 인자로만 받는데, 22KB docx의 base64(29,368자)를 한 번의 어시스턴트 출력으로 내보내면 **출력 토큰 한도에 잘려 손상**된다(2회 시도 모두 "invalid base64"). malssaum(26KB)은 성공했으나 이 턴은 한도에 걸림. 그래서 드라이브엔 **같은 내용의 Google Docs**(텍스트라 무손상)를 올렸고, **포맷이 살아있는 Word 원본 `.docx`는 로컬에만** 존재. 정확한 .docx를 드라이브에 두려면 로컬 파일을 드래그&드롭하거나, docx를 ~6KB 이하로 줄여 재시도해야 함. Google Doc은 마크다운 표가 텍스트(│ 정렬)로 보이지만 내용은 전부 보존.
