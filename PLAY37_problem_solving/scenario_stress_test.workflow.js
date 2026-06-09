export const meta = {
  name: 'problem-solving-scenario-stress-test',
  description: '문제해결 추상 프레임을 7개 현실 시나리오에 적용→skeptic 현실검증으로 구체화',
  phases: [
    { title: '적용', detail: '시나리오별 프레임 적용 + 무브 판정(clean/adapt/useless) + 누락 보강' },
    { title: '현실검증', detail: 'skeptic이 교과서적 헛소리 쳐내고 현실 플레이북으로 구체화' },
  ],
}

// ── 1단계 수확에서 종합한 추상 프레임 (problem_solving_report.md 요약) ──
const FRAMEWORK = `
문제해결 5회로 (유튜브 20편→카드 109장에서 수렴):
[회로1] 문제정의(8할): '어떻게' 전에 '왜 이게 문제인가'를 먼저(X403). 현상≠문제, SMART로 재작성(X407). 5why로 근본원인까지(X401), 단 답은 통제·검증 가능한 것만(X402). 근본원인=가장 약한 고리 하나(TOC,X405). 목적·기대결과부터(X329). 주제를 구체적으로 한정(X317).
[회로2] 구조 외부화: 머릿속 말고 종이/다이어그램에 빈 틀을 먼저 그린다. 로직트리(왼→오, MECE)(X408,X409,X311), What-Why-How 3단(X411), 피시본(머리=문제·중간뼈=원인갈래)(X316), 노드마다 일단 3개씩(X312), 검증된 프레임 빌리기(4P·5force)(X412), 종이 장단점+점수표(X220). 시각화하면 '어디가 비었나'가 보임(X413).
[회로3] 가설→검증→집중 루프: 자료 다 모으지 말고 가설 먼저(X416,X420), 게스티메이션 어림값(X417), 작게 파일럿 후 확산(X328), 반증 나오면 그 시점부터 재설정(X419). 80/20 핵심20%에 집중(X421), 병목부터(X304), 다 고치지 말고 비중 큰 것(X323), 효과 확보 후에 효율(X331). AND조건 3개 넘기면 인간이 못함→조건 줄이기(X118), 동시 고려 7개 이하(X222).
[회로4] 메타인지(고수 분기점): 모름을 인정·질문(X214), '아는 착각'을 왜?로 깨기(X207), 완성의 착각 버리기(거절=학습신호)(X213). 인지편향 알아채기: 그럴듯함≠확률(X114), 직전경험 오염 점검(X109), 핸런의 면도날=어리석음을 악의로 돌리지마라(X429). 틀리기 쉬운건 천천히 읽어 직관 첫답 의심(X106), So-What 한번 더(X423), 부정 피드백 적극 요청(X426). 막힘탈출: 보조선 긋기(X205), 사례 벤치마킹(X306), 습관적 사고 깨기(X432), 입장 스위치로 관점전환(X217), 감당가능한 혼란(스토름) 자청(X218), 기록으로 자기객관화(X430).
[회로5] 전이(능력의 정체): 제1원리-기본 진실까지 끓여내려 다시 쌓기(X424), 통념은 구성요소로 쪼개 검증(X425). 멘탈모델 격자로 분야 넘나들기(X427). 세컨드오더-2차 반응까지 시뮬레이션(X428). 특수→n 일반화(X204). 같은 구조 다른 도메인 이식(X332). 편집(상위로 묶어 인지부하↓)(X102). 피라미드 결론·3개 요약(X434).
주의: 이 프레임은 일처리·공부 맥락에 두텁고 놀이·즉흥·사교엔 거의 미검증(코퍼스 편향). 김경일 X108·X113은 설득/조작 경계.
`

const SCENARIOS = [
  { key: 'boardgame', title: '보드게임/방탈출 하는 자리', desc: '전략 보드게임(카탄·티켓투라이드류)·방탈출·추리게임에서 이기거나 막힌 퍼즐을 푸는 즉석 상황. 시간 압박·불완전 정보·상대의 수·운이 섞임. 종이에 트리 그릴 여유는 거의 없고 머릿속·말로 빠르게.' },
  { key: 'exhibit', title: '전시/발표 자리 (내 결과물을 보여주고 질문에 답하기)', desc: '내 프로젝트·작품·부스·발표를 남에게 보여주고 그 자리에서 날아오는 질문·반박·관심에 대응하는 상황. 준비된 부분과 예상 못한 질문이 섞임. 관람/정보흡수 측면도 일부.' },
  { key: 'study', title: '공부 (안 풀리는 문제·어려운 개념·시험 전략)', desc: '혼자 책상에서 어려운 개념이 이해 안 되거나 문제가 안 풀리거나 시험 범위가 막막한 상황. 시간 여유는 상대적으로 있고 종이·기록 활용 가능.' },
  { key: 'work', title: '일처리 (갑자기 떨어진 모호한 업무·보고)', desc: '상사/클라이언트가 모호하게 던진 과제("이거 좀 알아봐줘")를 받아 방향을 잡고 결과를 보고하는 상황. 프레임의 본거지지만 신입·1인 상황에서 실제로 어떻게 굴리는지가 관건.' },
  { key: 'hangout', title: '놀러간 자리 (여행/모임에서 계획 틀어짐·즉흥 결정)', desc: '친구들과 여행·모임에서 예약이 펑크나거나 길을 잃거나 의견이 갈리거나 비가 오는 등 계획이 틀어진 즉흥 상황. 종이·분석 도구 없음, 분위기·관계가 걸려 있어 "분석적으로 보이면" 오히려 깸.' },
  { key: 'crisis', title: '위기·돌발 (고장·사고·펑크 같은 갑작스런 문제)', desc: '기기 고장·교통사고·예약 취소·갑작스런 일정 붕괴처럼 빠른 판단과 행동이 필요한 돌발 상황. 시간이 가장 촉박하고 감정(불안)이 끼어듦.' },
  { key: 'conflict', title: '인간관계 갈등 (오해·다툼 풀기)', desc: '연인·친구·동료와의 오해·다툼·서운함을 푸는 상황. "문제"가 상대 마음이라 분해·정량화가 안 먹히고, 분석적으로 접근하면 더 악화될 위험이 큼.' },
]

const APPLY_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['scenario', 'mini_cases', 'moves', 'missing', 'verdict'],
  properties: {
    scenario: { type: 'string' },
    mini_cases: { type: 'array', minItems: 1, items: { type: 'string' }, description: '이 시나리오의 현실적인 구체 미니 상황 1~2개' },
    moves: {
      type: 'array', minItems: 6,
      items: {
        type: 'object', additionalProperties: false,
        required: ['framework_move', 'axis', 'verdict', 'concrete_form'],
        properties: {
          framework_move: { type: 'string', description: '프레임의 어떤 무브를 적용했는지 (카드ID 포함)' },
          axis: { type: 'string', description: '회로1~5 중 어디' },
          verdict: { type: 'string', enum: ['clean', 'adapt', 'useless'], description: 'clean=그대로 먹힘 / adapt=변형해야 먹힘 / useless=이 상황엔 안 먹힘' },
          concrete_form: { type: 'string', description: '이 시나리오에서 실제로 취하는 구체 행동/말 (추상 금지)' },
        },
      },
    },
    missing: { type: 'array', items: { type: 'string' }, description: '프레임엔 없지만 이 시나리오에 꼭 필요한 무브' },
    verdict: { type: 'string', description: '프레임이 이 시나리오에 현실적으로 적용 가능한가 (정직하게)' },
  },
}

const PLAYBOOK_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['scenario', 'playbook', 'cut', 'realism'],
  properties: {
    scenario: { type: 'string' },
    playbook: {
      type: 'array', minItems: 4,
      items: {
        type: 'object', additionalProperties: false,
        required: ['trigger', 'action'],
        properties: {
          trigger: { type: 'string', description: '이런 순간이 오면 (구체적 신호)' },
          action: { type: 'string', description: '이렇게 한다 (한 동작/한 마디, 바로 실행 가능)' },
          source: { type: 'string', description: '근거 프레임 무브/카드ID (있으면)' },
        },
      },
    },
    cut: { type: 'array', items: { type: 'string' }, description: '이 시나리오엔 교과서적이라 잘라낸 프레임 무브 + 이유' },
    realism: { type: 'string', description: '추상 프레임이 현실에서 살아남는 정도에 대한 솔직한 평가' },
  },
}

const applyPrompt = (s) => `너는 "${s.title}"에 실제로 자주 처하는 현실적인 사람이다. 아래 '문제해결 추상 프레임'을 이 시나리오에 적용해보고, 각 무브가 현실에서 진짜 먹히는지 냉정하게 판정하라.

## 시나리오
${s.title} — ${s.desc}

## 문제해결 추상 프레임 (적용 대상)
${FRAMEWORK}

## 할 일
1. 이 시나리오의 **현실적인 미니 상황 1~2개**를 구체적으로 떠올린다 (실제 있을 법한 장면).
2. 프레임의 5회로를 훑으며 **이 시나리오에 적용되는 무브를 최소 6개 이상** 골라, 각각:
   - verdict: clean(그대로 먹힘) / adapt(변형해야 먹힘) / useless(여기선 안 먹힘 — 솔직하게 골라라, 다 clean이면 거짓말)
   - concrete_form: 이 상황에서 **실제로 취하는 구체 행동이나 입 밖으로 낼 말**. "구조화한다" 같은 추상어 금지. 예: 보드게임이면 "내 턴 오기 전에 '내가 이기려면 뭐가 막혀야 하지?'를 상대 관점에서 한 번 뒤집어 본다".
3. **missing**: 프레임엔 없지만 이 시나리오에서 꼭 필요한 무브(특히 시간압박·관계·즉흥성 때문에 생기는 것).
4. **verdict**: 이 추상 프레임이 이 시나리오에 현실적으로 쓸 만한가? (놀이·사교·즉흥 시나리오면 "종이에 트리 그릴 수 없다" 같은 현실 제약을 정직히 반영)

스키마(StructuredOutput)에 맞춰 반환. concrete_form은 짧고 행동 가능하게.`

const criticPrompt = (s, applied) => `너는 "${s.title}"을 수도 없이 겪어본 깐깐한 현실주의자다. 아래는 누군가가 문제해결 프레임을 이 시나리오에 적용해본 결과다. 너의 일은 **교과서적 헛소리를 쳐내고, 진짜 현실에서 살아남는 것만 추려 손에 잡히는 플레이북으로 만드는 것**이다.

## 시나리오
${s.title} — ${s.desc}

## 적용 결과 (검토 대상)
${JSON.stringify(applied, null, 2)}

## 할 일
1. **cut**: 위 무브 중 이 시나리오에선 교과서적·비현실적·과한 것을 골라 이유와 함께 잘라낸다. (예: "놀러간 자리에서 로직트리 그리기 — 분위기 깸, 아무도 안 함") useless로 판정된 것뿐 아니라, clean/adapt라도 현실에선 안 하는 걸 솔직히 쳐내라.
2. **playbook**: 살아남은 것 + missing을 합쳐 **'이런 순간이 오면(trigger) → 이렇게 한다(action)' 형식의 현실 플레이북 4~7개**. action은 한 동작/한 마디로, 그 자리에서 바로 할 수 있어야 한다. 가능하면 근거 카드ID를 source에 단다.
3. **realism**: 추상 프레임이 이 시나리오에서 살아남는 정도를 한 단락으로 솔직 평가 — 어떤 회로는 잘 옮겨오고 어떤 회로는 죽는지.

핵심 기준: "실제로 그 자리에서 할 사람만 적어라." 멋있어 보이지만 아무도 안 하는 건 cut. 스키마(StructuredOutput)에 맞춰 반환.`

phase('적용')
const results = await pipeline(
  SCENARIOS,
  (s) => agent(applyPrompt(s), { schema: APPLY_SCHEMA, phase: '적용', label: `적용:${s.key}` }),
  (applied, s) => agent(criticPrompt(s, applied), { schema: PLAYBOOK_SCHEMA, phase: '현실검증', label: `검증:${s.key}` })
    .then((playbook) => ({ key: s.key, title: s.title, applied, playbook })),
)

const ok = results.filter(Boolean)
log(`시나리오 ${ok.length}/${SCENARIOS.length} 스트레스테스트 완료`)
return { scenarios: ok }
