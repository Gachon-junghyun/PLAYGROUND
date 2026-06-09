"""Residue 카드(JSONL) → 자체완결 cards.html 한 장으로 굽는다.

PLAY33 viewer 패턴 차용(자체 포함). 카드를 HTML 안에 JS 상수로 박아 넣어
더블클릭만으로 열린다(file:// CORS 무관). 카드가 바뀌면 다시 실행:
  python build_viewer.py

idea/novel 분기를 시각적으로 드러낸다:
  - idea  : trigger→reframe, 자가점검 질문, 다음 복습일/reps 표시(파란 계열).
  - novel : trigger/복습일 없음. felt-shift를 강조(보라 계열). SRS 흔적 없음.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

VIEWER_DIR = Path(__file__).resolve().parent
PLAY_DIR = VIEWER_DIR.parent
CARDS_FILE = PLAY_DIR / "data" / "cards.jsonl"


def load_cards() -> list[dict]:
    out = []
    for line in CARDS_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError as e:
            print(f"[warn] JSON 파싱 실패 → {e}", file=sys.stderr)
    return out


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>책 체화 카드 — PLAY34</title>
<style>
  :root{
    --bg:#0f1115; --panel:#1a1e26; --panel2:#222834; --line:#2c333f;
    --txt:#e6e9ef; --muted:#9aa4b2; --idea:#5b9dff; --novel:#c678dd;
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--txt);
    font-family:"Segoe UI","Malgun Gothic","Apple SD Gothic Neo",system-ui,sans-serif;
    line-height:1.55;font-size:15px}
  header{position:sticky;top:0;z-index:10;background:rgba(15,17,21,.95);
    backdrop-filter:blur(6px);border-bottom:1px solid var(--line);padding:14px 18px}
  h1{margin:0;font-size:18px;font-weight:700}
  h1 small{color:var(--muted);font-weight:400;font-size:13px;margin-left:8px}
  .controls{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px;align-items:center}
  .controls input,.controls select{background:var(--panel2);color:var(--txt);
    border:1px solid var(--line);border-radius:7px;padding:7px 10px;font-size:14px;font-family:inherit}
  .controls input[type=search]{flex:1;min-width:180px}
  #stats{color:var(--muted);font-size:13px;margin-left:auto}
  main{padding:18px;max-width:1280px;margin:0 auto}
  .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(360px,1fr));gap:14px}
  .card{background:var(--panel);border:1px solid var(--line);border-radius:12px;
    padding:14px 15px;display:flex;flex-direction:column;gap:9px;overflow:hidden;border-top:3px solid var(--idea)}
  .card.novel{border-top-color:var(--novel)}
  .card-top{display:flex;align-items:center;gap:7px;flex-wrap:wrap}
  .cid{font-family:"Consolas",monospace;font-size:11px;color:var(--muted);
    background:var(--panel2);padding:2px 6px;border-radius:5px}
  .chip{font-size:11px;padding:2px 8px;border-radius:999px;font-weight:600;white-space:nowrap}
  .chip.idea{background:rgba(91,157,255,.16);color:var(--idea)}
  .chip.novel{background:rgba(198,120,221,.16);color:var(--novel)}
  .book{font-size:12px;color:var(--muted)}
  .lbl{font-size:10.5px;color:var(--muted);text-transform:uppercase;letter-spacing:.05em;margin-top:4px}
  .trigger{font-size:13px;color:#d6cfa8;border-left:3px solid #b9933a;
    padding:6px 10px;background:rgba(185,147,58,.08);border-radius:0 7px 7px 0}
  .reframe{font-weight:600;font-size:15px;color:#eef2f8}
  .why{font-size:13px;color:#c8cfd9}
  .evidence{font-size:12.5px;color:#c8cfd9;border-left:3px solid var(--idea);
    padding:6px 10px;background:var(--panel2);border-radius:0 7px 7px 0;font-style:italic}
  .card.novel .evidence{border-left-color:var(--novel)}
  .vq{font-size:12.5px;color:#cdd3dc;margin:2px 0 0 16px;padding:0}
  .anti{font-size:12px;color:#e0b0b0;border-left:3px solid #b85c5c;
    padding:5px 10px;background:rgba(184,92,92,.08);border-radius:0 7px 7px 0}
  .foot{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin-top:auto;padding-top:6px;font-size:11px}
  .tag{background:var(--panel2);color:var(--muted);padding:2px 7px;border-radius:5px}
  .empty{color:var(--muted);text-align:center;padding:60px 0}
</style>
</head>
<body>
<header>
  <h1>책 체화 카드 <small>PLAY34 · 잔여물(residue)을 발현으로</small></h1>
  <div class="controls">
    <input type="search" id="q" placeholder="검색 (reframe·trigger·책·인용·ID)…">
    <select id="type"><option value="">전체 종류</option><option value="idea">idea</option><option value="novel">novel</option></select>
    <select id="book"><option value="">전체 책</option></select>
    <select id="status"><option value="">전체 상태</option><option value="due">오늘 만기</option><option value="scheduled">예약됨</option><option value="novel">소설(SRS 외)</option></select>
    <span id="stats"></span>
  </div>
</header>
<main><div class="grid" id="grid"></div></main>
<script>
const CARDS = __CARDS_JSON__;
const TODAY = "__TODAY__";

function esc(s){ return String(s==null?"":s).replace(/[&<>"]/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[m])); }
function statusOf(c){
  if(c.book.type==="novel" || !c.review) return "novel";
  return (c.review.due <= TODAY) ? "due" : "scheduled";
}
function fillSelect(id, values){
  const sel=document.getElementById(id);
  values.forEach(v=>{ const o=document.createElement("option"); o.value=v; o.textContent=v; sel.appendChild(o); });
}
fillSelect("book", [...new Set(CARDS.map(c=>c.book.title))].sort());

function cardHtml(c){
  const t = c.book.type;
  const vq = (c.verification_questions||[]).map(q=>`<li class="vq">${esc(q)}</li>`).join("");
  let foot = `<span class="tag">${esc(c.book.author)}</span>`;
  if(t==="idea" && c.review){
    foot += `<span class="tag">due ${esc(c.review.due)}</span>`;
    foot += `<span class="tag">reps ${esc(c.review.reps)}</span>`;
    foot += `<span class="tag">ease ${esc(c.review.ease)}</span>`;
  } else {
    foot += `<span class="tag">SRS 외 · 경험</span>`;
  }
  return `<div class="card ${t}">
    <div class="card-top">
      <span class="cid">${esc(c.card_id)}</span>
      <span class="chip ${t}">${t==="idea"?"💡 idea":"📖 novel"}</span>
      <span class="book">${esc(c.book.title)}</span>
    </div>
    ${(t==="idea" && c.trigger_when)?`<div class="lbl">상황이 오면 (trigger)</div><div class="trigger">⚡ ${esc(c.trigger_when)}</div>`:""}
    <div class="lbl">${t==="idea"?"받아치는 한 수 (reframe)":"나에 대해 깨달은 것 (felt-shift)"}</div>
    <div class="reframe">${esc(c.reframe)}</div>
    ${c.why_it_matters?`<div class="why">${esc(c.why_it_matters)}</div>`:""}
    ${c.evidence?`<div class="evidence">${esc(c.evidence)}</div>`:""}
    ${vq?`<div class="lbl">자가 점검</div><ul style="margin:0;padding-left:18px">${vq}</ul>`:""}
    ${c.anti_signal?`<div class="anti"><b>⚠ 오용 신호</b> · ${esc(c.anti_signal)}</div>`:""}
    <div class="foot">${foot}</div>
  </div>`;
}

const grid=document.getElementById("grid"), stats=document.getElementById("stats");
function render(){
  const q=document.getElementById("q").value.trim().toLowerCase();
  const ft=document.getElementById("type").value, fb=document.getElementById("book").value,
        fs=document.getElementById("status").value;
  const rows=CARDS.filter(c=>{
    if(ft && c.book.type!==ft) return false;
    if(fb && c.book.title!==fb) return false;
    if(fs && statusOf(c)!==fs) return false;
    if(q){
      const hay=[c.card_id,c.book.title,c.book.author,c.trigger_when,c.reframe,c.why_it_matters,c.evidence,c.anti_signal,(c.verification_questions||[]).join(" ")].join(" ").toLowerCase();
      if(!hay.includes(q)) return false;
    }
    return true;
  });
  grid.innerHTML = rows.length ? rows.map(cardHtml).join("") : `<div class="empty">조건에 맞는 카드가 없어요.</div>`;
  const due = CARDS.filter(c=>statusOf(c)==="due").length;
  stats.textContent = `${rows.length} / ${CARDS.length}개 · 오늘 만기 ${due}`;
}
["q","type","book","status"].forEach(id=>{
  document.getElementById(id).addEventListener("input",render);
  document.getElementById(id).addEventListener("change",render);
});
render();
</script>
</body>
</html>
"""


def main() -> None:
    from datetime import date

    cards = load_cards()
    if not cards:
        print("FAILED: 카드를 하나도 못 읽음 (data/cards.jsonl 확인)")
        sys.exit(1)
    html = HTML_TEMPLATE.replace(
        "__CARDS_JSON__", json.dumps(cards, ensure_ascii=False)
    ).replace("__TODAY__", date.today().isoformat())
    out = VIEWER_DIR / "cards.html"
    out.write_text(html, encoding="utf-8")
    by_type: dict[str, int] = {}
    for c in cards:
        by_type[c["book"]["type"]] = by_type.get(c["book"]["type"], 0) + 1
    print(f"[OK] {len(cards)}장 → {out}")
    print("     " + " · ".join(f"{k} {v}장" for k, v in by_type.items()))


if __name__ == "__main__":
    main()
