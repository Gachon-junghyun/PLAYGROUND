export const meta = {
  name: 'maturity-roleplay-concrete-playbook',
  description: '구체적 갈등 상황 6개를 양쪽 입장 상황극(미성숙/성숙 2테이크)으로 극화→현실코치가 대사·몸동작 단위의 실천 플레이북으로 구체화',
  phases: [
    { title: '극화', detail: '상황별 양쪽 입장 + 미성숙/성숙 2테이크 대사극 + 초벌 플레이북' },
    { title: '구체화', detail: '현실코치가 추상 제거→정확한 대사/몸동작으로, 수용≠굴종 안전점검' },
  ],
}

const FRAMEWORK = `
어른스러움 6축(카드 121장에서 수렴):
①감정조절: 자극-반응 사이 간격(욱하면 입 닫고 코로 4초·자리 뜨기 X215/X201), 누르지 말고 끊기(X203), 감정에 이름붙여 세분화(X110/X212).
②현실수용: 통제 이분법(X313), 비난은 내가 동의할 때만 효력(X219), 결과 집착만 내려놓기(X317). ⚠수용≠굴종, 부당함엔 적용 금지(X404/X406).
③책임·주체성: 감정의 오리진은 나(X213), 남탓·변명 끊기(X113/X221), 손해도 내 선택으로(X311).
④자기객관화: 한발 물러서 관찰(X214), 내 미숙 먼저 인정(X218), 무례를 악의로 개인화 말기(X209/X318), 독심술 끄고 직접 물어보기(X412/X407).
⑤관계성숙: 솔직≠무례 상대가 받을 말로(X206), You→I-message(X210/X126), 평가 대신 상황·기분(X126), 손절=등급 한칸(X410), 상처 줬으면 변명없이 사과(X117), 화내는 사람과 그자리서 안 싸우고 나중에(X207), 수긍 먼저(X217).
⑥절제·길게보기: 지친 밤엔 결정 미룸(X203), 섣불리 후회 잉태 말기(X312).
[행동축 보강 B5]: 마음 다스린 뒤 반드시 한 동작 — 10초짜리로 쪼개 시작(X504), 한 세트만 잘라 착수(X502), 고민이 행동을 대체 못하게(X520), 회피적 캔슬 알아채기(X510).
관통 안전핀: 충동은 끊되 반드시 (a)선을 긋거나 (b)행동 하나를 한다. '수용'이 행동에 안 묶이면 굴종.
`

// 메인이 생성한 구체적 갈등 상황 6개 (현실적·양쪽 입장이 다 일리있게)
const SCENARIOS = [
  { key: 'lover_cancel', title: '연인이 데이트를 또 당일 취소', desc: '사귄 지 1년. 이번 주 토요일 데이트를 금요일 밤에 "회사 일 터졌다, 미안"으로 취소. 이번 달 두 번째. 나(A)는 "또 후순위가 됐다"는 서운함이 폭발 직전. 상대(B)는 진짜로 야근에 몰려 죄책감+억울("나도 잘리게 생겼는데 왜 이걸로")이 동시에. 카톡 "미안 ㅠㅠ 토요일 안 될 거 같아"가 막 떴고 손가락이 답장을 친다.' },
  { key: 'boss_public', title: '상사가 회의에서 남들 앞에 내 보고서를 깠다', desc: '주간회의. 팀장이 내가 밤새 만든 보고서를 두고 "이걸 보고서라고 가져왔어요? 신입도 이것보단 낫겠다"라고 다른 팀원 다 듣는 데서 깠다. 나(A)는 억울+모욕(사실 일정이 촉박했고 자료도 늦게 받음). 팀장(B)은 위에서 깨지고 와서 압박+"쟤가 정신 차려야 한다"는 의도. 다들 내 입을 본다.' },
  { key: 'parent_nag', title: '부모의 "결혼/취업 언제" 잔소리', desc: '명절. 밥상에서 엄마가 "옆집 누구는 벌써 자리 잡았다더라, 너는 언제 사람 구실 하니"라고 친척들 앞에서. 나(A)는 비교+면박에 수치+분노. 엄마(B)는 사실 불안("내가 없으면 쟤 어쩌나")과 사랑을 잔소리로밖에 표현 못 하는 사람. 숟가락 든 손이 떨린다.' },
  { key: 'friend_money', title: '친구가 또 돈을 빌려달라 한다', desc: '친한 친구가 세 번째로 "딱 이번만, 다음 달에 꼭 갚을게"라며 50만원을 빌려달라 한다. 지난번 것도 아직 안 갚음. 나(A)는 거절하면 우정 깨질까/매정할까 죄책감, 빌려주면 또 호구 될 분노가 공존. 친구(B)는 진짜 급하고("카드값 막아야") 미안함+절박. 나는 지금 답을 해야 한다.' },
  { key: 'chores', title: '동거인/배우자와 집안일 분담 다툼', desc: '같이 사는 사이. 내(A)가 또 설거지·빨래·쓰레기를 다 했고 상대(B)는 소파에서 폰. "나만 하잖아"가 터지기 직전. 상대(B)는 "나는 돈을 더 벌고 주말에 운전·고장수리 다 하는데"라고 자기 기여는 안 쳐준다는 억울함. 내가 그릇을 쾅 내려놓으려는 순간.' },
  { key: 'self_collapse', title: '새벽의 자기비하·번아웃 (나 vs 나)', desc: '새벽 2시. 프로젝트 실패+남들과 비교로 "나는 안 되는 인간"이 머릿속에서 자동 재생. 한쪽(A)은 "다 그만두고 싶다, 이불 속에 숨자"는 무너진 나, 다른 쪽(B)은 "이러다 진짜 망한다, 정신 차려 채찍질해"라는 다그치는 나. 둘 다 나라서 더 괴롭다. 폰으로 또 남 SNS를 켜려 한다.' },
]

const DRAMA_SCHEMA = {
  type:'object', additionalProperties:false,
  required:['scenario','side_a','side_b','take1_immature','take2_mature','draft_playbook'],
  properties:{
    scenario:{type:'string'},
    side_a:{type:'object', additionalProperties:false, required:['position','inner_truth','wants'],
      properties:{position:{type:'string'},inner_truth:{type:'string'},wants:{type:'string'}}},
    side_b:{type:'object', additionalProperties:false, required:['position','inner_truth','wants'],
      properties:{position:{type:'string'},inner_truth:{type:'string'},wants:{type:'string'}}},
    take1_immature:{type:'array', minItems:3, items:{type:'string'}, description:'터지는 버전 대사 3~5줄. "화자: 대사 (속마음)" 형식'},
    take2_mature:{type:'array', minItems:3, items:{type:'string'}, description:'성숙 버전 대사 3~6줄. "화자: 대사 (카드ID·왜)" 형식'},
    draft_playbook:{type:'array', minItems:4, items:{type:'object', additionalProperties:false,
      required:['trigger','say','do','card'],
      properties:{trigger:{type:'string'},say:{type:'string'},do:{type:'string'},card:{type:'string'}}}},
  },
}

const FINAL_SCHEMA = {
  type:'object', additionalProperties:false,
  required:['scenario','both_pov','dialogue_immature','dialogue_mature','playbook','accept_vs_submit','lesson_a','lesson_b'],
  properties:{
    scenario:{type:'string'},
    both_pov:{type:'string', description:'양쪽 입장 2~3문장 — 둘 다 옳음이 드러나게'},
    dialogue_immature:{type:'array', items:{type:'string'}, description:'미성숙 2테이크 대사(다듬은 최종)'},
    dialogue_mature:{type:'array', items:{type:'string'}, description:'성숙 2테이크 대사(다듬은 최종, 카드ID 포함)'},
    playbook:{type:'array', minItems:4, items:{type:'object', additionalProperties:false,
      required:['trigger','say','do','card'],
      properties:{
        trigger:{type:'string', description:'구체적 신호(언제). 추상 금지'},
        say:{type:'string', description:'★입 밖으로 낼 정확한 대사. "구체적으로 말한다"같은 추상 금지, 실제 따옴표 문장'},
        do:{type:'string', description:'★몸으로 하는 정확한 동작(호흡·시선·자리·폰 등). 실제 동작'},
        card:{type:'string', description:'근거 카드ID'},
      }}},
    accept_vs_submit:{type:'string', description:'이 상황에서 수용(성숙)과 굴종(자기억압)을 가르는 선 한 문장 — 양쪽에 다'},
    lesson_a:{type:'string', description:'A에게 한 줄'},
    lesson_b:{type:'string', description:'B에게 한 줄'},
  },
}

const dramaPrompt = (s)=>`너는 현실적인 갈등을 생생하게 극화하는 작가다. 아래 상황을 양쪽 입장이 둘 다 일리있게 살려 상황극으로 써라.

## 상황
${s.title} — ${s.desc}

## 어른스러움 프레임 (성숙 버전에 적용)
${FRAMEWORK}

## 할 일
1. side_a / side_b: 양쪽의 입장·속마음·진짜 원하는 것. **둘 다 악당이 아니게, 각자 옳게.**
2. take1_immature: 실제로 이렇게 터지는 대사 3~5줄. 각 줄 "A: 대사 (속마음/실패한 무브)".
3. take2_mature: 같은 장면이 프레임으로 풀리는 대사 3~6줄. 각 줄 "A: 대사 (적용 카드ID·왜)". A쪽·B쪽 둘 다의 성숙한 수를 보여라.
4. draft_playbook: 이 상황의 trigger→say(정확한 대사)→do(몸동작)→card 4개+. **say는 실제 입으로 낼 따옴표 문장, do는 실제 몸동작. 추상어 금지.**
스키마(StructuredOutput)로 반환.`

const coachPrompt = (s,draft)=>`너는 깐깐한 현실 코치다. 아래 상황극 초벌을 받아 **세상에서 제일 구체적이고 바로 따라 할 수 있는** 플레이북으로 다듬어라. 추상은 전부 죽여라.

## 상황
${s.title} — ${s.desc}

## 초벌 (개선 대상)
${JSON.stringify(draft, null, 2)}

## 할 일
1. both_pov: 양쪽 다 옳음을 2~3문장으로.
2. dialogue_immature / dialogue_mature: 초벌 대사를 더 진짜처럼 다듬어 최종본으로(성숙본엔 카드ID 유지).
3. playbook: 초벌을 다듬어 4~6행. 기준은 단 하나 — **"say는 그대로 읽으면 되는 실제 대사, do는 그대로 하면 되는 실제 몸동작."** "차분히 말한다" "감정을 조절한다" 같은 추상은 전부 구체 대사·동작으로 교체하거나 잘라라. 비현실적인 멋부린 대사도 잘라라(실제로 그렇게 말 안 함).
4. accept_vs_submit: 이 상황에서 수용(성숙)과 굴종(참고 삼킴)을 가르는 선 한 문장.
5. lesson_a / lesson_b: 양쪽에게 한 줄씩.
핵심: "실제로 그 순간 이 문장을 말하고 이 동작을 할 수 있는가?"만 통과시켜라. 스키마(StructuredOutput)로 반환.`

phase('극화')
const results = await pipeline(
  SCENARIOS,
  (s)=>agent(dramaPrompt(s), {schema:DRAMA_SCHEMA, phase:'극화', label:`극화:${s.key}`}),
  (draft,s)=>agent(coachPrompt(s,draft), {schema:FINAL_SCHEMA, phase:'구체화', label:`구체화:${s.key}`})
    .then((final)=>({key:s.key, title:s.title, final})),
)
const ok = results.filter(Boolean)
log(`상황극 ${ok.length}/${SCENARIOS.length} 구체화 완료`)
return { scenarios: ok }
