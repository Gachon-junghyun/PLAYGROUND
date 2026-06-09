// problem_solving_playbook.md → problem_solving_playbook.docx
// 정보 밀도 보존(전 카드ID·플레이북 그대로) + 가독성(표 음영·콜아웃·목차).
// 자급: PLAY37/docs/node_modules 의 docx 사용 (PLAY33 import 안 함).
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, HeadingLevel, BorderStyle, WidthType, ShadingType,
  TableOfContents, PageNumber, Header, Footer, PageBreak,
} = require("docx");

const SRC = path.join(__dirname, "..", "problem_solving_playbook.md");
const OUT = path.join(__dirname, "problem_solving_playbook.docx");
const FONT = "Malgun Gothic";
const INK = "1A1A1A", MUTED = "5A5A5A", ACCENT = "2E5BBA";
const FILL_HEAD = "D5E3F7", FILL_NOTE = "EAF1FB", FILL_CELL = "F7FAFF";
const CONTENT_W = 9360;

// ---- inline **bold** parser ----
function inline(text, base = {}) {
  const out = [];
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  for (const p of parts) {
    if (!p) continue;
    if (p.startsWith("**") && p.endsWith("**"))
      out.push(new TextRun({ text: p.slice(2, -2), bold: true, font: FONT, size: 20, color: INK, ...base }));
    else
      out.push(new TextRun({ text: p, font: FONT, size: 20, color: INK, ...base }));
  }
  return out.length ? out : [new TextRun({ text: "", font: FONT, size: 20 })];
}

const para = (text, opts = {}) =>
  new Paragraph({ children: inline(text), spacing: { after: 110, line: 276 }, ...opts });

function heading(text, level) {
  const sizes = { 1: 34, 2: 26, 3: 23 };
  return new Paragraph({
    children: [new TextRun({ text, bold: true, font: FONT, size: sizes[level], color: level === 1 ? INK : ACCENT })],
    heading: level === 1 ? HeadingLevel.HEADING_1 : level === 2 ? HeadingLevel.HEADING_2 : HeadingLevel.HEADING_3,
    spacing: { before: level === 1 ? 120 : 260, after: 120 },
    border: level <= 2 ? { bottom: { style: BorderStyle.SINGLE, size: 8, color: level === 1 ? ACCENT : "C9D8F0", space: 4 } } : undefined,
  });
}

// shaded callout for blockquotes (> ...)
function callout(text) {
  return new Paragraph({
    children: inline(text, { size: 19, italics: true, color: MUTED }),
    shading: { fill: FILL_NOTE, type: ShadingType.CLEAR },
    border: { left: { style: BorderStyle.SINGLE, size: 18, color: ACCENT, space: 8 } },
    spacing: { before: 60, after: 120, line: 264 },
    indent: { left: 120 },
  });
}

const cell = (text, { head = false } = {}) =>
  new TableCell({
    shading: { fill: head ? FILL_HEAD : FILL_CELL, type: ShadingType.CLEAR },
    margins: { top: 60, bottom: 60, left: 90, right: 90 },
    children: [new Paragraph({
      children: inline(text, head ? { bold: true } : {}),
      spacing: { after: 0, line: 252 },
    })],
  });

function table(rows) {
  const ncol = rows[0].length;
  const widthEach = Math.floor(CONTENT_W / ncol);
  return new Table({
    width: { size: CONTENT_W, type: WidthType.DXA },
    columnWidths: rows[0].map(() => widthEach),
    rows: rows.map((r, i) =>
      new TableRow({ tableHeader: i === 0, children: r.map((c) => cell(c, { head: i === 0 })) })),
  });
}

// ---- parse markdown ----
const lines = fs.readFileSync(SRC, "utf8").split(/\r?\n/);
const body = [];
let i = 0;
while (i < lines.length) {
  let ln = lines[i];
  // tables
  if (/^\s*\|/.test(ln)) {
    const block = [];
    while (i < lines.length && /^\s*\|/.test(lines[i])) { block.push(lines[i]); i++; }
    const rows = block
      .filter((r) => !/^\s*\|[\s:|-]+\|\s*$/.test(r)) // drop separator row
      .map((r) => r.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map((c) => c.trim()));
    if (rows.length) body.push(table(rows));
    body.push(new Paragraph({ text: "", spacing: { after: 80 } }));
    continue;
  }
  if (/^#\s/.test(ln)) { body.push(heading(ln.replace(/^#\s/, ""), 1)); i++; continue; }
  if (/^##\s/.test(ln)) { body.push(heading(ln.replace(/^##\s/, ""), 2)); i++; continue; }
  if (/^###\s/.test(ln)) { body.push(heading(ln.replace(/^###\s/, ""), 3)); i++; continue; }
  if (/^>\s?/.test(ln)) {
    // merge consecutive blockquote lines
    const buf = [];
    while (i < lines.length && /^>\s?/.test(lines[i])) { buf.push(lines[i].replace(/^>\s?/, "")); i++; }
    body.push(callout(buf.join(" ")));
    continue;
  }
  if (/^---\s*$/.test(ln)) {
    body.push(new Paragraph({ border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "C9D8F0", space: 2 } }, spacing: { after: 120 } }));
    i++; continue;
  }
  if (/^\s*[-*]\s+/.test(ln)) {
    body.push(new Paragraph({ children: inline(ln.replace(/^\s*[-*]\s+/, "")), bullet: { level: 0 }, spacing: { after: 60, line: 264 } }));
    i++; continue;
  }
  if (/^\s*\d+\.\s+/.test(ln)) {
    body.push(new Paragraph({ children: inline(ln.replace(/^\s*\d+\.\s+/, "")), numbering: { reference: "num", level: 0 }, spacing: { after: 60, line: 264 } }));
    i++; continue;
  }
  if (ln.trim() === "") { i++; continue; }
  body.push(para(ln));
  i++;
}

// ---- assemble ----
const titlePage = [
  new Paragraph({ text: "", spacing: { before: 1800 } }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 },
    children: [new TextRun({ text: "문제해결능력, 현실에서 쓰는 법", bold: true, font: FONT, size: 48, color: INK })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 600 },
    children: [new TextRun({ text: "7개 자리 플레이북", font: FONT, size: 30, color: ACCENT })] }),
  new Paragraph({ alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "유튜브 20편 → 추상 프레임(카드 109장) → 7개 현실 시나리오 스트레스테스트", font: FONT, size: 19, color: MUTED })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 80 },
    children: [new TextRun({ text: "PLAY37_problem_solving · 2026-06-04", font: FONT, size: 18, color: MUTED })] }),
  new Paragraph({ children: [new PageBreak()] }),
  heading("목차", 2),
  new TableOfContents("목차", { hyperlink: true, headingStyleRange: "1-3" }),
  new Paragraph({ children: [new PageBreak()] }),
];

const doc = new Document({
  creator: "PLAY37_problem_solving",
  title: "문제해결능력, 현실에서 쓰는 법",
  styles: { default: { document: { run: { font: FONT, size: 20, color: INK } } } },
  numbering: {
    config: [{ reference: "num", levels: [{ level: 0, format: "decimal", text: "%1.", alignment: AlignmentType.START }] }],
  },
  sections: [{
    properties: { page: { margin: { top: 1100, bottom: 1100, left: 1100, right: 1100 } } },
    headers: { default: new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT,
      children: [new TextRun({ text: "문제해결 플레이북", font: FONT, size: 16, color: MUTED })] })] }) },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
      children: [new TextRun({ children: ["", PageNumber.CURRENT], font: FONT, size: 16, color: MUTED })] })] }) },
    children: [...titlePage, ...body],
  }],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(OUT, buf);
  console.log("WROTE", OUT, buf.length, "bytes");
});
