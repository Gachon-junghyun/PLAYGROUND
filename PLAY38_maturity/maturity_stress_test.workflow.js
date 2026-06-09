export const meta = {
  name: 'maturity-hard-situation-stress-test',
  description: '어른스러움 추상 프레임(6축·카드99)을 9개 어려운 현실 상황에 적용→skeptic 현실검증으로 "그 순간 어떻게 행동하나" 플레이북으로 구체화',
  phases: [
    { title: '적용', detail: '어려운 상황별 6축 적용 + 무브 판정(clean/adapt/useless) + 누락 보강' },
    { title: '현실검증', detail: 'skeptic이 교과서적 헛소리/수용으로 포장된 회피를 쳐내고 현실 플레이북으로 구체화' },
  ],
}

// ── 1단계 수확 종합 프레임 (maturity_report.md 요약) ──
const FRAMEWORK = `
어른스러움(성숙함) 6축 — 한국 심리·상담·불교·스토아 유튜브 18편→카드 99장에서 수렴:
[축1] 감정조절: "참기"가 아니라 자극과 반응 사이 간격 만들기. 화나면 그 자리를 뛰어서 떠나 3분(X201)·15초 심호흡으로 폭발 넘기기(X215)·전화 끊고 산책(X101). 감정은 머리가 아니라 몸의 움직임이니 몸 변화를 먼저 알아차림(X320), 평소에 안 변하도록 미리 훈련(X321). 감정을 뭉치지 말고 이름 붙여 세분화(X110·X212). 누르면 의지력 바닥나 더 터짐(X203)→누르지 말고 끊기.
[축2] 현실수용: 통제 이분법이 척추. "통제 가능한가?"부터 묻기(X313), 외부 자극은 못 정하니 내 마음 면역력을 키움(X303). 배신은 그 사람 본성("돌을 위로 던지면 떨어진다")(X316), 억울함은 밝히면 원한이 원한을 낳으니 덮을 줄 알기(X306·X307), 최선 다하되 결과 집착만 내려놓기(X317). 비난은 내가 동의할 때만 효력이 있다(X219). ⚠경계: 수용≠굴종, 순수 착취는 도망쳐야(X406).
[축3] 책임·주체성(코퍼스 최약축): 감정의 오리진은 나—누가 유발했어도 소화 못 한 책임은 내 것(X213). 남탓 대신 내가 할 수 있는 것(X113). 내 선택을 해명·변명 안 하는 게 인생의 주인(X221). 손해 봐도 내가 싫어 끊는다고 자기 선택임을 인정(X311).
[축4] 자기객관화: 한 발 물러서 나를 관찰해 데이터 모으기(X214), 내 미숙함을 먼저 인정—성격이 아니라 배울 능력(X218). 남 진단 전에 내 그릇부터(X205). 무의식 나쁜 습관(독심술·자기비하)을 적어 의식화해 대체(X412). 성공체험 일반화(휴브리스) 경계(X104). 무례를 악의로 개인화 말기(X209·X318).
[축5] 관계성숙: 솔직함≠무례함—할 말은 하되 상대가 받을 언어로 조정(X206), You→I-message(X210·X126), 평가 대신 상황·기분 설명(X126). 손절=폭파가 아니라 마음속 등급 한 칸 내리기(X410), 관계는 흐르는 물(X401), 좋고싫음 안 따지면 다 만남(X310). 상처 줬으면 변명없이 인정·사과(X117). 화내는 사람과 그 자리서 다투지 말고 흘려보냈다 나중에(X207). 제3자와 함께 해로운 관계 평가(X405).
[축6] 절제·길게보기: 의지력은 총량 자원—지친 밤엔 중요 결정·소비·충돌을 미룸(X203), 섣불리 결정해 후회 잉태 말고 신중히 기다림(X312), 만족지연 연습(X419), 중독은 의지박약이 아니라 공허를 메우려는 의존이니 갈증의 출처를 다룸(X418).
관통: ①간격이 전부 ②오리진을 나로 ③통제 이분법으로 에너지 배분 ④개인화 안 하기 ⑤인정중독 탈출, 중심을 내 안으로 ⑥시작점은 "내가 미성숙하다"는 자각.
주의: 코퍼스가 "마음 다스리기(감정·관계·수용)"에 쏠리고 "행동·생계·약속·결정의 책임" 같은 행동하는 어른은 희박(책임축 6장뿐). 수용·인욕이 회피·자기억압으로 변질될 위험 있음.
`

const SCENARIOS = [
  { key: 'provoked', title: '무시·도발·모욕을 당하는 순간', desc: '사람들 앞에서 누가 나를 깔보거나, 비꼬거나, 모욕적인 말로 도발한다. 즉시 발끈해 받아치고 싶은 충동과 체면이 걸려 있다. 그 자리에서 어떻게 행동하나.' },
  { key: 'falsely_blamed', title: '억울하게 비난·오해받을 때', desc: '내가 안 한 일/의도가 왜곡돼 비난받거나 누명을 쓴다. 밝혀서 결백을 입증하고 싶은 강한 충동이 있는데, 밝히면 상대가 가해자가 되거나 분쟁이 커진다. 어디까지 밝히고 어디서 멈추나.' },
  { key: 'rage', title: '욱하고 화가 폭발하기 직전', desc: '가족·연인·동료에게 화가 머리끝까지 치밀어 폭언이 나오려는 그 15초. 한 번 터뜨리면 관계에 못이 박힌다. 그 순간 몸과 입을 어떻게 다루나.' },
  { key: 'my_failure', title: '내 실수로 일을 망치고 망신당했을 때', desc: '내 잘못으로 프로젝트/약속/일이 무너지고 사람들 앞에서 망신당했다. 변명·남탓·자기연민으로 도망치고 싶다. 책임을 어떻게 지고 다시 서나. (코퍼스 최약축 검증)' },
  { key: 'intimate_conflict', title: '가까운 사람과의 갈등·이별', desc: '연인·가족·오랜 친구와 서운함이 쌓여 다투거나 헤어질지 고민한다. 감정이 끓어 충동적으로 끊거나 폭발하기 직전. 분석적으로 접근하면 더 악화된다. 어떻게 푸나/정리하나.' },
  { key: 'money_duty', title: '돈·생계·떠안은 책임의 압박', desc: '생활비·빚·부양·내가 떠안은 책임이 어깨를 짓누른다. 도망치거나 무너지거나 남 탓하고 싶지만 그만둘 수 없는 자리다. 불안 속에서 어떻게 버티고 행동하나. (코퍼스 갭—마음 다스리기로 충분한지 검증)' },
  { key: 'toxic_cutoff', title: '해로운 사람·관계를 손절할지 판단', desc: '나를 착취·가스라이팅·반복적으로 상처 주는 사람이 있다. 끊자니 죄책감·필요·관계비용이 걸리고, 두자니 소진된다. 참을 관계와 끊을 관계를 어떻게 가르고 실행하나.' },
  { key: 'collapse', title: '불안·무너짐·자기비하에 빠졌을 때', desc: '큰 상처/실패 후 "내 인생은 쓰레기야" 같은 자기비하와 불안에 빠져 아무것도 못 하겠는 상태. 혼자 덮어버리고("됐어") 싶다. 어떻게 다시 일어서나, 언제 도움을 구하나.' },
  { key: 'envy', title: '남이 잘되는 걸 보고 질투·박탈감이 들 때', desc: '친구·동료·SNS 속 누군가가 나보다 잘나가는 걸 보고 시샘·비교·박탈감이 올라온다. 깎아내리거나 자기비하로 빠지고 싶다. 그 감정을 어떻게 다루나.' },
]

const APPLY_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['scenario', 'mini_cases', 'moves', 'missing', 'verdict'],
  properties: {
    scenario: { type: 'string' },
    mini_cases: { type: 'array', minItems: 1, items: { type: 'string' }, description: '이 어려운 상황의 현실적인 구체 미니 장면 1~2개' },
    moves: {
      type: 'array', minItems: 6,
      items: {
        type: 'object', additionalProperties: false,
        required: ['framework_move', 'axis', 'verdict', 'concrete_form'],
        properties: {
          framework_move: { type: 'string', description: '프레임의 어떤 무브를 적용했는지 (카드ID 포함)' },
          axis: { type: 'string', description: '축1~6 중 어디' },
          verdict: { type: 'string', enum: ['clean', 'adapt', 'useless'], description: 'clean=그대로 먹힘 / adapt=변형해야 먹힘 / useless=이 상황엔 안 먹힘' },
          concrete_form: { type: 'string', description: '이 상황에서 실제로 취하는 구체 행동/말 (추상 금지)' },
        },
      },
    },
    missing: { type: 'array', items: { type: 'string' }, description: '프레임엔 없지만 이 어려운 상황에 꼭 필요한 무브(특히 책임·행동·타이밍 때문에 생기는 것)' },
    verdict: { type: 'string', description: '프레임이 이 어려운 상황에 현실적으로 적용 가능한가 (정직하게). 수용이 회피로 변질될 위험도 짚어라.' },
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
    cut: { type: 'array', items: { type: 'string' }, description: '이 상황엔 교과서적/회피로 변질되는 프레임 무브 + 이유' },
    realism: { type: 'string', description: '추상 프레임이 이 어려운 상황에서 살아남는 정도 + 수용↔굴종/회피 경계에 대한 솔직 평가' },
  },
}

const applyPrompt = (s) => `너는 "${s.title}"을 실제로 겪는 평범한 사람이다. 아래 '어른스러움 추상 프레임'을 이 어려운 상황에 적용해보고, 각 무브가 현실에서 진짜 먹히는지 냉정하게 판정하라.

## 어려운 상황
${s.title} — ${s.desc}

## 어른스러움 추상 프레임 (적용 대상)
${FRAMEWORK}

## 할 일
1. 이 상황의 **현실적인 미니 장면 1~2개**를 구체적으로 떠올린다.
2. 프레임의 6축을 훑으며 **이 상황에 적용되는 무브를 최소 6개 이상** 골라, 각각:
   - verdict: clean(그대로 먹힘) / adapt(변형해야 먹힘) / useless(여기선 안 먹힘 — 솔직하게, 다 clean이면 거짓말)
   - concrete_form: 이 순간 **실제로 취하는 구체 행동이나 입 밖으로 낼 말**. "감정을 조절한다" 같은 추상어 금지.
3. **missing**: 프레임엔 없지만 이 상황에서 꼭 필요한 무브 — 특히 (a)행동·책임·생계처럼 마음 다스리기로 안 되는 것 (b)타이밍 (c)관계 기술.
4. **verdict**: 이 프레임이 이 어려운 상황에 현실적으로 쓸 만한가? **특히 "수용·내려놓기·인욕"이 이 상황에선 회피·자기억압·굴종으로 변질될 위험은 없는지** 정직히 반영하라.

스키마(StructuredOutput)에 맞춰 반환. concrete_form은 짧고 행동 가능하게.`

const criticPrompt = (s, applied) => `너는 "${s.title}"을 수도 없이 겪어본 깐깐한 현실주의자다. 아래는 누군가가 어른스러움 프레임을 이 상황에 적용한 결과다. 너의 일은 **교과서적 헛소리와 '성숙'으로 포장된 회피를 쳐내고, 진짜 그 순간 살아남는 것만 추려 손에 잡히는 플레이북으로 만드는 것**이다.

## 어려운 상황
${s.title} — ${s.desc}

## 적용 결과 (검토 대상)
${JSON.stringify(applied, null, 2)}

## 할 일
1. **cut**: 위 무브 중 교과서적·비현실적이거나, 특히 **"수용/내려놓기/인욕"이라는 이름으로 부당함을 참고 회피하게 만드는 것**을 골라 이유와 함께 잘라낸다. clean/adapt라도 현실에선 안 하거나 해로운 건 솔직히 쳐내라.
2. **playbook**: 살아남은 것 + missing을 합쳐 **'이런 순간이 오면(trigger) → 이렇게 한다(action)' 4~7개**. action은 한 동작/한 마디로 그 자리에서 바로 할 수 있어야 한다. 근거 카드ID를 source에 단다.
3. **realism**: 프레임이 이 상황에서 살아남는 정도 + **수용과 굴종/회피의 경계선**을 한 단락으로 솔직 평가. 어떤 축은 잘 옮겨오고 어떤 축(특히 책임·행동)은 비어 있는지.

핵심 기준: "실제로 그 순간 할 사람만 적어라." 성숙해 보이지만 회피인 건 cut. 스키마(StructuredOutput)에 맞춰 반환.`

phase('적용')
const results = await pipeline(
  SCENARIOS,
  (s) => agent(applyPrompt(s), { schema: APPLY_SCHEMA, phase: '적용', label: `적용:${s.key}` }),
  (applied, s) => agent(criticPrompt(s, applied), { schema: PLAYBOOK_SCHEMA, phase: '현실검증', label: `검증:${s.key}` })
    .then((playbook) => ({ key: s.key, title: s.title, applied, playbook })),
)

const ok = results.filter(Boolean)
log(`어려운 상황 ${ok.length}/${SCENARIOS.length} 스트레스테스트 완료`)
return { scenarios: ok }
