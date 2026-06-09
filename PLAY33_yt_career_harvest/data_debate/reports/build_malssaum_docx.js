// Build malssaum_playbook.docx from the markdown playbook.
// Goal: keep ALL information density (every card ID + quote), but make it
// easy to read via plain-language glosses and colored callout boxes.

const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, LevelFormat, TableOfContents, HeadingLevel, BorderStyle,
  WidthType, ShadingType, PageNumber, PageBreak, Header, Footer,
} = require("docx");

// ---------- palette ----------
const INK = "1A1A1A";
const MUTED = "5A5A5A";
const ACCENT = "2E5BBA";      // headings / rules
const BODY_SIZE = 22;         // 11pt
const CONTENT_W = 9360;       // US Letter, 1" margins

// box fills
const FILL_GLOSS = "FFF4D6";   // soft amber — 쉽게 말하면
const FILL_EVID  = "EAF1FB";   // soft blue  — 근거
const FILL_MIC   = "E5F4E7";   // soft green — 실전 멘트
const FILL_WARN  = "FBE9E7";   // soft red   — 약점/주의
const FILL_HEAD  = "D5E3F7";   // table header

// ---------- helpers ----------
const runs = (parts) =>
  parts.map((p) =>
    typeof p === "string"
      ? new TextRun({ text: p, size: BODY_SIZE, color: INK })
      : new TextRun({ size: BODY_SIZE, color: INK, ...p })
  );

const para = (parts, opts = {}) =>
  new Paragraph({
    children: Array.isArray(parts) ? runs(parts) : runs([parts]),
    spacing: { after: 120, line: 288 },
    ...opts,
  });

// A shaded callout block (paragraph-based, compact) with a colored left bar
// and a bold label line. Returns an ARRAY of paragraphs (spread at call site).
function callout(fill, label, labelColor, bodyParts) {
  const shading = { fill, type: ShadingType.CLEAR };
  const leftBar = { left: { style: BorderStyle.SINGLE, size: 18, color: labelColor, space: 6 } };
  const out = [];
  out.push(
    new Paragraph({
      shading,
      border: leftBar,
      indent: { left: 120 },
      spacing: { before: 60, after: 40, line: 264 },
      children: [new TextRun({ text: label, bold: true, size: BODY_SIZE, color: labelColor })],
    })
  );
  bodyParts.forEach((bp, i) =>
    out.push(
      new Paragraph({
        shading,
        border: leftBar,
        indent: { left: 120 },
        spacing: { after: i === bodyParts.length - 1 ? 120 : 60, line: 276 },
        children: runs(bp),
      })
    )
  );
  return out;
}

const spacer = (after = 120) => new Paragraph({ spacing: { after }, children: [] });

// Render one "move": number+title heading, gloss, full explanation, evidence, mic, warn.
function move(m) {
  const out = [];
  out.push(
    new Paragraph({
      heading: HeadingLevel.HEADING_3,
      spacing: { before: 200, after: 80 },
      children: [
        new TextRun({ text: m.tag + "  ", bold: true, size: 24, color: ACCENT }),
        new TextRun({ text: m.title, bold: true, size: 24, color: INK }),
      ],
    })
  );
  if (m.gloss)
    out.push(...callout(FILL_GLOSS, "쉽게 말하면", "9A6700", [[{ text: m.gloss, italics: true }]]));
  if (m.body) out.push(para(m.body));
  if (m.evidence) out.push(...callout(FILL_EVID, "근거 · 실제 인용", "1E4FA0", m.evidence));
  if (m.mic) out.push(...callout(FILL_MIC, "🎯 실전 멘트", "1F7A33", [m.mic]));
  if (m.warn) out.push(...callout(FILL_WARN, "⚠️ 약점 · 이렇게 풀린다", "B23B2E", [m.warn]));
  out.push(spacer(60));
  return out;
}

// section title with colored underline rule
function sectionTitle(text, sub) {
  const arr = [
    new Paragraph({
      heading: HeadingLevel.HEADING_1,
      pageBreakBefore: true,
      spacing: { before: 0, after: 60 },
      border: { bottom: { style: BorderStyle.SINGLE, size: 18, color: ACCENT, space: 4 } },
      children: [new TextRun({ text, bold: true, size: 36, color: ACCENT })],
    }),
  ];
  if (sub)
    arr.push(
      new Paragraph({
        spacing: { after: 160, line: 276 },
        children: [new TextRun({ text: sub, italics: true, size: 22, color: MUTED })],
      })
    );
  return arr;
}

// ============================================================
// CONTENT
// ============================================================

// ---- Section ① 잘하는 법 ----
const sec1 = [
  {
    tag: "①-1",
    title: "정의 추출 → 그 정의에 가두기",
    gloss: "핵심 단어의 뜻을 내가 정하지 말고 상대에게 먼저 정의하게 시켜라. 그 다음부터는 그 사람이 만든 자(尺)로만 모든 걸 잰다. 자기가 만든 기준에 걸리면 빠져나갈 명분이 없다.",
    body: "상대에게 핵심어를 먼저 정의하게 시킨 뒤, 그 정의로 상대의 모든 답을 심판한다. 자기가 만든 기준에 묶이면 도망갈 핑계가 사라진다.",
    evidence: [
      [{ text: "(E401) Greenwald: " }, { text: "“what makes a peacemaking president? ... so you agree that prevention is a part of it.”", italics: true }],
      [{ text: "(D107): " }, "“내가 말하는 ‘온전한’이란 ~입니다”처럼 형용사를 직접 정의해 기준을 선점."],
    ],
    mic: ["“잠깐, ‘OO’를 정확히 뭐라고 정의하고 쓰는 거예요? 그거부터 정하죠.”"],
    warn: ["상대가 한 줄 정의를 거부하고 내 핵심어를 역으로 정의해버리면 프레임을 빼앗긴다."],
  },
  {
    tag: "①-2",
    title: "핀 박고 → 기준 갈아치우기",
    gloss: "먼저 숫자처럼 명확한 걸로 못을 박아 주도권을 잡는다. 상대가 답을 내놓는 순간, 측정 불가능한 축(가치·도덕)으로 전장을 옮겨 방금 그 답을 무의미하게 만든다.",
    body: "측정 가능한 것으로 먼저 못 박아 주도권을 잡고, 답이 나오는 순간 측정 불가능한 축으로 전장을 옮긴다.",
    evidence: [
      [{ text: "(E501) Kirk: " }, "viability(숫자)로 핀을 박고 즉시 ‘moral worth’로 이동해 앞의 답을 무의미화."],
      [{ text: "(D309): " }, "“단기 가격 → 장기 가치”로 비교축을 갈아탐."],
    ],
    mic: ["“그 숫자는 인정. 근데 진짜 쟁점은 [새 기준]이죠.”"],
    warn: ["“방금 그거 물어놓고 왜 딴 걸로 옮기냐”고 골대 이동을 지적당하면 역공당한다."],
  },
  {
    tag: "①-3",
    title: "상대 전제를 받아 방향만 튼다 (rebuttal judo) — 최다·최강",
    gloss: "새 논거를 찾지 마라. 상대가 방금 인정한 그 전제를 그대로 받아서 “맞아, 그러니까 오히려…”로 결론만 뒤집는다. 코퍼스 전체에서 가장 많이(24장) 나오고 승률도 가장 높은 무브. 상대 입에서 나온 걸 쓰니 반박 자체가 자기모순이 된다.",
    body: "상대가 방금 인정한 전제를 집어 결론만 역전시킨다. 새 논거가 필요 없어 반박이 거의 불가능하다. 이 책 전체에서 가장 강한 단 하나의 무브.",
    evidence: [
      [{ text: "(E507) Naima: " }, "“집단 편애는 나쁘다”를 받아 ", { text: "“that’s why it’s important to have representation that is diverse”", italics: true }, "로 역전."],
      [{ text: "(E402) Greenwald: " }, "“전쟁을 끝냈다”를 인정하되 자해 비유로 프레임만 재구성."],
    ],
    mic: ["“그 말 맞아요. 근데 그게 사실은 제 결론을 증명하는데요?”"],
    warn: ["상대가 ‘기술(describe) ≠ 옹호(endorse)’로 전제와 결론을 다시 분리하면 풀린다."],
  },
  {
    tag: "①-4",
    title: "입증책임 전가 + 강제 이분법 + 안 놔주기",
    gloss: "“내 주장이 기본값이고, 반대하려면 네가 증명해”로 판을 깐다. 그리고 정직하게 답하면 곧 내 말을 인정하게 되는 예/아니오 질문을 계속 들이민다.",
    body: "“내 명제가 기본값, 반대하면 네가 증명”으로 세팅하고, 정직하면 곧 인정이 되는 예/아니오를 계속 들이민다.",
    evidence: [
      [{ text: "(E404) Greenwald: " }, { text: "“Were we at war when Trump was inaugurated? ... So he made that war, right?”", italics: true }],
      [{ text: "(E503) Kirk: " }, "“왜 시민권법 이후에 나빠졌는지 네가 설명해.”"],
      [{ text: "(E517) Mehdi: " }, "핵 타임라인을 깔고 “이 날짜를 설명하라.”"],
    ],
    mic: ["“예/아니오로요. — 그럼 그건 당신이 증명할 차례죠.”"],
    warn: ["“표 수·직관은 공리가 아니다, 내용으로 논증하라”며 틀 자체를 거부당하면 무력. 받되 메커니즘을 즉시 공급하고 되받아 닫는다 (E505)."],
  },
  {
    tag: "①-5",
    title: "퇴로를 상대의 *이전 발언*으로 막는다",
    gloss: "상대가 정의를 흐리며 도망가려 하면, 새로 반박하지 말고 그 사람이 처음에 한 답을 그대로 들이민다. 지금 말을 바꾸는 게 곧 자기모순으로 드러난다.",
    body: "상대가 정의를 흐리며 도망가면, 새 반박 대신 본인이 처음 한 답에 핀을 박아 재정의를 자기모순으로 노출시킨다.",
    evidence: [
      [{ text: "(E405) Greenwald: " }, { text: "“as you said the first time when I asked you.”", italics: true }],
      [{ text: "(D117): " }, "토씨 안 틀리게 인용해 “제가 언제 그랬어요” 발뺌을 차단."],
    ],
    mic: ["“방금 전엔 X라고 했잖아요. 지금 말 바꾸는 거예요?”"],
    warn: ["녹취·정확한 기억이 없으면 인용 자체를 부인당한다."],
  },
  {
    tag: "①-6",
    title: "버즈워드 정의 요구로 멈춰 세우기",
    gloss: "그럴듯한 전문용어가 전제로 슬쩍 깔리려는 순간 “그게 무슨 뜻이냐”고 물어 오용·공허함을 드러낸다. 자신만만하던 단정이 더듬거림으로 바뀐다.",
    body: "그럴듯한 전문용어가 전제로 깔리려는 순간 뜻을 물어 공허함을 드러낸다.",
    evidence: [
      [{ text: "(E208) Destiny: " }, { text: "“What does landlocked economy mean?”", italics: true }, " — 자신만만한 단정을 더듬거림으로 전환."],
      [{ text: "역으로 내가 쓸 땐 " }, "적확한 한자 법률어로 (D110)."],
    ],
    mic: ["“‘OO’가 정확히 무슨 뜻이죠? 풀어서요.”"],
  },
  {
    tag: "①-7",
    title: "무서운 단어를 직접 정의시켜 무력화 (문자 시험)",
    gloss: "상대가 던진 강한 라벨을 글자 그대로 시험한다. “그 단어가 진짜 그 뜻이면 [극단 사례]여야 하는데, 그게 돼요?” — 과장임이 드러나며 상대가 스스로 자백한다.",
    body: "상대의 강한 라벨을 문자 그대로 시험해 과장임을 드러낸다.",
    evidence: [
      [{ text: "(E515) Mehdi: " }, { text: "“Open border means I could just walk into America. Nobody could do that.”", italics: true }, " → (E516) “그럼 열린 국경은 없었다는 거네”로 자백을 받음."],
    ],
    mic: ["“‘OO’? 문자 그대로면 [극단 사례]여야 하는데, 그게 돼요?”"],
  },
  {
    tag: "①-8",
    title: "기준/좌표계를 내가 먼저 깐다",
    gloss: "결론을 강요하지 마라. 그 결론이 나올 수밖에 없는 판단축을 먼저 깔면, 상대가 그 위에서 스스로 결론을 내리고 “내가 판단했다”고 느낀다. 강요보다 훨씬 강하다.",
    body: "결론을 강요하지 않고, 그 결론이 나올 수밖에 없는 판단축을 먼저 깐다. 상대가 그 위에서 스스로 결론에 도달한다.",
    evidence: [
      [{ text: "(D301) 박강사: " }, "“A기준이면 B, C기준이면 추천 안 함… 사라고 말하지 않는다.”"],
      [{ text: "(E617) Haqiqatjou: " }, "척도(평화의 양)를 선점해 상대를 그 척도 위에서 패배시킴."],
    ],
    warn: ["“왜 그 기준이 맞냐”고 정당성을 되물으면 무너진다."],
  },
  {
    tag: "①-9",
    title: "함정은 이름 붙여 깨고, 상대가 쓰기 전에 선제 면역",
    gloss: "gish gallop(말 폭탄)·motte-and-bailey·거짓 이분법 같은 수법은 소리 내어 이름을 붙이는 순간 힘을 잃는다. 내가 받을 비판도 미리 스스로 이름 붙여 면역시킨다.",
    body: "gish gallop·motte-and-bailey·거짓 이분법은 소리 내어 명명하는 순간 힘을 잃는다.",
    evidence: [
      [{ text: "(E604) Dean: " }, "말 폭탄을 호명한 뒤 직렬로 하나씩 처리."],
      [{ text: "(E518) Mehdi: " }, "받을 비판(no-true-Scotsman)을 스스로 명명해 면역."],
    ],
    warn: ["명명만으론 부족하다 — 명명 후 실제로 점을 하나씩 닫아야 한다."],
  },
];

// ---- Section ② 잘 긁는 법 ----
const sec2 = [
  {
    tag: "②-1",
    title: "페이스 강탈 — 상대가 빨라질수록 나는 더 느리게",
    gloss: "사람은 무의식적으로 상대 템포에 맞추려 한다. 속사포로 쏘아대도 내가 따라가지 않으면 상대 혼자 공회전하며 제 페이스에 말린다.",
    body: "사람은 상대 호흡·템포에 동기화하려는 경향이 있다. 내가 안 따라가면 상대 혼자 공회전한다.",
    evidence: [
      [{ text: "(D214): " }, "“사람은 호흡에 맞춰 가려는 경향… 우리 속도대로 천천히… 상대는 자기 페이스에 말리게.”"],
    ],
    mic: ["상대가 속사포로 쏘면 한 박자 늦춰 “음… 천천히 가죠.”"],
    warn: ["과하면 깔보는 연출처럼 보여 역효과."],
  },
  {
    tag: "②-2",
    title: "무브를 소리내어 명명하기 (망신 주기) — ⭐가장 안전",
    gloss: "상대의 수법(말 폭탄·화제 전환)에 이름을 붙여 공개하면, 청중 앞에서 그 수법이 무력화되고 상대는 ‘들킨 사람’이 된다. 긁기 중 제일 안전하고 효율 높다 — 인신공격도 거짓도 없이 상대의 실제 행동만 짚으니까.",
    body: "상대의 수법을 이름 붙여 공개하면 청중 앞에서 무력화되고 상대는 들킨 사람이 된다. 긁기 중 가장 안전.",
    evidence: [
      [{ text: "(E604): " }, "“한꺼번에 던져 압도하려는 거죠… 하나씩 갈게요.”"],
      [{ text: "(E606): " }, "화제 전환을 ", { text: "“It’s a pivot”", italics: true }, "으로 미리 까발려 도주로 차단."],
    ],
    mic: ["“지금 한 번에 다섯 개 던져서 하나씩 못 보게 하는 거죠? 하나씩 갑시다.”"],
    warn: ["명명이 빗나가면 피해망상처럼 보인다. 매번 라벨을 붙이면 메타게임만 한다는 인상."],
  },
  {
    tag: "②-3",
    title: "일관성/대칭 함정 — 모순을 들춰 쩔쩔매게",
    gloss: "상대가 자기 진영엔 안 적용하는 기준을, 그 사람 편에도 똑같이 대칭으로 들이댄다. 위선이 드러나면 변명 모드로 밀려나며 평정을 잃는다.",
    body: "상대가 자기 진영엔 안 쓰는 기준을 대칭으로 들이대 위선을 노출한다.",
    evidence: [
      [{ text: "(E309): " }, "“네 편이 지면 그 사람 탓, 버니가 지면 언론 탓.”"],
      [{ text: "(E406): " }, "“트럼프엔 전쟁이라 정의하고 바이든엔 아니라고?”"],
    ],
    mic: ["“그 기준 네 편에도 똑같이 대면 어떻게 돼?”"],
    warn: ["상대가 정당한 비대칭(거짓 vs 진실)을 제시하면 풀린다."],
  },
  {
    tag: "②-4",
    title: "가상 캐릭터 조롱 (인신공격 회피하며 긁기)",
    gloss: "사람을 직접 까지 말고 별명·캐릭터·패러디로 조롱한다. ‘인신공격’ 비난을 피하면서 흔들 수 있다. 단 — 사람이 아니라 논리를 캐릭터화해야 안전하다.",
    body: "사람을 직접 까지 말고 별명·캐릭터로 조롱해 인신공격 비난을 피하며 흔든다.",
    evidence: [
      [{ text: "(M708): " }, "진행자를 ‘정명보 감독’으로 캐릭터화해 내내 콜백."],
      [{ text: "(M416): " }, "비호감 화법을 일상에 과장 이식(“된장찌개 온보딩”)."],
    ],
    warn: ["가장 찌질해 보이기 쉬운 구역. 악의적이면 청중이 표적에 동정한다. 사람이 아니라 논리를 캐릭터화해야 안전."],
  },
  {
    tag: "②-5",
    title: "I-메시지로 동요시키기",
    gloss: "맞받아 비난하지 말고 “나는 네가 그렇게 말한 게 마음이 아프네”처럼 내 감정만 던진다. 화난 상대는 받아칠 표적을 잃고 흔들린다.",
    body: "맞비난 대신 내 감정만 던지면, 화난 상대도 받아칠 표적을 잃고 흔들린다.",
    evidence: [
      [{ text: "(D215): " }, "“나는 너가 그런 말 한 게 마음이 아프네… 화내던 상대도 동요.”"],
      [{ text: "(D216): " }, "“그래, 그랬구나 / 어쩌라고” — 맞비난을 끊어 도발 연료를 차단."],
    ],
    warn: ["진정성 없이 기법으로만 쓰면 ‘감정팔이’로 역공. 논점을 이기는 게 아니라 분위기만 무력화하는 수."],
  },
  {
    tag: "②-6",
    title: "톤·경멸 연출 — 끝을 떨어뜨리고 낮게",
    gloss: "화날 때 문장 끝을 올리지 말고 떨어뜨려 저음으로 간다. 동요 없이 단호해 보인다.",
    body: "화날 때 문장 끝을 떨어뜨려 저음으로 가면 동요 없이 단호해 보인다.",
    evidence: [
      [{ text: "(D111): " }, "“‘짜증나’ 뒤를 떨어뜨리는 거예요.”"],
      [{ text: "보조 (E104) Destiny: " }, "피아노 + “filibuster” 경멸 연출 — 단, 역효과 사례(상대가 “답변을 회피로 매도한다”고 되받음)."],
    ],
    warn: ["단조로운 저음은 무성의로 비친다. 경멸 연출은 명명당하면 내가 회피하는 쪽으로 뒤집힌다."],
  },
  {
    tag: "②-7",
    title: "“감정적이네” 라벨 — 그리고 깨는 법",
    gloss: "상대에게 “감정적이네” 라벨을 붙이면 그 주장이 통째로 무력화돼 보인다. 가장 야비한 수. 반대로 내가 당했을 땐 즉시 법적·단정 어미로 갈아타 무효화한다.",
    body: "라벨을 붙이면 상대 주장이 통째로 무력화돼 보인다. 당했을 때는 감정어를 버리고 법적·단정 어미로 갈아타면 무효화된다.",
    evidence: [
      [{ text: "(E312) Kirk: " }, "상대를 “넌 그냥 이기고 싶을 뿐 / 음악 전공”으로 동기·자격에 가둠."],
      [{ text: "(되받기) (D112): " }, "감정어를 버리고 “~입니다 / ~입니까”만 사용."],
    ],
    warn: ["가장 야비해 보이는 수 — 근거 없으면 “본론 말고 사람 까네”로 역풍(E312에서 상대가 바로 이렇게 받아침)."],
  },
];

// ---- Section ③ 말 없게 만드는 법 ----
const sec3 = [
  {
    tag: "③-1",
    title: "각주/근거 Gotcha — 상대가 댄 출처를 그 출처로 죽인다",
    gloss: "상대가 “이건 믿을 만한 출처”라고 자기 근거를 내세우면, 그 페이지·각주를 직접 따라가 “그 출처가 스스로 이걸 약하다(weak)고 등급 매겼다”고 읽어준다. 반박 대상이 상대 자신의 인용이라 변명할 표면이 없다.",
    body: "상대가 내세운 출처의 각주를 따라가, 그 출처가 스스로 자기 주장을 약하게 평가했음을 읽어준다.",
    evidence: [
      [{ text: "(E414, David Wood): " }, { text: "“The report that Korah just said is authentic is actually weak.”", italics: true }],
    ],
    mic: ["“그 자료 좋아요. 근데 각주 4번 보셨어요? 직접 읽어볼게요.”"],
    warn: ["상대가 등급을 함께 인용해뒀거나 admissibility를 따로 논증할 줄 알면 무너진다."],
  },
  {
    tag: "③-2",
    title: "정확한 인용으로 발뺌 차단 — 상대의 직전 발언에 못 박기 ⭐최강",
    gloss: "상대가 “정의에 따라 다르다”로 도망가면, “아까 처음 내가 물었을 때 당신이 한 답대로 가죠”로 되박는다. 5분 전 자기 입으로 한 말이 들이밀어지면, 지금 정의 흐리는 게 곧 자기모순이 된다. 영어·한국 코퍼스가 독립적으로 ‘가장 강한 피니셔’로 꼽은 단 하나.",
    body: "상대가 정의를 흐리며 도망가면, 처음에 한 답을 정확히 인용해 되박는다. 자기 입으로 한 말이라 반박하려면 자기모순을 자백해야 한다.",
    evidence: [
      [{ text: "(E405, Greenwald): " }, { text: "“As you said the first time when I asked you.”", italics: true }],
      [{ text: "(D117, 흥버튼): " }, "“정확히 인용해야 ‘제가 언제 그랬어요’를 막는다.”"],
      [{ text: "(D213, 신카일): " }, "“경청하며 모순 채집.”"],
    ],
    mic: ["“근데 너 아까는 ○○라고 했잖아.”"],
    warn: ["녹취·기억이 없으면 인용 자체를 부인당한다. 상대가 “그땐 말을 다듬은 거고 지금이 정확한 입장”이라 선 그으면 약해진다."],
  },
  {
    tag: "③-3",
    title: "출처 없는 주장 폭로 — John Smith 함정",
    gloss: "상대가 근거 없이 주장하면, 가짜 디테일(존재하지 않는 이름)을 슬쩍 끼워 받아준 뒤 “그 이름, 방금 내가 지어냈어요”로 까발린다. 증거를 쥐기도 전에 주장부터 했다는 게 그 자리에서 입증된다.",
    body: "상대가 근거 없이 주장하면 가짜 디테일을 끼워 받아준 뒤 지어낸 것임을 폭로해, 증거 없이 주장부터 했음을 입증한다.",
    evidence: [
      [{ text: "(E108, Ryan): " }, { text: "“A man named John Smith... I just made that name up.”", italics: true }],
    ],
    mic: ["상대가 “사례 많아요” → “하나만 이름·날짜 대보세요.” 못 대면 끝."],
    warn: ["상대가 실제 레코드를 갖고 있으면(E108에서 나중에 Enforcement Act 1870을 꺼냄) 역으로 망신. 정말 비어 있을 때만 쓴다."],
  },
  {
    tag: "③-4",
    title: "자기모순 즉석 노출 — 두 입장을 나란히",
    gloss: "동시에 붙들 수 없는 두 명제를 한 문장에 나란히 놓아 충돌시킨다. “이란인은 죽음을 원하는 광신도다 — 그런데 종전 협상 테이블에 앉아 있다. 죽고 싶은 자가 왜 전쟁을 끝내려 하나?”",
    body: "동시에 못 붙드는 두 명제를 한 문장에 놓아 충돌시킨다.",
    evidence: [
      [{ text: "(E412, Greenwald): " }, "“이란인은 죽음을 원한다면서 왜 종전 협상에 앉아 있나?”"],
      [{ text: "(E303, Contrapoints): " }, "“제3당 표가 결정적이 아니라며, 그 협박이 먹히려면 결정적이어야 하잖아?”"],
    ],
    mic: ["“방금 A라 했고 좀 전엔 not-A라 했어요. 둘 중 뭐예요?”"],
    warn: ["상대가 두 명제를 구분 범주로 쪼개면 빠져나간다(E303 counter). 진짜 모순인지 층위가 다른지 먼저 확인."],
  },
  {
    tag: "③-5",
    title: "골대 옮김 잡아 인정 못박기 — Concession-Lock",
    gloss: "상대가 강한 주장(“국경 열림”)에서 약한 주장(“숫자만 늘었음”)으로 후퇴하는 순간, “그럼 ‘열린 국경’은 없었다는 데 동의하는 거네요”로 도장을 찍는다. 안 잠그면 곧장 강한 주장으로 복귀한다.",
    body: "상대가 강 → 약으로 후퇴하는 순간 그 후퇴를 인정으로 못 박는다. 안 잠그면 강한 주장으로 되돌아간다.",
    evidence: [
      [{ text: "(E516, Mehdi): " }, { text: "“So then we agree there wasn’t an open border.”", italics: true }],
    ],
    mic: ["상대가 한발 빼면 “그럼 아까 그 말은 취소죠?”"],
    warn: ["“정책상 openness는 없었지만 실질적으로 열렸다”로 강/약을 다시 묶으면 빠진다."],
  },
  {
    tag: "③-6",
    title: "현실 대조 질문 — “그래서 바뀐 게 있나요?”",
    gloss: "추상적 명분엔 구체적 변화·메커니즘·타임라인을 요구한다. 명분만 있고 경로가 없으면 그 자리에서 텅 빈 게 보인다.",
    body: "추상 명분에 구체적 변화·메커니즘·타임라인을 요구한다. 경로가 없으면 비어 보인다.",
    evidence: [
      [{ text: "(E304, Contrapoints): " }, { text: "“What is the theory of change? On what timeframe?”", italics: true }],
      [{ text: "(E607, Dean): " }, "“장점을 수치로 하나만 itemize.”"],
    ],
    mic: ["“구체적으로 뭐가 달라져요? 언제까지요?”"],
    warn: ["상대가 같은 burden을 되던지면 무승부(E304). 진짜 로드맵을 가졌으면 오히려 발언권을 헌납하는 셈."],
  },
  {
    tag: "③-7",
    title: "강제 이분법 — 정직한 답이 곧 항복인 yes/no",
    gloss: "어느 쪽으로 답해도 내 명제를 인정하게 되는 양자택일을 던지고, 회피성 부연은 ‘회피’로 읽으며 놔주지 않는다.",
    body: "어느 쪽이든 내 명제를 인정하는 binary를 던지고, 회피성 부연을 회피로 읽으며 안 놔준다.",
    evidence: [
      [{ text: "(E404, Greenwald): " }, { text: "“Were we at war when Trump was inaugurated?”", italics: true }],
    ],
    warn: ["영리한 상대는 이분법 자체를 거부한다(“둘 중 하나로 답할 게 아니다”, E611/E610). 진짜 제3의 답이 있으면 안 통하고 강압적으로 비친다."],
  },
  {
    tag: "③-8",
    title: "‘감정적’ 라벨 무효화 — 어미를 법률 단정으로",
    gloss: "“감정적이시네”로 무력화당하면, 감정어를 통째로 버리고 “~입니다 / ~입니까” + 정확한 법률·전문 용어로만 말한다. 라벨이 즉시 무효가 되고 상대가 변명 모드로 들어간다.",
    body: "감정 라벨로 무력화당하면 감정어를 버리고 단정 어미 + 정확한 전문용어로 전환한다.",
    evidence: [
      [{ text: "(D112, 흥버튼): " }, "“이건 갑의 횡포입니다… 계약 위반입니다.”"],
      [{ text: "(D110): " }, "“돈 깎아요?”가 아니라 “부당대금감액”. + 톤은 끝 내림(D111)."],
    ],
    warn: ["근거(실제 위반)가 없으면 공허한 위협, 용어를 오용하면 허세로 역공당한다."],
  },
  {
    tag: "③-9",
    title: "자해 비유 한 방 — 사실은 인정, 의미를 다시 칠한다",
    gloss: "상대가 댄 사실은 부정하지 말고 그대로 받아들인 뒤, 그림이 그려지는 비유 하나로 그 사실의 의미를 재구성해 머리에 박는다.",
    body: "상대의 사실은 받아들인 뒤, 한 장면 비유로 의미를 재구성해 각인시킨다.",
    evidence: [
      [{ text: "(E402, Greenwald): " }, { text: "“I stabbed myself... then brought myself to the ER... that proves I’m interested in self-care.”", italics: true }],
    ],
    mic: ["“맞아요. 근데 그게 사실은 이런 뜻이죠 —” + 한 장면 비유."],
    warn: ["상대가 baseline을 부정하면(이미 분쟁 상태였다) 비유의 전제가 무너진다."],
  },
];

// ---- cheat sheet rows ----
const cheat = [
  ["시작·아무 때나", "핵심어를 상대에게 정의시키고 그 정의에 가두기", "①1 (E401/D107)"],
  ["상대가 전제를 인정함", "“맞아, 그러니까 오히려…” 받아 뒤집기", "①3 (E507/E402)"],
  ["“경우에 따라 다르다”로 도망", "“아까는 ○○라고 했잖아” 직전 발언 핀", "③2 (E405/D117)"],
  ["무서운 단어로 겁줌", "“그게 정확히 무슨 뜻인데?” 정의 요구/문자시험", "①6·7 (E208/E515)"],
  ["말 폭탄(gish gallop)", "“하나씩 보죠” 명명 + 직렬 처리", "①9·②2 (E604)"],
  ["상대가 흥분/속사포", "나는 더 느리게, 끝 톤 내려서", "②1·6 (D214/D111)"],
  ["위선/이중잣대", "같은 기준을 네 편에도 대칭으로", "②3 (E309)"],
  ["욕/인신공격 받음", "I-메시지 “그 말 들으니 좀 그러네”", "②5 (D215)"],
  ["명분만 있고 알맹이 없음", "“그래서 뭐가 바뀌어요? 언제까지?”", "③6 (E304)"],
  ["출처 없이 주장", "“이름·날짜 하나만 대보세요”", "③3 (E108)"],
  ["강→약 주장으로 후퇴", "“그럼 아까 그 말은 취소죠?” 못박기", "③5 (E516)"],
  ["“감정적이네” 라벨 당함", "감정어 버리고 “~입니다/~입니까” 단정", "③8 (D112)"],
];

// ============================================================
// BUILD
// ============================================================
const children = [];

// --- cover ---
children.push(
  new Paragraph({ spacing: { before: 1200, after: 0 }, children: [] }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 80 },
    children: [new TextRun({ text: "말싸움 플레이북", bold: true, size: 64, color: ACCENT })],
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 400 },
    children: [new TextRun({ text: "잘하는 법 · 잘 긁는 법 · 말 없게 만드는 법", size: 30, color: MUTED })],
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 60, line: 300 },
    children: [new TextRun({ text: "토론 카드 163장에서 추출한 실전 기술 집대성", size: 24, color: INK })],
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 1000, line: 300 },
    children: [new TextRun({ text: "영어 실시간 토론 99장 (E_b1~6) · 한국 설득·말싸움 64장 (D_b1~4) · 대화 코퍼스 보너스 (M_b*)", size: 20, color: MUTED })],
  })
);

// warning box on cover
children.push(
  ...callout(FILL_WARN, "⚠️ 먼저 읽을 것 — 이 책의 한계", "B23B2E", [
    [{ text: "출처 영상 다수가 “owns / destroys”식 편집이라 “이겼다(won)”가 실제 승리는 아니다. 편집된 클립의 청중 장악이지 진짜 논파가 아닐 때가 많다." }],
    [{ text: "그러므로 이 책은 무용담 따라하기용이 아니라 기술 학습용이다. 특히 ② ‘긁기’는 “남에게 쓰는 법”보다 “당했을 때 알아보는 법”으로 읽어라." }],
    [{ text: "Whisper 화자분리가 없어 발언 귀속은 추론이다. 인용은 기술의 형태를 보여주는 예시로 받아들일 것." }],
  ])
);

// --- TOC ---
children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(
  new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { after: 120 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 18, color: ACCENT, space: 4 } },
    children: [new TextRun({ text: "목차", bold: true, size: 36, color: ACCENT })],
  })
);
children.push(new TableOfContents("Table of Contents", { hyperlink: true, headingStyleRange: "1-2" }));

// --- 이 책을 읽는 법 ---
children.push(...sectionTitle("이 책을 읽는 법", "세 각도가 어떻게 맞물리는가"));
children.push(
  para("이 플레이북은 같은 토론 기술을 세 각도에서 본다. 세 각도는 따로 노는 게 아니라 하나의 골격에 얹힌다:"),
  new Paragraph({ numbering: { reference: "num", level: 0 }, spacing: { after: 80, line: 288 },
    children: runs([{ text: "① 잘하는 법", bold: true }, " = 안 지는 골격. 판을 지배하고 무너지지 않는 구조."]) }),
  new Paragraph({ numbering: { reference: "num", level: 0 }, spacing: { after: 80, line: 288 },
    children: runs([{ text: "② 잘 긁는 법", bold: true }, " = 상대 흔들기(고위험). 잘못 쓰면 내가 더 찌질해 보인다."]) }),
  new Paragraph({ numbering: { reference: "num", level: 0 }, spacing: { after: 160, line: 288 },
    children: runs([{ text: "③ 말 없게 만드는 법", bold: true }, " = 피니셔(사실은 셋업). 한 방처럼 보이지만 미리 깔아둔 함정의 결과물이다."]) })
);
children.push(
  ...callout(FILL_GLOSS, "한 장으로 요약하면", "9A6700", [
    [{ text: "멋진 한 방이 이기는 게 아니다. 이기는 엔진은 네 개다 — ① 정의·기준을 먼저 깐다, ② 끝까지 듣고 기억한다, ③ 틈을 미리 찾는다, ④ 안 흔들린다. 화려한 피니셔보다 ‘골격 + 끝까지 듣고 기억하기’가 가장 안 털리는 길이다.", italics: true }],
  ])
);
children.push(spacer(80));
children.push(
  para([
    "각 무브는 ",
    { text: "쉽게 말하면", bold: true, color: "9A6700" },
    "(핵심 직관) → 설명 → ",
    { text: "근거", bold: true, color: "1E4FA0" },
    "(카드ID + 실제 인용) → ",
    { text: "🎯 실전 멘트", bold: true, color: "1F7A33" },
    " → ",
    { text: "⚠️ 약점", bold: true, color: "B23B2E" },
    " 순서로 정리돼 있다. 카드ID(E·D·M으로 시작)는 원본 코퍼스의 근거 카드를 가리킨다.",
  ])
);

// --- Section ① ---
children.push(
  ...sectionTitle(
    "① 잘하는 법 — 이기는 구조",
    "판을 지배하고 안 지는 골격. 163장에서 이긴 수가 거의 다 흘러나오는 자리. 강한 순서로 9개."
  )
);
sec1.forEach((m) => children.push(...move(m)));
children.push(
  ...callout(FILL_GLOSS, "① 한 줄 요약", "9A6700", [
    [{ text: "이기는 골격은 “핵심어를 누가 정의하느냐”로 거의 결판난다. 가장 강한 무브는 #3 rebuttal judo — 새 논거 없이 상대가 방금 인정한 것만으로 결론을 뒤집어 반박 불가능하게 만든다.", italics: true }],
  ])
);

// --- Section ② ---
children.push(
  ...sectionTitle(
    "② 잘 긁는 법 — 도발·흔들기 (고위험 구역)",
    "상대를 감정적으로 흔들어 실수를 끌어내거나 페이스를 뺏는 기술. 잘못 쓰면 내가 더 찌질해 보인다. 강한 순서로 7개."
  )
);
sec2.forEach((m) => children.push(...move(m)));
children.push(
  ...callout(FILL_GLOSS, "② 긁기의 황금률", "9A6700", [
    [{ text: "긁어서 끌어낼 구체적 실수(모순·발뺌·과장)가 보일 때만 긁어라. 단지 화나서, 청중 웃기려고면 참아라. 긁기는 거의 다 “남에게 쓰면 1점, 당해서 알아보면 5점.”", italics: true }],
    [{ text: "제일 안전·고효율: #2 무브 명명하기 (인신공격·거짓 없이 상대의 실제 수법만 짚어 청중이 내 편). #4 캐릭터 조롱·#7 라벨링은 가장 위험 → 마지막 카드로만.", italics: true }],
  ])
);

// --- Section ③ ---
children.push(
  ...sectionTitle(
    "③ 말 없게 만드는 법 — 피니셔",
    "환상부터 깨자. “한 방에 말문 막힘”은 즉흥 천재성이 아니라 미리 깔아둔 함정이다. 강한 순서로 9개."
  )
);
children.push(
  ...callout(FILL_EVID, "피니셔의 본질 — 먼저 알고 들어가라", "1E4FA0", [
    [{ text: "깨끗한 피니셔는 거의 다 셋업의 결과물이다. Greenwald가 정의를 먼저 추출했고(E401), David Wood가 각주를 미리 펴뒀고(E414), Mehdi가 타임라인을 미리 짰기에(E517) 마지막 질문이 결정타가 됐다." }],
    [{ text: "좋은 상대는 답을 갖고 있어 안 막힌다. 그러니 “이 한마디면 끝”이 아니라 “이 틈을 미리 찾아두면 이 한마디가 끝낸다”로 생각하라." }],
  ])
);
children.push(spacer(80));
sec3.forEach((m) => children.push(...move(m)));
children.push(
  ...callout(FILL_GLOSS, "피니셔의 진실", "9A6700", [
    [{ text: "8할은 말솜씨가 아니라 사전 정찰이다 — 각주를 미리 읽고(1·3), 직전 발언을 기억하고(2), 모순쌍·골대 이동을 미리 표시(4·5). 질문은 피니셔가 아니라 셋업이고, 진짜 피니셔는 상대가 자기 입으로 판 함정을 닫는 순간이다.", italics: true }],
    [{ text: "제일 강한 피니셔: #2 직전 발언 핀(E405/D117) — 영어·한국 코퍼스가 독립적으로 같은 결론에 도달한 유일한 피니셔. 전제는 하나 — 끝까지 듣고 기억할 것.", italics: true }],
  ])
);

// --- Cheat sheet ---
children.push(...sectionTitle("한 장 치트시트 — 상황 → 무브", "급할 때 이 표만 봐도 된다."));
const headRow = new TableRow({
  tableHeader: true,
  children: ["이런 상황", "이렇게", "카드"].map((t, i) =>
    new TableCell({
      width: { size: [2900, 4360, 2100][i], type: WidthType.DXA },
      shading: { fill: FILL_HEAD, type: ShadingType.CLEAR },
      margins: { top: 80, bottom: 80, left: 120, right: 120 },
      children: [new Paragraph({ children: [new TextRun({ text: t, bold: true, size: 22, color: INK })] })],
    })
  ),
});
const dataRows = cheat.map((row, ri) =>
  new TableRow({
    children: row.map((cell, ci) =>
      new TableCell({
        width: { size: [2900, 4360, 2100][ci], type: WidthType.DXA },
        shading: { fill: ri % 2 ? "F4F7FC" : "FFFFFF", type: ShadingType.CLEAR },
        margins: { top: 70, bottom: 70, left: 120, right: 120 },
        children: [new Paragraph({ children: [new TextRun({ text: cell, size: 20, color: ci === 2 ? MUTED : INK, bold: ci === 0 })] })],
      })
    ),
  })
);
const cellBorder = { style: BorderStyle.SINGLE, size: 1, color: "C9D6EA" };
children.push(
  new Table({
    width: { size: CONTENT_W, type: WidthType.DXA },
    columnWidths: [2900, 4360, 2100],
    borders: { top: cellBorder, bottom: cellBorder, left: cellBorder, right: cellBorder, insideHorizontal: cellBorder, insideVertical: cellBorder },
    rows: [headRow, ...dataRows],
  })
);

// --- Closing ---
children.push(...sectionTitle("닫는 말 — 진짜 엔진은 한 줄이 아니다", "세 섹션을 관통하는 진실"));
children.push(para([{ text: "멋진 한 방이 이기는 게 아니다.", bold: true }, " 이기는 엔진은 네 개다 —"]));
const engines = [
  ["정의·기준을 먼저 깐다", "①의 거의 전부 = “말싸움의 8할은 정의 장악.”"],
  ["끝까지 듣고 기억한다", "그래야 ③2(직전 발언 핀)·③5(골대 잠금)가 가능하다. 코퍼스가 독립적으로 가장 강하다고 꼽은 게 이거다."],
  ["틈을 미리 찾는다", "피니셔는 즉흥이 아니라 사전 정찰이다."],
  ["안 흔들린다", "② 긁기의 표적이 되지 않는 것. 압박에 평정을 지키면 위 셋을 실행할 인지 여유가 남는다."],
];
engines.forEach(([h, b]) =>
  children.push(
    new Paragraph({
      numbering: { reference: "engine", level: 0 },
      spacing: { after: 100, line: 288 },
      children: runs([{ text: h + " — ", bold: true }, b]),
    })
  )
);
children.push(
  ...callout(FILL_WARN, "정직하게 — ② 긁기는 대부분 역효과다", "B23B2E", [
    [{ text: "영상 속에서도 긁은 쪽이 “회피한다 / 사람 깐다”로 뒤집힌 사례가 더 많았다(E104·E312). 인용된 “won”은 편집된 클립의 청중 장악이지 진짜 논파가 아닐 때가 많다 — 무용담 말고 기술만 가져가라." }],
    [{ text: "제일 안 털리는 길은 화려한 피니셔가 아니라 ① 골격 + “끝까지 듣고 기억하기”다." }],
  ])
);

// --- Appendix ---
children.push(...sectionTitle("부록 — 소스", "이 책의 출처와 한계"));
const srcs = [
  "영어 토론 99장 — data_argue_en/cards/E_b1~6.jsonl",
  "한국 설득·말싸움 64장 — data_debate/cards/D_b1~4.jsonl",
  "(보너스) 대화 코퍼스 — data/cards/M_b*.jsonl",
  "리포트 — debate_en_report.md · debate_easy_guide.md · debate_report.md",
  "subagent 3개가 세 각도로 전 카드·리포트를 재독해 추출 → 메인이 종합.",
];
srcs.forEach((s) =>
  children.push(new Paragraph({ numbering: { reference: "bul", level: 0 }, spacing: { after: 70, line: 288 }, children: runs([s]) }))
);
children.push(spacer(60));
children.push(
  ...callout(FILL_WARN, "⚠️ 한계 (다시 한 번)", "B23B2E", [
    [{ text: "Whisper 화자분리 없음 → 발언 귀속은 추론. “owns” 클립의 편집 편향 → won ≠ 실제 승리. 이 책은 기술 학습용이다." }],
  ])
);

// ============================================================
// DOCUMENT
// ============================================================
const doc = new Document({
  styles: {
    default: { document: { run: { font: "Malgun Gothic", size: BODY_SIZE, color: INK } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 36, bold: true, font: "Malgun Gothic", color: ACCENT },
        paragraph: { spacing: { before: 240, after: 160 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, font: "Malgun Gothic", color: INK },
        paragraph: { spacing: { before: 200, after: 120 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 24, bold: true, font: "Malgun Gothic", color: INK },
        paragraph: { spacing: { before: 180, after: 80 }, outlineLevel: 2 } },
    ],
  },
  numbering: {
    config: [
      { reference: "num", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 600, hanging: 320 } } } }] },
      { reference: "engine", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 600, hanging: 320 } } } }] },
      { reference: "bul", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 600, hanging: 320 } } } }] },
    ],
  },
  sections: [
    {
      properties: {
        page: {
          size: { width: 12240, height: 15840 },
          margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 },
        },
      },
      headers: {
        default: new Header({
          children: [
            new Paragraph({
              alignment: AlignmentType.RIGHT,
              spacing: { after: 0 },
              border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: "D0D8E8", space: 2 } },
              children: [new TextRun({ text: "말싸움 플레이북", size: 16, color: MUTED })],
            }),
          ],
        }),
      },
      footers: {
        default: new Footer({
          children: [
            new Paragraph({
              alignment: AlignmentType.CENTER,
              children: [
                new TextRun({ text: "— ", size: 16, color: MUTED }),
                new TextRun({ children: [PageNumber.CURRENT], size: 16, color: MUTED }),
                new TextRun({ text: " —", size: 16, color: MUTED }),
              ],
            }),
          ],
        }),
      },
      children,
    },
  ],
});

Packer.toBuffer(doc).then((buffer) => {
  fs.writeFileSync("malssaum_playbook.docx", buffer);
  console.log("DONE wrote malssaum_playbook.docx (" + buffer.length + " bytes)");
});
