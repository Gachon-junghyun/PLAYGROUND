# PLAY33_yt_career_harvest/viewer/build_viewer.py
"""토론 카드(JSONL) → 자체완결 cards.html 한 장으로 굽는다.

카드 데이터를 HTML 안에 JS 상수로 박아넣어, 더블클릭만으로 열린다 (file:// CORS 무관).
카드가 바뀌면 다시 실행: python build_viewer.py

읽는 소스:
  ../data_argue_en/cards/E_b*.jsonl  (영어 실시간 토론, 99장)  → corpus "EN"
  ../data_debate/cards/D_b*.jsonl    (한국 설득·말싸움, 64장)  → corpus "KR"
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

VIEWER_DIR = Path(__file__).resolve().parent
PLAY_DIR = VIEWER_DIR.parent

SOURCES = [
    # 패턴을 [1-9]로 좁혀 사이드카(E_b1.ko.jsonl 등)가 카드로 안 잡히게.
    ("EN", "영어 실시간 토론", PLAY_DIR / "data_argue_en" / "cards", "E_b[1-9].jsonl"),
    ("KR", "한국 설득·말싸움", PLAY_DIR / "data_debate" / "cards", "D_b[1-9].jsonl"),
]
# 한글 번역 사이드카 (card_id로 병합)
KO_DIR = PLAY_DIR / "data_argue_en" / "cards"
KO_PATTERN = "E_b[1-9].ko.jsonl"


def load_cards() -> list[dict]:
    out: list[dict] = []
    for corpus, label, cards_dir, pattern in SOURCES:
        for f in sorted(cards_dir.glob(pattern)):
            for line in f.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    c = json.loads(line)
                except json.JSONDecodeError as e:
                    print(f"[warn] {f.name}: JSON 파싱 실패 → {e}", file=sys.stderr)
                    continue
                c["corpus"] = corpus
                c["corpus_label"] = label
                sv = c.get("source_video") or {}
                c["_channel"] = sv.get("channel", "?")
                c["_title"] = sv.get("title_hint", "")
                c["_vid"] = sv.get("video_id", "")
                out.append(c)
    # 한글 번역 병합
    ko: dict[str, dict] = {}
    for f in sorted(KO_DIR.glob(KO_PATTERN)):
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                k = json.loads(line)
            except json.JSONDecodeError:
                continue
            ko[k.get("card_id")] = k
    for c in out:
        k = ko.get(c["card_id"])
        if k:
            for fld in ("move_ko", "how_ko", "counter_ko", "quote_gloss_ko"):
                c[fld] = k.get(fld, "")
    return out


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>토론 카드 뷰어 — PLAY33</title>
<style>
  :root{
    --bg:#0f1115; --panel:#1a1e26; --panel2:#222834; --line:#2c333f;
    --txt:#e6e9ef; --muted:#9aa4b2; --accent:#5b9dff;
    --won:#3fb950; --neutral:#8b949e; --lost:#f85149;
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--txt);
    font-family:"Segoe UI","Malgun Gothic","Apple SD Gothic Neo",system-ui,sans-serif;
    line-height:1.5;font-size:15px}
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
  .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:14px}
  .card{background:var(--panel);border:1px solid var(--line);border-radius:12px;
    padding:14px 15px;display:flex;flex-direction:column;gap:9px;overflow:hidden}
  .card-top{display:flex;align-items:center;gap:7px;flex-wrap:wrap}
  .cid{font-family:"Consolas",monospace;font-size:11px;color:var(--muted);
    background:var(--panel2);padding:2px 6px;border-radius:5px}
  .chip{font-size:11px;padding:2px 8px;border-radius:999px;font-weight:600;white-space:nowrap}
  .corpus{font-size:10px;color:var(--muted);border:1px solid var(--line);padding:2px 6px;border-radius:5px}
  .move{font-weight:600;font-size:15px}
  .who{font-size:12px;color:var(--accent)}
  .label{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.04em;margin-top:2px}
  .how{font-size:13.5px;color:#cdd3dc}
  .quote{font-size:13px;color:#c8cfd9;border-left:3px solid var(--accent);
    padding:6px 10px;background:var(--panel2);border-radius:0 7px 7px 0;font-style:italic}
  .counter{font-size:13px;color:#d6cfa8;border-left:3px solid #b9933a;
    padding:6px 10px;background:rgba(185,147,58,.08);border-radius:0 7px 7px 0}
  .foot{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin-top:auto;padding-top:4px;font-size:11px}
  .tag{background:var(--panel2);color:var(--muted);padding:2px 7px;border-radius:5px}
  .eff-won{background:rgba(63,185,80,.16);color:var(--won)}
  .eff-neutral{background:rgba(139,148,158,.16);color:var(--neutral)}
  .eff-lost{background:rgba(248,81,73,.16);color:var(--lost)}
  a.vid{color:var(--accent);text-decoration:none;font-size:11px}
  a.vid:hover{text-decoration:underline}
  .gloss{font-size:12px;color:var(--muted);font-style:normal;margin-top:4px}
  .toggle{background:var(--accent);color:#fff;border:none;border-radius:7px;
    padding:7px 12px;font-size:14px;font-family:inherit;cursor:pointer;font-weight:600}
  .toggle:hover{filter:brightness(1.1)}
  .empty{color:var(--muted);text-align:center;padding:60px 0}
</style>
</head>
<body>
<header>
  <h1>토론 카드 뷰어 <small>PLAY33 · 실제 토론/말싸움 무브 카드</small></h1>
  <div class="controls">
    <input type="search" id="q" placeholder="검색 (무브·근거·인용·채널·ID)…">
    <select id="corpus"><option value="">전체 코퍼스</option></select>
    <select id="axis"><option value="">전체 축</option></select>
    <select id="channel"><option value="">전체 채널</option></select>
    <select id="eff"><option value="">전체 효과</option><option value="won">won</option><option value="neutral">neutral</option><option value="lost">lost</option></select>
    <button id="lang" class="toggle" title="영어 카드 한글/원문 전환">🇰🇷 한글</button>
    <span id="stats"></span>
  </div>
</header>
<main><div class="grid" id="grid"></div></main>
<script>
const CARDS = __CARDS_JSON__;

const AXIS_COLORS = ["#5b9dff","#c678dd","#56b6c2","#e5a04c","#98c379","#e06c75","#d19a66","#61afef"];
const axisColor = {};
[...new Set(CARDS.map(c=>c.axis))].forEach((a,i)=>{ axisColor[a]=AXIS_COLORS[i%AXIS_COLORS.length]; });

function esc(s){ return String(s==null?"":s).replace(/[&<>"]/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[m])); }
function effClass(e){ const w=(e||"").trim().toLowerCase().split(/[\s—-]/)[0]; return ["won","neutral","lost"].includes(w)?w:""; }

function fillSelect(id, values){
  const sel=document.getElementById(id);
  values.forEach(v=>{ const o=document.createElement("option"); o.value=v; o.textContent=v; sel.appendChild(o); });
}
fillSelect("corpus", [...new Set(CARDS.map(c=>c.corpus_label))]);
fillSelect("axis", [...new Set(CARDS.map(c=>c.axis))].sort());
fillSelect("channel", [...new Set(CARDS.map(c=>c._channel))].sort());

let LANG = "ko";   // EN 카드만 영향: 한글 번역 ↔ 원문
function cardHtml(c){
  const col = axisColor[c.axis] || "#5b9dff";
  const ec = effClass(c.effectiveness);
  const KO = LANG==="ko", hasKo = !!c.move_ko;
  const move    = (KO && hasKo) ? c.move_ko    : c.move;
  const how     = (KO && hasKo) ? c.how_ko     : c.how_it_works;
  const counter = (KO && hasKo) ? c.counter_ko : c.counter;
  const gloss   = (KO && c.quote_gloss_ko) ? c.quote_gloss_ko : "";
  const vid = c._vid ? `<a class="vid" href="https://www.youtube.com/watch?v=${encodeURIComponent(c._vid)}" target="_blank" rel="noopener">▶ 원본</a>` : "";
  let foot = `<span class="corpus">${esc(c.corpus)}</span>`;
  if(c.effectiveness) foot += `<span class="chip eff-${ec||'neutral'}">${esc((c.effectiveness||'').split(/[—-]/)[0].trim())}</span>`;
  if(Array.isArray(c.applies_to)) c.applies_to.forEach(a=>foot+=`<span class="tag">${esc(a)}</span>`);
  if(c.confidence) foot += `<span class="tag">conf: ${esc((c.confidence||'').split(/[—-]/)[0].trim())}</span>`;
  foot += vid;
  return `<div class="card">
    <div class="card-top">
      <span class="cid">${esc(c.card_id)}</span>
      <span class="chip" style="background:${col}22;color:${col}">${esc(c.axis)}</span>
    </div>
    <div class="move">${esc(move)}</div>
    ${c.who?`<div class="who">👤 ${esc(c.who)}</div>`:""}
    <div class="how">${esc(how)}</div>
    <div class="quote">“${esc(c.evidence_quote)}”${gloss?`<div class="gloss">↳ ${esc(gloss)}</div>`:""}</div>
    ${counter?`<div class="counter"><b>🛡 막는 법</b> · ${esc(counter)}</div>`:""}
    <div style="font-size:11.5px;color:var(--muted)">${esc(c._channel)}${c._title?" · "+esc(c._title):""}</div>
    <div class="foot">${foot}</div>
  </div>`;
}

const grid=document.getElementById("grid"), stats=document.getElementById("stats");
function render(){
  const q=document.getElementById("q").value.trim().toLowerCase();
  const fc=document.getElementById("corpus").value, fa=document.getElementById("axis").value,
        fch=document.getElementById("channel").value, fe=document.getElementById("eff").value;
  const rows=CARDS.filter(c=>{
    if(fc && c.corpus_label!==fc) return false;
    if(fa && c.axis!==fa) return false;
    if(fch && c._channel!==fch) return false;
    if(fe && effClass(c.effectiveness)!==fe) return false;
    if(q){
      const hay=[c.card_id,c.axis,c.move,c.how_it_works,c.evidence_quote,c.counter,c._channel,c._title,c.who,(c.applies_to||[]).join(" "),c.move_ko,c.how_ko,c.counter_ko,c.quote_gloss_ko].join(" ").toLowerCase();
      if(!hay.includes(q)) return false;
    }
    return true;
  });
  grid.innerHTML = rows.length ? rows.map(cardHtml).join("") : `<div class="empty">조건에 맞는 카드가 없어요.</div>`;
  stats.textContent = `${rows.length} / ${CARDS.length}개`;
}
["q","corpus","axis","channel","eff"].forEach(id=>{
  document.getElementById(id).addEventListener("input",render);
  document.getElementById(id).addEventListener("change",render);
});
document.getElementById("lang").addEventListener("click",()=>{
  LANG = LANG==="ko" ? "en" : "ko";
  document.getElementById("lang").textContent = LANG==="ko" ? "🇰🇷 한글" : "🇬🇧 원문";
  render();
});
render();
</script>
</body>
</html>
"""


def main() -> None:
    cards = load_cards()
    if not cards:
        print("FAILED: 카드를 하나도 못 읽음 (data_argue_en/cards, data_debate/cards 확인)")
        sys.exit(1)
    html = HTML_TEMPLATE.replace(
        "__CARDS_JSON__", json.dumps(cards, ensure_ascii=False)
    )
    out = VIEWER_DIR / "cards.html"
    out.write_text(html, encoding="utf-8")
    by_corpus: dict[str, int] = {}
    for c in cards:
        by_corpus[c["corpus"]] = by_corpus.get(c["corpus"], 0) + 1
    print(f"[OK] {len(cards)}장 → {out}")
    print("     " + " · ".join(f"{k} {v}장" for k, v in by_corpus.items()))


if __name__ == "__main__":
    main()
