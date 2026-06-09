export const meta = {
  name: 'gravitas-disrespect-stress-test',
  description: '위엄·무게감 6축(카드133)을 8개 무시·무례 현실 상황에 적용→skeptic 현실검증으로 "그 순간 무시 안 당하려면 어떻게" 플레이북으로 구체화. 안전핀=위엄≠오만/조작',
  phases: [
    { title: '적용', detail: '무시·무례 상황별 6축 적용 + 무브 판정(clean/adapt/useless) + 누락 보강 + 변질위험 점검' },
    { title: '현실검증', detail: 'skeptic이 코스프레·허세·조작으로 변질되는 무브를 쳐내고 그 순간 살아남는 플레이북으로 구체화' },
  ],
}

// ── 1단계 수확 종합 프레임 (gravitas_report.md 요약) ──
const FRAMEWORK = `
무시받지 않는 위엄·무게감 6축 — 협상가·프레임/권력 장인·카리스마 코치·경계 수문장 32편(KO16+EN16)→카드133에서 수렴:
[축1] 지위·평판/만만함신호(status_reputation, 최다): 위엄은 더하기가 아니라 '만만함 신호' 빼기. 과잉사과 끊기(짠토커 K416), 자기잘못 아닌 일에 사과 금지, 과잉설명·변명 끊기(ThatGuy E402 "변명 시작=공격 승인"), 비굴한 웃음으로 무마 끊기(K415), 말끝 흐리지 말고 '~다'까지 맺기(한석준 K410), 과잉 공손(헤징·돌려말하기) 빼기(Bruce Lambert E415), 굽신·자기비하로 틈 먼저 열지 않기(이헌주 K405), 구걸(사랑·인정·관심·돈) 금지(예나 K301). 더하는 쪽=대체불가·희소성·권위(그린E201·치알디니E209·E208)지만 진짜 실력일 때만(희렌최 "본업 실력이 아우라" K309).
[축2] 존재감·비언어(presence_nonverbal): 저지위는 눈·입·발걸음에서 샌다. 방 들어가 3초 멈춰 공간 차지(Auren E310), gravitas=커지기 아니라 안 움츠러들기(E311), 서두르는 걸음·도망갈 구석 찾는 눈·사과하듯 빠른 미소 제거(E313), low&slow 낮고 느리게(Voss E109), 명령은 하강 억양(Harvey E214), 평소보다 천천히+흔들리지 않는 아이컨택(희렌최 K307), 강조는 키우지 말고 '앞에서 잠깐 쉬기'(한석준 K414), 목소리는 distinct·dynamic(Vinh E314).
[축3] 도발 앞 평정(composure_under_fire): 발끈=미끼 물기. 무례는 진실추구 아니라 컨트롤 테스트, 반응하는 순간 진다(ThatGuy E401). 모욕은 나에 대한 묘사 아니라 상대의 고백—나는 표적 아닌 관찰자(E406). 감정 90%는 사건 아니라 내가 깐 스토리(Therapy E411), 발끈 직전 입닫고 숨쉬고 시간벌기(E413). 공격에 같은 톤으로 맞서면 둘다 멍청해지고 아무것도 못얻음(Voss E110). 3초 참고 한박자(닥터유 K315). 감정 임계점 높이기(희렌최 K308).
[축4] 협상·레버리지(negotiation_leverage): 매달리지 않는 자가 통제. 무게 뿌리는 톤 아니라 떠날 수 있는 실제 대안 BATNA(COC E216 "더 나은 2번째 선택지 가진 쪽이 이긴다, care less할 수 있는 여유가 무게"). 첫제안 즉시 예스 금지(류재언 K102), 내가3 상대가7 말하게(K107), 말끝 미러링 후 침묵(Voss E105), A 말하지만 B 원함—B에 응답(E112). ⚠[조작주의] 라벨링·No질문·상호성 밀집.
[축5] 프레임 장악(frame_control): 방어하면 진다. 모욕 내용에 반박 말고 프레임을 쳐라—변호=상대 프레임 수락(COC E212). 수동공격에 해명 말고 "그게 무슨 의미야?" 되물으면 수세가 상대로(이헌주 K408). 옳고그름 다투지 말고 상황을 한문장 명명—"지금 둘다 너무 단정적이라 불안해"(삶의지혜 K312). 입장 아니라 그 밑 이해로 축 옮기기(Ury E113).
[축6] 경계·되돌려주기(boundary_assertion): 부드러운 톤+분명한 내용. "지금은 제 시간이 필요해서 그건 못할 것 같아요"(짠토커 K417), 건강한 공격성 "너 선 넘었어"를 말·태도·표정으로(K418). 낮고 단호하고 중립적 톤으로 사적으로 한문장—허락요청 아니라 규칙 통보(ThatGuy E404), 경계 무시되면 소동없이 조용히 떠남(E405). 시그니처 "제가 잘못 들은 것 같아서요, 좀 전 말씀 저에게 하신 건가요?"(닥터유 K314). 떠맡김엔 "그거 좀 어려울 것 같아요"(이헌주 K409).
관통 3알맹이: ①한 박자 늦추기(반사→선택, 모든 축의 최소단위) ②만만함 신호 제거(빼기의 규율) ③방어/매달림 안 하기. 무게 뿌리=톤 아니라 BATNA·실력. 단단함은 다정함과 한 쌍일 때만 위엄.
⚠️ 안전핀(필수 점검): 위엄≠오만/지배, 단호함≠무례, 평정≠억압/회피, 절제≠조작. 모든 카드 shadow가 한 칸 밀리면 오만·냉담·조작·허세로 변질됨을 경고. 협상·권력·설득 기법은 진정성 없으면 조작. 너진똑식 "또라이 반격"은 응징 편향—상징적 1회 선긋기까지만.
`

const SCENARIOS = [
  { key: 'talked_over', title: '회의·자리에서 내 말이 끊기고 무시당할 때', desc: '발언하는데 누가 덮어서 말하거나, 내 의견이 그냥 흘려지고 다음 사람으로 넘어간다. 끼어들어 우기자니 추해 보이고, 가만있자니 또 묻힌다. 그 순간 어떻게 무게를 세우나.' },
  { key: 'mocked', title: '면전에서 비꼼·조롱·은근한 깔봄을 당할 때', desc: '"옷이 좀 그러네?" "맹한 애가 추천하니까" 같은 잽·수동공격이 웃음 섞여 날아온다. 발끈하면 예민한 사람 되고, 같이 웃으면 만만해진다. 품위를 잃지 않고 어떻게 되받나.' },
  { key: 'authority_belittles', title: '상사·권위자가 나를 아랫사람 취급·함부로 대할 때', desc: '직급·나이를 앞세워 갑질하거나, 내 전문성을 무시하고 함부로 지시·핀잔한다. 대들면 찍히고, 참으면 굳어진다. 위계 안에서 어떻게 선을 긋나.' },
  { key: 'pushover_dumping', title: '반복적으로 일·부탁을 떠넘기고 만만하게 볼 때', desc: '"이것 좀 해줄 수 있지?"가 늘 나에게만 온다. 거절을 못 해 또 떠안고, 그게 당연시된다. 관계를 깨지 않으면서 어떻게 "호구 구조"를 끊나.' },
  { key: 'provoked_test', title: '무례한 도발·시비로 기싸움을 걸어올 때', desc: '대놓고 시비를 걸거나, 나를 시험하듯 무례하게 찌른다. 받아치면 진흙탕, 피하면 이긴 줄 안다. 그 자리에서 흔들리지 않고 어떻게 제압하나. (응징 충동 변질 위험 검증)' },
  { key: 'lowballed', title: '협상·거래·연봉에서 후려치기·갑질을 당할 때', desc: '내 값을 깎으려 들거나, "원래 이 정도면 됐지"식으로 후려친다. 굽히면 손해, 세게 나가면 관계가 깨질까 두렵다. 어떻게 무게를 지키며 레버리지를 잡나.' },
  { key: 'intimate_takes_for_granted', title: '가까운 사람이 나를 가볍게 여기고 약속을 안 지킬 때', desc: '연인·가족·오랜 친구가 내 시간·말을 가볍게 여기고, 약속을 당일 깨거나 무시한다. 정색하면 관계가 상하고, 넘어가면 패턴이 된다. 친밀함을 지키며 어떻게 무게를 회복하나.' },
  { key: 'new_room', title: '처음 들어간 자리에서 묻히고 만만하게 시작될 때', desc: '낯선 모임·새 팀·첫 미팅에서 존재감 없이 묻히고, 처음부터 가볍게 취급받는다. 무게 잡으면 허세 같고, 가만있으면 투명인간이 된다. 첫인상에서 어떻게 위엄을 세우나. (허세·코스프레 변질 위험 검증)' },
]

const APPLY_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['scenario', 'mini_cases', 'moves', 'missing', 'distortion_risk', 'verdict'],
  properties: {
    scenario: { type: 'string' },
    mini_cases: { type: 'array', minItems: 1, items: { type: 'string' }, description: '이 무시·무례 상황의 현실적 구체 미니 장면 1~2개' },
    moves: {
      type: 'array', minItems: 6,
      items: {
        type: 'object', additionalProperties: false,
        required: ['framework_move', 'axis', 'verdict', 'concrete_form'],
        properties: {
          framework_move: { type: 'string', description: '프레임의 어떤 무브를 적용했는지 (카드ID 포함)' },
          axis: { type: 'string', description: '축1~6 중 어디' },
          verdict: { type: 'string', enum: ['clean', 'adapt', 'useless'], description: 'clean=그대로 먹힘 / adapt=변형해야 먹힘 / useless=이 상황엔 안 먹힘' },
          concrete_form: { type: 'string', description: '이 상황에서 실제로 취하는 구체 행동/입 밖으로 낼 말 (추상 금지)' },
        },
      },
    },
    missing: { type: 'array', items: { type: 'string' }, description: '프레임엔 없지만 이 상황에 꼭 필요한 무브 (특히 타이밍·관계비용·위계 때문에 생기는 것)' },
    distortion_risk: { type: 'string', description: '이 상황에서 위엄 무브가 오만/조작/허세/응징/벽치기로 변질될 위험을 구체적으로 (안전핀: 위엄≠오만, 단호함≠무례, 평정≠억압, 절제≠조작)' },
    verdict: { type: 'string', description: '프레임이 이 무시·무례 상황에 현실적으로 쓸 만한가 (정직하게).' },
  },
}

const PLAYBOOK_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['scenario', 'playbook', 'cut', 'dignity_line'],
  properties: {
    scenario: { type: 'string' },
    playbook: {
      type: 'array', minItems: 4,
      items: {
        type: 'object', additionalProperties: false,
        required: ['trigger', 'action'],
        properties: {
          trigger: { type: 'string', description: '이런 순간이 오면 (구체적 신호)' },
          action: { type: 'string', description: '이렇게 한다 (한 동작/한 마디, 바로 실행 가능 — 실제 멘트면 더 좋음)' },
          source: { type: 'string', description: '근거 카드ID (있으면)' },
        },
      },
    },
    cut: { type: 'array', items: { type: 'string' }, description: '이 상황엔 코스프레/허세/조작/응징으로 변질되는 무브 + 이유' },
    dignity_line: { type: 'string', description: '위엄↔오만/조작, 단호함↔무례, 평정↔억압의 경계선을 이 상황에서 어떻게 지키는지 한 단락 솔직 평가' },
  },
}

const applyPrompt = (s) => `너는 "${s.title}"을 실제로 겪는 평범한 사람이다. 아래 '위엄·무게감 프레임'을 이 무시·무례 상황에 적용해보고, 각 무브가 현실에서 진짜 먹히는지 냉정하게 판정하라.

## 무시·무례 상황
${s.title} — ${s.desc}

## 위엄·무게감 프레임 (적용 대상)
${FRAMEWORK}

## 할 일
1. 이 상황의 **현실적인 미니 장면 1~2개**를 구체적으로 떠올린다.
2. 프레임의 6축을 훑으며 **이 상황에 적용되는 무브를 최소 6개 이상** 골라, 각각:
   - verdict: clean(그대로 먹힘) / adapt(변형해야 먹힘) / useless(여기선 안 먹힘 — 솔직하게, 다 clean이면 거짓말)
   - concrete_form: 이 순간 **실제로 취하는 구체 행동이나 입 밖으로 낼 말**(가능하면 실제 멘트). "위엄을 세운다" 같은 추상어 금지.
3. **missing**: 프레임엔 없지만 이 상황에서 꼭 필요한 무브 — 특히 (a)타이밍 (b)위계·관계비용 (c)상대가 안 멈출 때의 다음 수.
4. **distortion_risk**: 이 상황에서 위엄 무브가 **오만·조작·허세·응징·벽치기로 변질될 위험**을 구체적으로 짚어라(안전핀: 위엄≠오만, 단호함≠무례, 평정≠억압/회피, 절제≠조작).
5. **verdict**: 이 프레임이 이 무시·무례 상황에 현실적으로 쓸 만한가?

스키마(StructuredOutput)에 맞춰 반환. concrete_form은 짧고 행동 가능하게.`

const criticPrompt = (s, applied) => `너는 "${s.title}"을 수도 없이 겪어본 깐깐한 현실주의자다. 아래는 누군가가 위엄 프레임을 이 상황에 적용한 결과다. 너의 일은 **코스프레·허세·'무게 잡기'·조작·응징으로 변질되는 것을 쳐내고, 진짜 그 순간 무시 안 당하고 살아남는 것만 추려 손에 잡히는 플레이북으로 만드는 것**이다.

## 무시·무례 상황
${s.title} — ${s.desc}

## 적용 결과 (검토 대상)
${JSON.stringify(applied, null, 2)}

## 할 일
1. **cut**: 위 무브 중 (a)현실에선 허세·폼 잡기·코스프레로 보이거나 (b)조작/가짜공감이거나 (c)응징·기싸움으로 번지거나 (d)20대 또래·실제 위계에선 역효과인 것을 골라 이유와 함께 잘라낸다. clean이라도 그 자리에서 진짜 안 하거나 해로운 건 쳐내라.
2. **playbook**: 살아남은 것 + missing을 합쳐 **'이런 순간이 오면(trigger) → 이렇게 한다(action)' 4~7개**. action은 한 동작/한 마디로 그 자리에서 바로 할 수 있어야 한다(가능하면 실제 멘트). 근거 카드ID를 source에 단다.
3. **dignity_line**: 이 상황에서 **위엄↔오만/지배, 단호함↔무례, 평정↔억압/회피, 절제↔조작**의 경계선을 어떻게 지키는지 한 단락으로 솔직 평가. 특히 무시에 대응하다 똑같이 무례·응징으로 떨어지는 함정을 짚어라.

핵심 기준: "실제로 그 순간 위엄 있게 행동할 사람만 적어라." 무게 잡지만 허세인 것, 단호하지만 무례한 것, 평정이지만 억압인 것은 cut. 스키마(StructuredOutput)에 맞춰 반환.`

phase('적용')
const results = await pipeline(
  SCENARIOS,
  (s) => agent(applyPrompt(s), { schema: APPLY_SCHEMA, phase: '적용', label: `적용:${s.key}` }),
  (applied, s) => agent(criticPrompt(s, applied), { schema: PLAYBOOK_SCHEMA, phase: '현실검증', label: `검증:${s.key}` })
    .then((playbook) => ({ key: s.key, title: s.title, applied, playbook })),
)

const ok = results.filter(Boolean)
log(`무시·무례 상황 ${ok.length}/${SCENARIOS.length} 스트레스테스트 완료`)
return { scenarios: ok }
