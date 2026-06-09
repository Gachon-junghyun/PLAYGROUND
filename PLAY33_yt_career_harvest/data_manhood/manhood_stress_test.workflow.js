export const meta = {
  name: 'manhood-scenario-stress-test',
  description: '남자다움 6기둥 행동강령을 7개 현실 시나리오에 적용→skeptic 현실검증으로 허세/교과서 쳐내고 구체 플레이북화',
  phases: [
    { title: '적용', detail: '시나리오별 6기둥 적용 + 판정(clean/adapt/posturing) + 그림자/누락' },
    { title: '현실검증', detail: 'skeptic이 영화적 허세 쳐내고 trigger→action 현실 플레이북으로' },
  ],
}

// ── 남자다움 추상 프레임 (manhood_report.md / 카드 92장에서 수렴) ──
const FRAMEWORK = `
남자다움 6기둥 (영화·실존 인물 18인→카드 92장에서 수렴). 핵심: 남자다움=세 보임이 아니라 신뢰감. 따뜻함이 빠지면 나머지 다섯은 위험한 가면.

[기둥1] 존재감(bearing): 말로 자기 증명 안 함, 준비·일관성이 대신 말하게 둠. 놀림에 발끈 말고 같이 웃음(키아누 X114). 항상성=유행 안 좇는 자기 기준(본드 X224). 직함 떼고 본명으로(로건 X212). 침묵으로 화면 잡음(차태식 X301). ▶그림자: 침묵·폼이 실속 없으면 허세·수상함(X318 폼생폼사).
[기둥2] 실력(competence): 자기 일은 자기 손으로, 티 안 나게 넘길 디테일도 제대로(톰크루즈 X101). 결과 전에 기초 능력 먼저 훈련(X102). 몸에 밴 숙련·절차(존윅 X116·X117). 말이 아니라 결과물로 신뢰(막시무스 X201). ▶그림자: 실력 과시가 군림·흉기가 됨.
[기둥3] 의리·보호(code): 지키는 선과 사람이 있음. 윗사람·다수가 누굴 깎을 때 동조 안 하고 챙기는 쪽(키아누 X111). 내 안위보다 지킬 대상 먼저(막시무스 X203, 차태식 X304). 책임을 남에게 안 떠넘기고 짊어짐(송자호 X315). ▶그림자: 의리가 폭력정당화·비례상실·범죄조직 충성으로(존윅 X118, 느와르).
[기둥4] 맷집(resolve): 무너져도 다시 섬. 압박에 발 안 뺌. 감정 부정 안 하고(무섭다 인정) 그대로 둔 채 행동만 한 칸(록키 X217). 확신은 행동 뒤에 옴—냉소적이어도 일단 움직이면 따라옴(로건 X211). '한 발'=전체 말고 다음 한 동작으로 축소(차태식 X307). 회복 이력 숨기지 않음(톰하디 X106). 닻=누구/무엇 위해(막시무스 X204, 마크 X314). ▶그림자: 고통 견디기를 훈장 삼으면 자기학대.
[기둥5] 절제(restraint): 도발에 즉답·격앙 안 함, 한 박자 멈추고 선만(존윅 X115). 특권 안 휘두름, 신분 안 들이밂(키아누 X112). 정점에서 방심 점검(톰하디 X107). 속내 함부로 안 흘림(대부 X223). ▶그림자: 절제가 정서적 마비·불신·통제로(본드 X226).
[기둥6] 따뜻함(humility_warmth): 강할수록 약한 것 돌봄(차태식 선인장 X310). 안 보이는 기여자 몫 먼저(키아누 X113). 곁에 있어주기(선우 X413). 힘 있어도 농담으로 편하게(마석도 X417). 자기 잘못은 죄책감으로 정직히 안고 감(로건 X209). ▶그림자: 온정이 선택적(내 식구만)이면 위선.
주의: 표본은 영화·미담이라 극적·이상화됨. 현실에선 톤다운 필요하고, 똑같이 하면 오히려 허세·과잉이 되는 무브가 많다—그걸 솔직히 골라내는 게 이 테스트의 목적.
`

const SCENARIOS = [
  { key: 'provoked', title: '무시·도발당하는 자리', desc: '누가 나를 깔보거나, 비꼬거나, 사람들 앞에서 면박을 주거나, 시비를 거는 상황. 발끈하면 지고 가만있으면 호구 같아 보이는 딜레마. 존재감·절제가 시험당함.' },
  { key: 'quit_urge', title: '압박 속 발 빼고 싶은 순간', desc: '어려운 과제·토론·공부·일에서 막혀서 "됐어, 이건 내 취향 아냐/관둘래"로 발 빼고 싶은 충동이 드는 상황. 발 빼면 편하지만 그게 도망인지 절제인지 헷갈림. 맷집이 시험당함.' },
  { key: 'protect', title: '약한 사람을 지켜야 하는데 동조 압력이 있는 자리', desc: '누가 부당하게 당하거나 따돌림·뒷담화·갑질을 목격했는데, 끼어들면 나도 표적이 되거나 분위기를 깨는 상황. 다수가 동조를 압박함. 의리·보호가 시험당함.' },
  { key: 'fail_shame', title: '실수·망신·약점이 드러나는 순간', desc: '내가 틀렸거나, 모른다는 게 들통나거나, 사람들 앞에서 망신당하거나, "넌 자격 없어" 같은 자기의심이 발동하는 상황. 맷집·겸손이 시험당함.' },
  { key: 'impress', title: '인정받고 싶은 자리 (발표·모임·소개·이성 앞)', desc: '잘 보이고 싶고 멋있어 보이고 싶은 자리(발표, 새 모임, 이성 앞, 면접). 허세·과시 욕구가 올라오는 상황. 존재감·따뜻함이 시험당하고, 허세 함정이 가장 큼.' },
  { key: 'conflict', title: '가까운 사람과의 갈등·다툼', desc: '친구·동료·가족과 오해나 서운함, 다툼이 생긴 상황. "이기는 것"이 목적이 아니라 관계를 푸는 게 목적이라, 강하게 나가면 더 망가짐. 절제·따뜻함이 시험당함.' },
  { key: 'temptation', title: '조종·편법의 유혹이 오는 순간', desc: '말로 상대를 이기려 조종하고 싶거나, 편한 길·편법으로 결과만 따먹고 싶거나, 약속을 슬쩍 어기고 싶은 유혹이 오는 상황. 신념·실력이 시험당함(설득=조종 경계 포함).' },
]

const APPLY_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['scenario', 'mini_cases', 'moves', 'shadow_traps', 'missing', 'verdict'],
  properties: {
    scenario: { type: 'string' },
    mini_cases: { type: 'array', minItems: 1, items: { type: 'string' }, description: '이 시나리오의 현실적 구체 미니 상황 1~2개' },
    moves: {
      type: 'array', minItems: 6,
      items: {
        type: 'object', additionalProperties: false,
        required: ['pillar_move', 'pillar', 'verdict', 'concrete_form'],
        properties: {
          pillar_move: { type: 'string', description: '6기둥의 어떤 무브를 적용했는지 (카드ID 포함)' },
          pillar: { type: 'string', description: '기둥1~6 중 어디 (존재감/실력/의리/맷집/절제/따뜻함)' },
          verdict: { type: 'string', enum: ['clean', 'adapt', 'posturing'], description: 'clean=그대로 먹힘 / adapt=톤다운·변형해야 먹힘 / posturing=현실에선 허세·과잉이라 안 먹힘' },
          concrete_form: { type: 'string', description: '이 상황에서 실제로 취하는 구체 행동/입 밖으로 낼 말. 추상어 금지.' },
        },
      },
    },
    shadow_traps: { type: 'array', items: { type: 'string' }, description: '이 시나리오에서 기둥이 그림자(허세·폭력·정서마비·자기학대·위선)로 뒤집히는 지점 1~2개' },
    missing: { type: 'array', items: { type: 'string' }, description: '6기둥엔 없지만 이 시나리오에 꼭 필요한 무브' },
    verdict: { type: 'string', description: '6기둥이 이 시나리오에 현실적으로 적용 가능한가 (정직하게)' },
  },
}

const PLAYBOOK_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['scenario', 'playbook', 'cut', 'one_liner', 'realism'],
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
          source: { type: 'string', description: '근거 기둥/카드ID (있으면)' },
        },
      },
    },
    cut: { type: 'array', items: { type: 'string' }, description: '이 시나리오엔 영화적 허세라 잘라낸 무브 + 이유' },
    one_liner: { type: 'string', description: '이 상황에서 속으로 욀 한 문장 (그 자리에서 바로 떠올릴 수 있게)' },
    realism: { type: 'string', description: '6기둥이 이 시나리오에서 살아남는 정도에 대한 솔직한 평가 — 어떤 기둥은 살고 어떤 건 죽는지' },
  },
}

const applyPrompt = (s) => `너는 "${s.title}"에 실제로 자주 처하는 평범한 현실의 한국 남자다(20대 학생/사회초년생 정서). 아래 '남자다움 6기둥'을 이 상황에 적용해보고, 각 무브가 현실에서 진짜 먹히는지 냉정하게 판정하라. 영화 표본은 극적이라, 똑같이 따라 하면 허세가 되는 게 많다 — 그걸 솔직히 골라내라.

## 시나리오
${s.title} — ${s.desc}

## 남자다움 6기둥 (적용 대상)
${FRAMEWORK}

## 할 일
1. 이 시나리오의 **현실적 미니 상황 1~2개**를 구체적으로 떠올린다 (실제 있을 법한 장면).
2. 6기둥을 훑으며 **이 시나리오에 적용되는 무브를 최소 6개** 골라, 각각:
   - verdict: clean / adapt / posturing (다 clean이면 거짓말이다. 영화에선 멋있지만 현실에선 허세인 건 posturing으로 솔직히 골라라)
   - concrete_form: 이 상황에서 **실제로 취하는 구체 행동이나 입 밖으로 낼 말**. "절제한다" 같은 추상어 금지. 예: "면박당하면 곧바로 받아치지 말고, 2초 쉬고 '그렇게 보셨구나' 한마디만 한 뒤 화제를 본론으로 돌린다."
3. **shadow_traps**: 이 상황에서 기둥이 그림자로 뒤집히는 지점(예: 존재감→허세, 의리→오지랖/폭력, 절제→찌질한 무반응).
4. **missing**: 6기둥엔 없지만 이 상황에 꼭 필요한 무브.
5. **verdict**: 6기둥이 이 시나리오에 현실적으로 쓸 만한가? 정직하게.

스키마(StructuredOutput)에 맞춰 반환. concrete_form은 짧고 행동 가능하게.`

const criticPrompt = (s, applied) => `너는 "${s.title}"을 수도 없이 겪어본 깐깐한 현실주의자다(허세를 가장 싫어함). 아래는 누군가가 남자다움 6기둥을 이 상황에 적용해본 결과다. 너의 일은 **영화적 허세·교과서적 헛소리를 쳐내고, 진짜 현실에서 멋있게 통하는 것만 추려 손에 잡히는 플레이북으로 만드는 것**이다.

## 시나리오
${s.title} — ${s.desc}

## 적용 결과 (검토 대상)
${JSON.stringify(applied, null, 2)}

## 할 일
1. **cut**: posturing(허세)으로 판정된 것 + clean/adapt라도 현실에선 안 하거나 오글거리는 걸 이유와 함께 잘라낸다. (예: "도발당했다고 본드처럼 씩 웃으며 농담 던지기 — 현실에선 빈정상한 사람으로 보임")
2. **playbook**: 살아남은 것 + missing을 합쳐 **'이런 순간이 오면(trigger) → 이렇게 한다(action)' 4~7개**. action은 한 동작/한 마디로, 그 자리에서 바로 할 수 있어야 한다. 근거 카드ID는 source에.
3. **one_liner**: 그 자리에서 속으로 욀 한 문장 (짧고 기억하기 쉽게).
4. **realism**: 6기둥이 이 상황에서 살아남는 정도를 한 단락으로 솔직 평가 — 어떤 기둥은 잘 옮겨오고 어떤 건 죽는지. 특히 그림자(허세로 뒤집힘)를 어떻게 피하는지.

핵심 기준: "실제로 그 자리에서 할 사람만, 그리고 진짜 멋있어 보이는 것만 적어라." 멋부리지만 오글거리는 건 전부 cut. 스키마(StructuredOutput)에 맞춰 반환.`

phase('적용')
const results = await pipeline(
  SCENARIOS,
  (s) => agent(applyPrompt(s), { schema: APPLY_SCHEMA, phase: '적용', label: `적용:${s.key}` }),
  (applied, s) => agent(criticPrompt(s, applied), { schema: PLAYBOOK_SCHEMA, phase: '현실검증', label: `검증:${s.key}` })
    .then((playbook) => ({ key: s.key, title: s.title, applied, playbook })),
)

const ok = results.filter(Boolean)
log(`남자다움 시나리오 ${ok.length}/${SCENARIOS.length} 스트레스테스트 완료`)
return { scenarios: ok }
