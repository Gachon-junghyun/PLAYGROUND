export const meta = {
  name: 'logic-scenario-stress-test',
  description: '말싸움/토론 163카드에서 역추출한 논리(truth-tracking) 6축을 6개 현실 자리에 적용→skeptic이 수사·교과서를 쳐내고 논리 훈련 플레이북으로 구체화',
  phases: [
    { title: '적용', detail: '자리별 논리축 적용 + 무브 판정(clean/adapt/useless, 논리/수사, 반사/사전준비) + 누락 보강' },
    { title: '현실검증', detail: 'skeptic이 수사·교과서 헛소리 쳐내고 논리 플레이북 + 훈련가능성 평가' },
  ],
}

// ── PLAY33 말싸움/토론 코퍼스(영어 99 + 한국 64 = 163카드)에서 'truth-tracking'만 역추출한 논리 프레임 ──
// 핵심 분리: 이김(winning/수사) ≠ 옳음(being right/논리). 이긴 것처럼 보이게 하나 옳음엔 기여 0인 무브는 🚫수사로 격리.
const FRAMEWORK = `
논리 6축 (말싸움/토론 163카드 역추출, 옳음에 기여하는 것만):

[L1 정의 규율] 핵심어/추상어를 먼저 정의하거나 상대에게 정의를 요구한다. 버즈워드 "그게 정확히 무슨 뜻이죠?"(E208), 무서운 단어를 문자 그대로 시험("open border면 그냥 걸어들어가야지", E515), 형용사 자가 정의("내가 말하는 '온전한'이란~", D107). 논리기능: 모호어가 추론을 오염시키는 걸 차단, "우리가 같은 걸 말하고 있나" 확인. ※수사판('정의를 장악해 상대를 가둠')은 이김용 — 논리판은 '정의 합의'.

[L2 입증책임] 주장하는 쪽이 증명한다(나 자신 포함). 출처 없는 주장 폭로 "사례 있다면 이름·날짜 하나만"(E108 John Smith 함정), 명분에 메커니즘·타임라인 요구 "그래서 구체적으로 뭐가 언제 바뀌나"(E304/E607), 검증가능 날짜사슬로 직관 뒤집기(E517). 논리기능: 무근거 주장을 기본값으로 받지 않음.

[L3 모순·일관성] 한 입장집합이 동시에 참일 수 있나 검사. 두 명제 충돌 노출("죽고싶은 광신도가 왜 종전협상에?", E412), 직전 발언과 대조(E405), 대칭 테스트=같은 기준을 내 편/반대편에 동일 적용(E309 "네 편 지면 그사람탓, 우리편 지면 언론탓?"), 강→약 골대이동 포착·고정(E516). 논리기능: 자기 포함 누구의 입장도 내적 모순 점검.

[L4 오류 탐지] 형식·비형식 오류 패턴 인식·명명. gish gallop(말폭탄)·motte-and-bailey(강약 왕복)·거짓 이분법·no-true-Scotsman을 소리내어 명명해 해체(E604/E105/E616/E518), 함정 선제 면역. 논리기능: '당했을 때 알아보는 법'의 핵심 — 가장 전이력 높은 축(어디서나 작동).

[L5 주장 보정] 주장 강도를 증거 강도에 맞춤(calibration). 강주장↔약주장 분리, 확실/불투명/어려움으로 등급화(PLAY39 선거리포트가 실연: 국정조사=확실, 특검=불투명, 재선거=어려움), '그럴듯함≠확률' 점검. 논리기능: 100%/0%로 안 가고 증거에 비례한 신뢰도 부여.

[L6 전제·반증 검토(스틸맨)] 내 결론의 전제를 의심하고 반대 입장을 가장 강한 형태로 세운다. 상대 전제를 부정 말고 가장 강하게 받아 방향만 검토(rebuttal judo E507/E102), 제1원리까지 끓이기, 2차 결과까지 시뮬(세컨드오더), 입장 스위치(상대 자리에서 다시 보기). 논리기능: 확증편향·동기화된 추론 차단.

🚫 수사(RHETORIC) — 논리 아님. 당했을 때 식별용, 내가 쓰지 말 것:
페이스 강탈/속도조절(D214·E211), 가상 캐릭터 조롱(M708), '감정적이시네' 라벨로 통째 무력화(E312), 톤·경멸 연출·피아노치기(E104·D111), I-메시지로 상대 흔들기(D215), 청중 장악용 owns/destroys 편집, 그리고 [윤리위험] 가스라이팅(D207)·가짜 사회증거(D306c)·더블바인드(D311)·가짜 희소성(D314). 이것들은 '이긴 것처럼' 보이게 하지만 주장의 참/거짓엔 기여 0. 일부는 조작.

주의: 코퍼스는 '이기는 토론' 편향(다수 owns/destroys 편집) — won은 실제 논파가 아니라 청중장악일 때 많음. 화자분리 없음(귀속은 문맥추론). 카드는 수사적 효과의 표본이지 진위 판정이 아님.
`

const SCENARIOS = [
  { key: 'live_argument', title: '실시간 말싸움/토론 (면전, 시간압박)', desc: '친구·동료·가족과 면전에서 의견이 부딪쳐 즉석으로 주고받는 상황. 또는 준비된 토론. 시간압박·감정·청중(주변 사람)이 끼고, 종이에 정리할 틈 없이 머릿속·말로 빠르게. 코퍼스의 본거지지만 "이기기"와 "옳기"가 가장 충돌하는 자리.' },
  { key: 'info_eval', title: '정보·뉴스·통계·음모론을 혼자 평가 (상대 없음)', desc: '기사·유튜브·SNS글·통계·"~카더라"를 혼자 읽으며 이게 믿을 만한지 판단하는 상황. 적대 상대가 없어 흔들 사람도 없지만, 그래서 내 확증편향·게으름이 유일한 적. PLAY39 선거리포트가 이 자리의 실연.' },
  { key: 'self_check', title: '내 생각 점검 — 동기화된 추론 (적이 나 자신)', desc: '내가 믿고 싶은 것, 화났을 때 떠오른 결론, "역시 내가 맞아" 싶은 순간을 스스로 검열하는 상황. 외부 상대가 없어 논리축을 *나에게* 돌려야 한다. 가장 어렵고 가장 본질적 — 논리를 남 패는 데가 아니라 자기교정에 쓰는 자리.' },
  { key: 'decision', title: '중요한 의사결정 (살까 말까·어느 쪽·되돌리기 어려움)', desc: '큰 지출·진로·계약처럼 되돌리기 어렵고 정보 불완전한 결정. 감정(불안·욕심)과 세일즈맨의 설득이 끼어든다. 전제검토·2차결과·주장보정이 실제로 돈/시간을 좌우하는 자리.' },
  { key: 'ethical_persuade', title: '윤리적 설득·발표 (남을 움직이되 조작 안 하기)', desc: '내 주장·결과물로 남을 설득하거나 발표하는 상황. "통하는 수사"와 "옳은 논증"의 경계에서, 효과는 있지만 조작인 무브를 스스로 안 쓰기로 선을 긋는 자리. 설득윤리가 정면으로 걸림.' },
  { key: 'manipulation_defense', title: '선동·가스라이팅·논리로 가장한 수사 방어', desc: '누군가(세일즈·사이비·정치선동·조종적 지인)가 논리처럼 보이는 수사로 나를 밀어붙이는 상황. 거짓 이분법·가짜 사회증거·기세·더블바인드를 *명명해서* 막아야 하는 자리. 코퍼스 🚫수사 목록이 여기선 방어용 체크리스트가 된다.' },
]

const APPLY_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['scenario', 'mini_cases', 'moves', 'missing', 'verdict'],
  properties: {
    scenario: { type: 'string' },
    mini_cases: { type: 'array', minItems: 1, items: { type: 'string' }, description: '이 자리의 현실적 구체 미니 상황 1~2개' },
    moves: {
      type: 'array', minItems: 6,
      items: {
        type: 'object', additionalProperties: false,
        required: ['framework_move', 'axis', 'kind', 'verdict', 'trainable_as', 'concrete_form'],
        properties: {
          framework_move: { type: 'string', description: '적용한 논리 무브 (L1~L6 또는 🚫수사, 카드ID 포함)' },
          axis: { type: 'string', description: 'L1정의/L2입증/L3모순/L4오류/L5보정/L6전제 중 어디 (또는 수사)' },
          kind: { type: 'string', enum: ['logic', 'rhetoric', 'both'], description: 'logic=옳음에 기여(truth-tracking) / rhetoric=이김에만 기여 / both=둘 다' },
          verdict: { type: 'string', enum: ['clean', 'adapt', 'useless'], description: 'clean=그대로 먹힘 / adapt=변형해야 먹힘 / useless=이 자리엔 안 먹힘 (다 clean이면 거짓말)' },
          trainable_as: { type: 'string', enum: ['reflex', 'setup', 'knowledge'], description: 'reflex=0.5초 반사로 굳힐 수 있음 / setup=사전 정찰·준비 있어야 작동 / knowledge=개념을 알고 있어야만 발동' },
          concrete_form: { type: 'string', description: '이 자리에서 실제로 취하는 구체 행동/말 (추상어 금지)' },
        },
      },
    },
    missing: { type: 'array', items: { type: 'string' }, description: '프레임엔 없지만 이 자리에 꼭 필요한 논리 무브' },
    verdict: { type: 'string', description: '논리 프레임이 이 자리에서 "옳기 위해" 현실적으로 쓸 만한가 (정직하게)' },
  },
}

const PLAYBOOK_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['scenario', 'playbook', 'cut', 'trainability', 'realism'],
  properties: {
    scenario: { type: 'string' },
    playbook: {
      type: 'array', minItems: 4,
      items: {
        type: 'object', additionalProperties: false,
        required: ['trigger', 'action', 'is_truth_tracking'],
        properties: {
          trigger: { type: 'string', description: '이런 순간이 오면 (구체적 신호)' },
          action: { type: 'string', description: '이렇게 한다 (한 동작/한 마디, 바로 실행 가능)' },
          source: { type: 'string', description: '근거 논리축/카드ID (있으면)' },
          is_truth_tracking: { type: 'boolean', description: 'true=옳음에 기여하는 논리 / false=이김용 수사라 경계 표시' },
        },
      },
    },
    cut: { type: 'array', items: { type: 'string' }, description: '잘라낸 것 + 이유. 특히 (a)교과서적이라 아무도 안 함 (b)논리로 위장한 수사라 옳음엔 무관 — 둘을 구분해 적어라' },
    trainability: { type: 'string', description: '이 자리에서 논리의 어떤 부분이 *반사로 굳힐 수 있고*(후천 훈련 가능) 어떤 부분이 *사전준비/지식*을 요구하는지 솔직 평가. "논리는 키울 수 있나"에 이 자리가 주는 답.' },
    realism: { type: 'string', description: '논리 프레임이 이 자리에서 "이기기"가 아니라 "옳기"에 살아남는 정도 솔직 평가' },
  },
}

const applyPrompt = (s) => `너는 "${s.title}"에 실제로 자주 처하는 현실적인 사람이다. 아래 '논리 6축 프레임'을 이 자리에 적용해보고, 각 무브가 *이기는 게 아니라 옳기 위해* 현실에서 진짜 먹히는지 냉정하게 판정하라.

## 자리
${s.title} — ${s.desc}

## 논리 6축 프레임 (적용 대상)
${FRAMEWORK}

## 할 일
1. 이 자리의 **현실적인 미니 상황 1~2개**를 구체적으로 떠올린다.
2. 프레임의 6축(+🚫수사)을 훑으며 **이 자리에 적용되는 무브를 최소 6개** 골라, 각각:
   - kind: logic / rhetoric / both — 이 무브가 *옳음*에 기여하나 *이김*에만 기여하나. 정직하게. (말싸움 자리에선 효과적인데 rhetoric인 게 많을 것이다 — 그걸 솔직히 rhetoric으로 찍어라)
   - verdict: clean / adapt / useless (다 clean이면 거짓말)
   - trainable_as: reflex(0.5초 반사로 굳힘) / setup(사전 정찰 필요) / knowledge(개념을 알아야 발동)
   - concrete_form: 이 자리에서 **실제로 취하는 구체 행동이나 입 밖에 낼 말**. 추상어 금지.
3. **missing**: 프레임엔 없지만 이 자리에서 옳기 위해 꼭 필요한 무브.
4. **verdict**: 이 프레임이 이 자리에서 "옳기 위해" 현실적으로 쓸 만한가.

핵심 긴장: 이 코퍼스는 "이기는 토론"에서 왔다. 이기는 데 좋은 무브와 옳은 데 좋은 무브는 다르다 — 그 차이를 kind로 정직하게 갈라라. 스키마(StructuredOutput)에 맞춰 반환.`

const criticPrompt = (s, applied) => `너는 "${s.title}"을 수도 없이 겪었고, "말싸움에서 이기는 것"과 "실제로 옳은 것"을 혼동하지 않는 깐깐한 현실주의자다. 아래는 누군가가 논리 프레임을 이 자리에 적용한 결과다. 네 일은 **수사(이김용)와 교과서적 헛소리를 쳐내고, 옳기 위해 진짜 쓰는 논리만 손에 잡히는 플레이북으로 만드는 것**이다.

## 자리
${s.title} — ${s.desc}

## 적용 결과 (검토 대상)
${JSON.stringify(applied, null, 2)}

## 할 일
1. **cut**: 잘라낼 것을 이유와 함께. 두 종류를 구분하라 — (a)교과서적이라 그 자리에서 아무도 안 함, (b)효과는 있지만 *논리로 위장한 수사*라 "옳음"엔 무관(페이스강탈·라벨링·캐릭터조롱·조작기법 등). clean/adapt여도 rhetoric이면 플레이북에선 빼되 "당했을 때 식별용"으로 남겨라.
2. **playbook**: 살아남은 논리 + missing을 합쳐 **'이런 순간(trigger) → 이렇게(action)' 4~7개**. action은 한 동작/한 마디로 그 자리에서 바로. 각 항목에 is_truth_tracking 표시(false면 "이건 수사니 경계" 의미). 가능하면 source에 카드ID/축.
3. **trainability**: 이 자리에서 논리의 어떤 부분이 *반사로 굳힐 수 있고*(=후천적으로 훈련 가능) 어떤 부분이 *사전준비·지식*을 요구하는지 솔직히. 이게 "논리는 후천적으로 키울 수 있나"라는 핵심 질문에 이 자리가 주는 답이다.
4. **realism**: 프레임이 이 자리에서 "이기기"가 아니라 "옳기"에 살아남는 정도 한 단락.

핵심 기준: "실제로 그 자리에서 *옳기 위해* 할 사람만 적어라." 멋있게 이기지만 옳음과 무관한 건 cut(단 식별용 메모). 스키마(StructuredOutput)에 맞춰 반환.`

phase('적용')
const results = await pipeline(
  SCENARIOS,
  (s) => agent(applyPrompt(s), { schema: APPLY_SCHEMA, phase: '적용', label: `적용:${s.key}` }),
  (applied, s) => agent(criticPrompt(s, applied), { schema: PLAYBOOK_SCHEMA, phase: '현실검증', label: `검증:${s.key}` })
    .then((playbook) => ({ key: s.key, title: s.title, applied, playbook })),
)

const ok = results.filter(Boolean)
log(`자리 ${ok.length}/${SCENARIOS.length} 스트레스테스트 완료`)
return { scenarios: ok }
