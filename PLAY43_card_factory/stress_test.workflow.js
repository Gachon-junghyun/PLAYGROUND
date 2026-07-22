export const meta = {
  name: 'card-factory-stress-test',
  description: '신규 사고함수 후보를 금융 시나리오에 수행(인용 아닌 데이터 답)→skeptic 적대검증으로 재진술·인용그침·anti_signal 미발화를 쳐내고 survives/cut 판정',
  phases: [
    { title: '적용', detail: '후보 함수를 현 금융 시나리오에 수행 + anti_signal을 news_alert.db 데이터로 판정' },
    { title: '적대검증', detail: 'skeptic이 재진술·인용그침·vacuous anti_signal을 refute → survives/cut + redesign' },
  ],
}

// 후보 함수는 args로 주입 (워크플로우는 파일 접근 불가 — 메인이 data/cards/*.functions.jsonl 신규분을 넘김)
//   args = { candidates: [<function-candidate obj>...], db_path: "<news_alert.db 절대경로>" }
//   또는 args = { candidates_json: "<stringified array>", db_path }  (안전 전달용)
let A = args
if (typeof A === 'string') { try { A = JSON.parse(A) } catch (e) { A = {} } }
A = A || {}
let candidates = A.candidates || A.candidates_json || []
if (typeof candidates === 'string') { try { candidates = JSON.parse(candidates) } catch (e) { candidates = [] } }
const DB = A.db_path || 'C:\\Users\\fivep\\OneDrive\\Desktop\\mvp\\research_Mvp\\news_alert.db'
log(`args typeof=${typeof args} / candidates=${candidates.length}개`)

const SCENARIO_HINT = `
현 한국·글로벌 금융 시나리오 풀(이 중 함수에 맞는 2~3개 골라 적용):
반도체 메모리 업황·HBM, 전력/원전/SMP, 2차전지·ESS, 자동차·관세, 조선·방산,
미국 금리·DXY·국채금리, AI capex, 중국 부양·부동산, 환율·외인 수급.
`.trim()

const APPLY_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['function_id', 'scenarios_applied', 'anti_signal_overall', 'info_gaps', 'performed_not_cited'],
  properties: {
    function_id: { type: 'string' },
    scenarios_applied: {
      type: 'array', minItems: 2,
      items: {
        type: 'object', additionalProperties: false,
        required: ['scenario', 'verification_answers', 'anti_signal_fired'],
        properties: {
          scenario: { type: 'string' },
          verification_answers: {
            type: 'array', minItems: 1,
            items: {
              type: 'object', additionalProperties: false,
              required: ['question', 'data_answer', 'source'],
              properties: {
                question: { type: 'string' },
                data_answer: { type: 'string', description: '데이터로 답. 가설형("~일 수 있다") 금지.' },
                source: { type: 'string', description: '[news_alert.db|source|date] 또는 [추론] 라벨' },
              },
            },
          },
          anti_signal_fired: { type: 'string', enum: ['no', 'partial', 'yes', 'no_data'] },
        },
      },
    },
    anti_signal_overall: { type: 'string', description: '종합 판정 + 본문에 없던 새 무력화 조건 발견 시 명시' },
    performed_not_cited: { type: 'string', description: '이 함수를 *수행*해서 나온 비자명 발견 1개 (인용만이면 빈손이라 적기)' },
    info_gaps: { type: 'array', items: { type: 'string' }, description: '못 채운 정량 공백' },
  },
}

const VERDICT_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['function_id', 'survives', 'is_restatement', 'data_grounded', 'anti_signal_testable', 'reasons'],
  properties: {
    function_id: { type: 'string' },
    survives: { type: 'boolean', description: '진짜·비자명·데이터검증가능한 사고 무브일 때만 true. 애매하면 false.' },
    is_restatement: { type: 'boolean', description: '기존 함수/뻔한 상식의 재진술인가' },
    data_grounded: { type: 'boolean', description: '적용이 데이터로 수행됐나(인용·손짓 아님)' },
    anti_signal_testable: { type: 'boolean', description: 'anti_signal이 실재하고 데이터로 검증 가능한가(vacuous 아님)' },
    reasons: { type: 'string', description: 'survives/cut 사유 한 단락' },
    redesign_suggestion: { type: 'string', description: 'anti_signal 보강·spec 수정 제안(있으면). function_redesign_queue 후보.' },
  },
}

const applyPrompt = (fn) => `너는 R5 v4 사고함수 *실행 프로토콜*의 수행자다(인용가 아님). 아래는 분석가 리포트에서 갓 증류된 **신규 사고함수 후보**다. 이걸 현 금융 시나리오 2~3개에 실제로 적용해 *수행*하라.

## 후보 함수
${JSON.stringify(fn, null, 2)}

## 시나리오 힌트
${SCENARIO_HINT}

## 수행 방법 (실행 프로토콜 Step A~C)
1. 함수의 verification_questions를 *던지고 데이터로 답한다*. 데이터는 mvp news_alert.db를 직접 sweep:
   Bash로 →  python -c "import sqlite3;c=sqlite3.connect(r'${DB}');cur=c.cursor();cur.execute(\\"SELECT date(s.fetched_at),s.source,s.title,substr(coalesce(c.body,s.summary,''),1,800) FROM seen_news s LEFT JOIN article_contents c ON s.url_hash=c.url_hash WHERE (s.title LIKE ? OR s.summary LIKE ?) AND date(s.fetched_at)>=date('now','-21 day') ORDER BY s.fetched_at DESC LIMIT 6\\",('%키워드%','%키워드%'));[print(r) for r in cur.fetchall()]"
   - 키워드는 함수의 도메인·트리거에서 뽑아라. 헤드라인만으로 의미 못 잡으면 본문(body)까지 읽어라.
2. 각 함수의 anti_signal 본문을 데이터로 **발화 여부 결론**(no/partial/yes/no_data). 가설형 금지.
3. anti_signal 본문에 *없던* 새 무력화 조건이 데이터에서 보이면 anti_signal_overall에 명시.
4. performed_not_cited: 이 함수를 *수행*해서 나온 비자명한 발견 1개. (이름만 인용했으면 여기가 빈손이 된다 — 그게 곧 약한 함수의 증거다.)

스키마(StructuredOutput)에 맞춰 반환. data_answer는 source 라벨 강제.`

const criticPrompt = (fn, applied) => `너는 "인용을 사고로 위장한 것"을 가장 싫어하는 깐깐한 회의주의자다. 아래 신규 사고함수 후보와 그 적용 결과를 보고, **진짜 라이브러리에 등재할 가치가 있는지** 냉정하게 refute하라.

## 후보 함수
${JSON.stringify(fn, null, 2)}

## 적용 결과 (검토 대상)
${JSON.stringify(applied, null, 2)}

## refute 체크 (하나라도 무너지면 survives=false)
1. **재진술(is_restatement)**: 이건 기존 F함수나 뻔한 투자 상식("실적 좋으면 오른다")의 다른 말 아닌가? related_functions와 abstract_form을 보고 판단.
2. **데이터 접지(data_grounded)**: 적용이 news_alert.db 데이터로 *수행*됐나, 아니면 "~할 수 있다"는 손짓·인용에 그쳤나? performed_not_cited가 진짜 비자명한가?
3. **anti_signal 검증가능(anti_signal_testable)**: anti_signal이 실재하고 데이터로 터질 수 있나, 아니면 무력화 불가능한 vacuous 문장인가?

survives=true는 셋 다 통과할 때만. 애매하면 false(cut). anti_signal 보강·spec 수정 아이디어가 있으면 redesign_suggestion에 적어라(라이브러리 진화 큐 후보). 스키마(StructuredOutput)에 맞춰 반환.`

if (!candidates.length) {
  log('스트레스 대상 후보 함수 0개 — 종료 (신규 함수가 없거나 모두 기존 함수에 매칭됨)')
  return { results: [], survived: [], redesign: [] }
}

phase('적용')
const results = await pipeline(
  candidates,
  (fn) => agent(applyPrompt(fn), { schema: APPLY_SCHEMA, phase: '적용', label: `적용:${fn.function_id || fn.name}` }),
  (applied, fn) => agent(criticPrompt(fn, applied), { schema: VERDICT_SCHEMA, phase: '적대검증', label: `검증:${fn.function_id || fn.name}` })
    .then((verdict) => ({ candidate: fn, applied, verdict })),
)

const ok = results.filter(Boolean)
// 게이트: 적대검증 생존 AND source_card_count>=2 (PLAY31/32 승격 기준)
const survived = ok.filter(r => r.verdict && r.verdict.survives && (Number(r.candidate.source_card_count) || 1) >= 2)
const held = ok.filter(r => r.verdict && r.verdict.survives && (Number(r.candidate.source_card_count) || 1) < 2)
const redesign = ok.filter(r => r.verdict && r.verdict.redesign_suggestion)
  .map(r => ({ function_id: r.candidate.function_id || r.candidate.name, suggestion: r.verdict.redesign_suggestion }))

log(`스트레스 ${ok.length}후보 → 생존+2카드 ${survived.length} / 생존하나 1카드보류 ${held.length} / cut ${ok.length - survived.length - held.length}`)

return {
  results: ok.map(r => ({ id: r.candidate.function_id || r.candidate.name, verdict: r.verdict, performed: r.applied && r.applied.performed_not_cited })),
  survived: survived.map(r => ({ ...r.candidate, _stress: r.verdict })),
  held_single_card: held.map(r => ({ id: r.candidate.function_id || r.candidate.name, name: r.candidate.name })),
  redesign,
}
