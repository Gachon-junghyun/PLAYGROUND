# PLAY40_gravitas

## 목적
"무시받지 않는 위엄·무게감"을 유튜브 수확으로 **추상 프레임**(위엄 6축·카드 133장)으로 뽑은 뒤, subagent 워크플로우로 **무시·무례 현실 상황 8개**(말 끊김·면전 조롱·상사 갑질·일 떠넘김·도발 시비·후려치기·친밀한 가벼이 여김·첫 자리 묻힘)에 적용·현실검증해 **"그 무시당하는 순간에 어떻게 행동하면 무게가 서는가"를 그 자리에서 바로 쓰는 구체 플레이북**으로 구체화하는 연구. **PLAY38_maturity(어른스러움)의 대칭편** — 38이 "내 감정 다스리기"라면 40은 "남이 나를 어떻게 대하게 만드나". PLAY37/38의 방법론을 그대로 차용.

## 실행법
1단계 수확 산출물은 PLAY33 안에 격리(`data_gravitas_ko/`·`data_gravitas_en/`)되고, 2단계 스트레스테스트·3단계 문서화가 이 PLAY의 본체다.

```powershell
# ── 1단계: 유튜브 수확 (PLAY33 스크립트 운전) — 이미 완료됨 ──
#   결과: PLAY33_yt_career_harvest/data_gravitas_{ko,en}/ (전사 KO16+EN16 + 카드 133 + 종합 리포트)
#   사전설치(무거움, 코드 실행경로 밖): pip install yt-dlp faster-whisper  (+ ffmpeg, CUDA GPU)

# ── 2단계: 스트레스테스트 워크플로우 (Claude Code Workflow) ──
#   gravitas_stress_test.workflow.js — 8 무시·무례 상황 × (적용→skeptic 현실검증) = 16 subagent (pipeline).
#   결과를 gravitas_findings.json 으로 저장(워크플로우는 리턴만 하므로 결과 JSON을 직접 기록).

# ── 3단계: .docx 빌드 ──
cd PLAY40_gravitas\docs
npm install        # 최초 1회 (docx 9.5.1, 자급 node_modules — 이미 설치돼 있음)
node build_docx.js # gravitas_playbook.md → gravitas_playbook.docx
```

## 입력 / 출력
- **입력:** 주제 문자열("위엄/무게감/무시받지 않기"). 1단계가 유튜브에서 한·미 코퍼스를 수집(원형 4종: 협상가·프레임/권력·카리스마·경계).
- **출력:**
  - `PLAY33.../data_gravitas_ko/reports/gravitas_report.md` — 1단계 추상 프레임(위엄 6축 + 카드 근거 + 문화비교 + 조작경고). KO·EN 카드를 합친 **단일 종합본**(EN 리포트 디렉토리는 비어 있음 — 의도된 단일 위치).
  - `PLAY40_gravitas/gravitas_findings.json` — 2단계 워크플로우 raw 결과(`{scenarios:[...]}`, 8상황 × 적용판정+플레이북+cut+dignity_line).
  - `PLAY40_gravitas/gravitas_playbook.md` — **최종 구체화 가이드**(위엄 6축 압축판 + 핵심 발견 + 8상황 trigger→action 표 + 치트시트 + 윤리).
  - `PLAY40_gravitas/gravitas_pocket.md` — **체화용 포켓카드**(playbook을 "그 순간 떠오를 만큼" 압축: 두 박자 "빼고→한 방" + 4비트 + 상황별 한 줄 6개 + 안전핀 + 이번 주 연습 1개). 잘 잊는 사용자를 위해 휴대폰으로 열어보는 1장.
  - `PLAY40_gravitas/docs/gravitas_playbook.docx` — Word 문서(로컬 전용, 28.8KB·표 9·TOC·zip 검증 통과).

## 가정 & 제약
- **PLAY 독립 규칙 절충:** PLAY37/38과 동일하게 1단계 수확은 PLAY33의 검증된 파이프라인을 *데이터로* 재사용(코드 import 아님). docx 빌더는 PLAY40 자체 `docs/node_modules`로 자급(다른 PLAY import 안 함). build_docx.js는 PLAY38 빌더를 gravitas용(제목·헤더·소스경로)으로 복제한 것.
- **위엄 ≠ 어른스러움:** 인접 PLAY38(어른스러움)이 "내 감정 다스리기"라면 PLAY40은 "남이 나를 어떻게 대하게 만드나". 별도 코퍼스(협상·권력·카리스마·경계)로 수확.
- **워크플로우 산출은 LLM subagent 판단**이라 경험적 실측이 아닌 합리적 추론. skeptic(현실검증) 단계가 코스프레·허세·조작·응징으로 변질되는 무브를 걸러낸다.
- **핵심 발견(연구 결론):** 프레임은 무시·무례 순간의 *마인드셋 절반(빼기·평정·방어 안 함)*엔 강력하지만 *전술 절반(타이밍·위계비용·에스컬레이션·동맹)*은 통째로 비어 있다. 그리고 **8개 상황 전부에서 모든 무브가 한 칸만 밀리면 "무시당한 분풀이를 위엄으로 포장한" 오만·응징·조작으로 변질** — 관통 안전핀은 PLAY38 "수용≠굴종"과 대칭인 **"위엄≠오만/지배, 단호함≠무례, 평정≠억압, 절제≠조작"**. 상세는 `gravitas_playbook.md §3`.
- **안전장치:** 플레이북은 위계·권력 비대칭에서 개인기의 한계를 명시하고 기록·HR·노동위·법률구조 등 제도적 레버리지로 이관할 것을 권고. 신변 위협은 경찰 **112**. "위엄"을 무시당한 분풀이·응징에 쓰지 말 것(상징적 1회 선긋기까지).
- Windows/PowerShell. node ≥ 18 (docx 빌드). 한글 폰트 Malgun Gothic.
- **드라이브 업로드는 미실시(외부 액션).** 원하면 폴더+Google Docs로 올릴 수 있음(.docx 바이너리는 base64 출력한도 이슈 있음 — 메모리 참조).

## 변경 이력
- 2026-06-06 — **체화용 포켓카드 추가** (`gravitas_pocket.md`). playbook 8상황·치트시트를 "그 순간 떠오를 만큼" 압축: 두 박자("빼고→한 방")+4비트(멈춤·빼기·한 줄·복귀)+상황별 입에 붙일 한 줄 6개+안전핀("선은 한 번만, 분풀이로 미끄러지면 오만")+이번 주 연습 1개("멈춤"만). 잘 잊는 사용자가 휴대폰으로 열어보는 1장 — 전체 가이드는 외우려다 하나도 안 되므로 최소단위로 분리.
- 2026-06-06 — **완성.** 끊겼던 파이프라인 재개·end-to-end 완료. 1단계 수확(PLAY33 data_gravitas_ko/en, 전사 KO16+EN16, 카드 133장, 종합 리포트)은 이전 세션 산출물이 온전해 재사용. ②스트레스테스트: `gravitas_stress_test.workflow.js`(8 무시·무례 상황×적용→skeptic 현실검증=16 subagent, pipeline) **재실행**→raw `gravitas_findings.json` 저장(이전 실행은 결과가 디스크에 안 남아 유실됨). ③종합: `gravitas_playbook.md`(위엄 6축 압축판+핵심 발견+8상황 trigger→action 표 7행씩+치트시트+윤리)→`docs/build_docx.js`(PLAY38 빌더 복제·gravitas화)로 `.docx` 빌드(28.8KB·표 9·TOC·zip 검증). **핵심 발견:** 프레임=마인드셋 절반(빼기·평정)엔 강하나 전술 절반(타이밍·위계비용·에스컬레이션·동맹)은 빔; 8상황 전부에서 skeptic이 "위엄은 상징적 1회 선긋기까지, 무시당한 분풀이로 미끄러지면 오만/응징"을 독립적으로 경고 → 관통 안전핀 "위엄≠오만/응징"(PLAY38 "수용≠굴종"과 대칭).
- 2026-06-06 — 최초 생성(스캐폴드). 스트레스테스트 워크플로우 작성 + docx 모듈 준비(중단됨).
