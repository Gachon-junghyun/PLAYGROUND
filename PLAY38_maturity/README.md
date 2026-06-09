# PLAY38_maturity

## 목적
"어른스러움(성숙함)"을 유튜브 수확으로 **추상 프레임**으로 뽑은 뒤, subagent 워크플로우로 **어려운 현실 상황**(무시·도발/억울한 비난/실패·손해/욱하는 순간/갈등·이별/책임·돈 압박/거절/가족/위기 등)에 적용·현실검증해 **"그 어려운 순간에 어떻게 행동하는가"를 그 자리에서 바로 쓰는 구체 플레이북**으로 구체화하는 연구. PLAY37(문제해결)의 방법론을 어른스러움에 차용.

## 실행법
PLAY37과 동일한 3단계 파이프라인. 1단계 수확 산출물은 PLAY33 안에 격리(`data_maturity/`)되고, 2단계 스트레스테스트·3단계 문서화가 이 PLAY의 본체다.

```powershell
# ── 1단계: 유튜브 수확 (PLAY33 스크립트 운전) ──
#   결과: PLAY33_yt_career_harvest/data_maturity/ (전사 18편 + 카드 + 리포트)
#   사전설치: pip install yt-dlp faster-whisper  (+ ffmpeg, CUDA GPU)
cd PLAY33_yt_career_harvest
PLAY33_TOPIC=maturity python data_maturity/search_targets.py     # 후보 수집(큐레이션용)
#   → search_candidates.jsonl 보고 data_maturity/queue.jsonl 수기 큐레이션(18편)
PLAY33_TOPIC=maturity python -u scripts/03_pipeline.py > data_maturity/run.log 2>&1   # 다운로드+전사(무거움→background)

# ── 2단계: 스트레스테스트 워크플로우 (Claude Code Workflow) ──
#   maturity_stress_test.workflow.js — N개 어려운 시나리오 × (적용→현실검증) = 2N subagent.

# ── 3단계: .docx 빌드 ──
cd PLAY38_maturity/docs
node build_docx.js          # maturity_playbook.md → maturity_playbook.docx
```

## 입력 / 출력
- **입력:** 주제 문자열("어른스러움/성숙함"). 1단계가 유튜브에서 코퍼스를 자동 수집.
- **출력:**
  - `PLAY33.../data_maturity/reports/maturity_report.md` — 1단계 추상 프레임(성숙함 축 + 카드 근거).
  - `PLAY38_maturity/scenario_findings.json` — 2단계 워크플로우 raw 결과(시나리오별 적용판정+플레이북).
  - `PLAY38_maturity/maturity_playbook.md` — **최종 구체화 가이드**(성숙함 축 + 어려운 상황 플레이북 + 치트시트).
  - `PLAY38_maturity/docs/maturity_playbook.docx` — Word 문서(로컬 전용).

## 가정 & 제약
- **PLAY 독립 규칙 절충:** PLAY37과 동일하게 1단계 수확은 PLAY33의 검증된 파이프라인을 재사용(코드 import가 아니라 데이터 재사용). 산출물이 `PLAY33/data_maturity/`에 생긴다. docx 빌더는 PLAY38 자체 `node_modules`로 자급.
- **어른스러움 ≠ 남자다움:** 인접한 `PLAY33/data_manhood`(남자다움) 코퍼스가 이미 있으나, 어른스러움은 성별중립이며 감정조절·현실수용·자기객관화에 무게가 다르다. 별도 코퍼스로 수확.
- **코퍼스 큐레이션:** 검색 기반 ytsearch로 성숙함의 결(정의·감정조절·분노·현실수용/스토아·관계갈등·자기객관화·절제·자존감·경청)을 균형 큐레이션. "책임·주체성(남탓)" 쿼리는 검색이 빈값이라 **코퍼스 갭** — 스트레스테스트 시나리오가 이 빈칸을 메우도록 설계.
- **워크플로우 산출은 LLM subagent 판단**이라 경험적 실측이 아닌 합리적 추론. skeptic 단계가 교과서성·회피를 거른다.
- **핵심 발견(연구 결론):** 프레임은 어려운 순간의 *내면 절반(충동 차단)*엔 강력한 응급 브레이크지만 *행동 절반(복구·실무·선긋기·수입)*은 통째로 비어 있다(책임축 6%). 그리고 **"수용·내려놓기"가 행동 하나에 안 묶이면 9개 상황 전부에서 회피·굴종으로 변질**된다 — 안전핀은 "수용≠굴종". 상세는 `maturity_playbook.md §3`.
- **위기 안전장치:** 플레이북은 일상마비 2주 초과·자해/자살 생각 시 즉시 전문가·자살예방상담(109)을 명시. "수용"을 학대·범죄·부당 책임에 적용 금지.
- Windows/PowerShell. node ≥ 18 (docx 빌드, `docs/node_modules`). 한글 폰트 Malgun Gothic.
- **드라이브 업로드는 미실시(외부 액션).** 원하면 PLAY37처럼 폴더+Google Docs로 올릴 수 있음(.docx 바이너리는 base64 출력한도 이슈 있음 — PLAY37 변경이력 참조).

## 변경 이력
- 2026-06-05 — **상황극 플레이북 추가** (`maturity_roleplay_playbook.md` + `roleplay_playbook.workflow.js`). 구체 갈등 6개(연인 당일취소·상사 공개비난·부모 잔소리·친구 돈요구·집안일 분담·새벽 자기비하)를 양쪽 입장+미성숙/성숙 2테이크 대사극으로 극화→현실코치가 *그대로 말할 대사·그대로 할 몸동작* 단위로 구체화(6×극화→구체화=12 subagent). 각 상황 = both_pov + 2테이크 대사 + 실천표(trigger→say→do→card) + 수용vs굴종 경계 + 양쪽 교훈. 추상 표보다 실천 밀도 높임(사용자 요청).
- 2026-06-05 — **개선 라운드(부분).** ①카드 무결성 감사: 99장 evidence_quote 전부 자막에 실재(반-날조 통과). ②플레이북 적대 감사→안전(손절 고위험 신고채널 112·1366·132, 치트시트 학대 금지선, 위기 109·1577-0199)·일관성(X401 축 수정)·실행가능성·과장톤 수정 + 보강 시나리오 2개(거절 못함·결정마비)→docx 재빌드(29.7KB·표12). ③#1 한계(책임·행동축 6%) 메우기 착수: `data_maturity/search_targets2.py`(책임·실행·자립 12쿼리)로 **보충 8편 전사 완료**(`queue_supplement.jsonl`, manifest 26편; 미루기극복·결단력·주체성·회피극복). 보충 8편→**B5 카드 22장**(책임15·절제4) 추출, `cards_all.jsonl` 총 **121장**. 플레이북 §4에 "💪 (보강) 책임·행동축" 표 7행 추가→docx 재빌드(30.9KB·표13). 이로써 §3이 "비었다"고 진단한 *행동 절반*을 코퍼스로 메움. 부가 발견: 행동축을 직접 검색해도 한국 유튜브는 심리/뉴스로 쏠려 갭이 구조적임 재확인.
- 2026-06-05 — **완성.** 3단계 파이프라인 end-to-end 완료. ①수확: `PLAY33/data_maturity/`에 ytsearch 20쿼리→18편 전사(large-v3/cuda/ko)→subagent 4개(B1~B4) 6축 카드 **99장**(중복0·필드누락0·high75/med21/low3)→종합 `maturity_report.md`. ②스트레스테스트: `maturity_stress_test.workflow.js`(9 어려운상황×적용→skeptic현실검증=18 subagent, pipeline)→raw `scenario_findings.json`. ③종합: `maturity_playbook.md`(6축+9상황 trigger→action표+치트시트+윤리)→`.docx` 빌드(`docs/maturity_playbook.docx`, 27.7KB·표10·TOC·zip검증). **핵심 발견:** 프레임=내면 절반(충동 차단)엔 응급 브레이크로 거의 다 살아남으나 행동 절반(복구·실무·선긋기)은 빔(책임축 6%); 9개 상황 전부에서 skeptic이 "수용은 행동에 묶일 때만 수용, 아니면 굴종"을 독립적으로 경고 → 관통 안전핀 "수용≠굴종". 코퍼스 갭(돈·책임 시나리오)은 의도적으로 검증해 행동 무브를 프레임 밖에서 끌어옴.
- 2026-06-05 — 최초 생성(스캐폴드). 어른스러움 코퍼스 큐레이션(ytsearch 20쿼리→18편 큐) + 전사 파이프라인 기동.
