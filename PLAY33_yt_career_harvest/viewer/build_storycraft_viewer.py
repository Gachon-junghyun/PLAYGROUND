"""storycraft 카드(JSONL) → 자체완결 storycraft_cards.html 한 장으로 굽는다.
데이터를 JS 상수로 임베드하므로 file:// 더블클릭으로 열린다(CORS 무관).

실행:  python viewer/build_storycraft_viewer.py
입력:  ../data_storycraft/cards/_all.jsonl
출력:  ../data_storycraft/reports/storycraft_cards.html
"""
import json, sys, html
from pathlib import Path

PLAY_DIR = Path(__file__).resolve().parent.parent
SRC = PLAY_DIR / "data_storycraft" / "cards" / "_all.jsonl"
OUT = PLAY_DIR / "data_storycraft" / "reports" / "storycraft_cards.html"

AXIS_LABEL = {
    "story_engine": "스토리 엔진", "character_craft": "캐릭터", "structure_plot": "구조·플롯",
    "prose_voice": "문장·표현", "theme_meaning": "주제·의미", "craft_mindset": "작법 태도",
}


def load():
    out = []
    for line in SRC.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        c = json.loads(line)
        sv = c.get("source_video") or {}
        c["_channel"] = sv.get("channel", "?")
        c["_title"] = sv.get("title_hint", "")
        c["_vid"] = sv.get("video_id", "")
        out.append(c)
    return out


PAGE = """<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>작법 카드 — storycraft (%(n)d장)</title>
<style>
 :root{--bg:#0f1115;--panel:#171a21;--line:#272c36;--ink:#e7e9ee;--mut:#8b93a5;}
 *{box-sizing:border-box} body{margin:0;background:var(--bg);color:var(--ink);
   font:15px/1.55 system-ui,"Segoe UI",Apple SD Gothic Neo,sans-serif}
 header{position:sticky;top:0;background:#0f1115ee;backdrop-filter:blur(6px);
   border-bottom:1px solid var(--line);padding:14px 18px;z-index:5}
 h1{font-size:17px;margin:0 0 10px} .ctrl{display:flex;gap:8px;flex-wrap:wrap}
 input,select{background:var(--panel);color:var(--ink);border:1px solid var(--line);
   border-radius:9px;padding:8px 10px;font-size:14px} input{flex:1;min-width:180px}
 #stat{color:var(--mut);font-size:13px;margin-top:8px}
 main{padding:18px;display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:14px}
 .card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px}
 .top{display:flex;align-items:center;gap:7px;flex-wrap:wrap;margin-bottom:8px}
 .cid{font:12px ui-monospace,monospace;color:var(--mut)}
 .chip{font-size:12px;padding:2px 8px;border-radius:99px}
 .conf{font-size:11px;color:var(--mut);margin-left:auto}
 .move{font-weight:600;margin:2px 0 8px}
 .how{color:#cdd3df;font-size:14px;margin-bottom:8px}
 .q{border-left:3px solid #3a4250;padding:4px 0 4px 10px;color:#aeb6c6;
   font-size:13px;font-style:italic;margin-bottom:8px;white-space:pre-wrap}
 .counter{font-size:13px;color:#d9a07a;margin-bottom:6px}
 .meta{font-size:12px;color:var(--mut);display:flex;gap:8px;flex-wrap:wrap;align-items:center}
 .vid{color:#5b9dff;text-decoration:none} .empty{color:var(--mut);padding:40px;text-align:center}
</style></head><body>
<header>
 <h1>작법 카드 — 재미있는 스토리 · 표현 · 좋은 글 <span style="color:var(--mut)">(%(n)d장)</span></h1>
 <div class="ctrl">
   <input id="q" placeholder="검색: 기법·인용·채널·인물…">
   <select id="axis"><option value="">전체 축</option></select>
   <select id="ch"><option value="">전체 채널</option></select>
   <select id="conf"><option value="">신뢰도 전체</option><option>high</option><option>medium</option><option>low</option></select>
 </div>
 <div id="stat"></div>
</header>
<main id="grid"></main>
<script>
const CARDS = %(data)s;
const AXIS_LABEL = %(axis)s;
const COLORS=["#5b9dff","#7bd88f","#e3b341","#d987d9","#e0795a","#54c8c8"];
const axisColor={}; [...new Set(CARDS.map(c=>c.axis))].forEach((a,i)=>axisColor[a]=COLORS[i%%COLORS.length]);
function esc(s){return (s||"").replace(/[&<>]/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[m]));}
function fill(id,vals,lab){const s=document.getElementById(id);
  vals.forEach(v=>{const o=document.createElement("option");o.value=v;o.textContent=lab?lab(v):v;s.appendChild(o);});}
fill("axis",[...new Set(CARDS.map(c=>c.axis))].sort(),v=>AXIS_LABEL[v]||v);
fill("ch",[...new Set(CARDS.map(c=>c._channel))].sort());
function card(c){const col=axisColor[c.axis]||"#5b9dff";
  const vid=c._vid?`<a class="vid" href="https://www.youtube.com/watch?v=${encodeURIComponent(c._vid)}" target="_blank" rel="noopener">▶ 원본</a>`:"";
  const counter=c.counter?`<div class="counter">⚠ ${esc(c.counter)}</div>`:"";
  const who=c.who?`· ${esc(c.who)}`:"";
  return `<div class="card"><div class="top">
    <span class="cid">${esc(c.card_id)}</span>
    <span class="chip" style="background:${col}22;color:${col}">${esc(AXIS_LABEL[c.axis]||c.axis)}</span>
    <span class="conf">${esc((c.confidence||"").split("—")[0].split("|")[0].trim())}</span></div>
    <div class="move">${esc(c.move)}</div>
    <div class="how">${esc(c.how_it_works)}</div>
    <div class="q">${esc(c.evidence_quote)}</div>
    ${counter}
    <div class="meta">${esc(c._channel)} ${who} ${vid}</div></div>`;}
function render(){const q=document.getElementById("q").value.toLowerCase(),
  fa=document.getElementById("axis").value,fc=document.getElementById("ch").value,
  fco=document.getElementById("conf").value;
  const rows=CARDS.filter(c=>{
    if(fa&&c.axis!==fa)return false; if(fc&&c._channel!==fc)return false;
    if(fco&&!(c.confidence||"").startsWith(fco))return false;
    if(q){const hay=[c.card_id,c.axis,c.move,c.how_it_works,c.evidence_quote,c.counter,c._channel,c._title,c.who].join(" ").toLowerCase();
      if(!hay.includes(q))return false;} return true;});
  document.getElementById("stat").textContent=`${rows.length} / ${CARDS.length}장`;
  document.getElementById("grid").innerHTML=rows.length?rows.map(card).join(""):`<div class="empty">조건에 맞는 카드가 없어요.</div>`;}
["q","axis","ch","conf"].forEach(id=>document.getElementById(id).addEventListener("input",render));
render();
</script></body></html>"""


def main():
    cards = load()
    if not cards:
        print("FAILED: 카드가 없음", file=sys.stderr); sys.exit(1)
    page = PAGE % {
        "n": len(cards),
        "data": json.dumps(cards, ensure_ascii=False),
        "axis": json.dumps(AXIS_LABEL, ensure_ascii=False),
    }
    OUT.write_text(page, encoding="utf-8")
    print(f"[OK] {len(cards)}장 → {OUT}")


if __name__ == "__main__":
    main()
