"""records.jsonl → 자기완결 viewer.html (의존성 0, 브라우저로 더블클릭).

사고 레코드를 눈으로 검증하기 위한 뷰어:
- 상단 대시보드(타입/측면/소스/core/trigger 적합률)
- 카드 브라우저(검색·측면/타입/tier/소스 필터·정렬)
- 검색 시뮬레이터(상황 문장 → BM25 랭킹으로 '무엇이 발동하나' 확인 = 시스템 검증)

실행:  python build_viewer.py   →  viewer.html 생성
데이터는 HTML 안에 박으므로 파일 하나만 열면 됨(로컬 fetch/CORS 문제 없음).
"""
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
RECORDS = HERE / "records.jsonl"
OUT = HERE / "viewer.html"

SIT = ("때", "작업", "상황", "구간", "시점", "국면", "경우", "동안")

recs = [json.loads(l) for l in RECORDS.read_text(encoding="utf-8").splitlines() if l.strip()]
n = len(recs)
stats = {
    "total": n,
    "types": dict(Counter(r["type"] for r in recs)),
    "aspects": dict(Counter(r["aspect"] for r in recs)),
    "sources": dict(Counter(r["source"] for r in recs)),
    "tiers": dict(Counter(r["tier"] for r in recs)),
    "core": sum(1 for r in recs if r["tier"] == "core"),
    "trig_ok": sum(1 for r in recs if r["trigger"].rstrip().endswith(SIT)),
}

DATA = json.dumps({"records": recs, "stats": stats}, ensure_ascii=False).replace("</", "<\\/")

HTML = """<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PLAY44 사고 레코드 뷰어</title>
<style>
:root{
  --bg:#0e1116; --panel:#161b22; --panel2:#1c2330; --line:#2a3240; --line2:#3a4658;
  --fg:#e6edf3; --mut:#8b98a9; --acc:#58a6ff;
  --c-think:#9b8cff; --c-domain:#3fb950; --c-output:#f0883e; --c-task:#56d4dd;
  --core:#ffd24d;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
  font-family:system-ui,-apple-system,"Malgun Gothic","Apple SD Gothic Neo",Pretendard,sans-serif;
  line-height:1.6;font-size:15px}
a{color:var(--acc)}
.wrap{max-width:1180px;margin:0 auto;padding:22px 18px 80px}
h1{font-size:20px;margin:0 0 2px}
.sub{color:var(--mut);font-size:13px;margin-bottom:18px}

/* dashboard */
.dash{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px;margin-bottom:18px}
.stat{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:11px 13px}
.stat .k{color:var(--mut);font-size:11px;text-transform:uppercase;letter-spacing:.4px}
.stat .v{font-size:22px;font-weight:700;margin-top:3px}
.stat .v small{font-size:13px;color:var(--mut);font-weight:400}
.bars{display:flex;flex-direction:column;gap:5px;margin-top:7px}
.bar{display:flex;align-items:center;gap:7px;font-size:12px}
.bar .lbl{width:78px;color:var(--mut);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.bar .track{flex:1;height:7px;background:var(--panel2);border-radius:4px;overflow:hidden}
.bar .fill{height:100%;background:var(--acc);border-radius:4px}
.bar .num{width:30px;text-align:right;color:var(--mut)}

/* controls */
.controls{position:sticky;top:0;z-index:5;background:var(--bg);
  padding:12px 0 10px;border-bottom:1px solid var(--line);margin-bottom:14px}
.row{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:8px}
input[type=text]{background:var(--panel);border:1px solid var(--line2);color:var(--fg);
  border-radius:8px;padding:9px 12px;font-size:14px;font-family:inherit;width:100%}
.chip{background:var(--panel);border:1px solid var(--line2);color:var(--mut);
  border-radius:999px;padding:4px 11px;font-size:12.5px;cursor:pointer;user-select:none;white-space:nowrap}
.chip.on{color:#fff;border-color:transparent}
.chip.on[data-k=think]{background:var(--c-think)} .chip.on[data-k=domain]{background:var(--c-domain)}
.chip.on[data-k=output]{background:var(--c-output)} .chip.on[data-k=task]{background:var(--c-task)}
.chip.on[data-k=g]{background:var(--acc)}
.lbl-mut{color:var(--mut);font-size:12px;margin-right:2px}
select{background:var(--panel);border:1px solid var(--line2);color:var(--fg);
  border-radius:8px;padding:7px 9px;font-size:13px;font-family:inherit}
.count{color:var(--mut);font-size:13px;margin-left:auto}

/* cards */
.grid{display:flex;flex-direction:column;gap:11px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:11px;padding:14px 16px;
  border-left:4px solid var(--line2)}
.card.think{border-left-color:var(--c-think)} .card.domain{border-left-color:var(--c-domain)}
.card.output{border-left-color:var(--c-output)} .card.task{border-left-color:var(--c-task)}
.card.core{box-shadow:inset 0 0 0 1px var(--core)}
.meta{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin-bottom:9px;font-size:11.5px}
.badge{border-radius:5px;padding:1.5px 7px;font-weight:600}
.b-id{font-family:ui-monospace,Consolas,monospace;background:var(--panel2);color:var(--mut)}
.b-type{background:#26303f;color:#a9c1e0}
.b-aspect{color:#0e1116;font-weight:700}
.b-aspect.think{background:var(--c-think)} .b-aspect.domain{background:var(--c-domain)}
.b-aspect.output{background:var(--c-output)} .b-aspect.task{background:var(--c-task)}
.b-core{background:var(--core);color:#0e1116;font-weight:700}
.b-src{color:var(--mut)} .b-use{color:var(--mut);margin-left:auto}
.trig{color:var(--acc);font-size:13.5px;margin-bottom:7px}
.trig::before{content:"⟶ 발동: ";color:var(--mut)}
.text{white-space:pre-wrap;font-size:14.5px}
.text.clamp{max-height:7.4em;overflow:hidden;
  -webkit-mask-image:linear-gradient(#000 70%,transparent);mask-image:linear-gradient(#000 70%,transparent)}
.more{color:var(--acc);font-size:12px;cursor:pointer;margin-top:4px;display:inline-block}
mark{background:#3a4d12;color:#e8ffb0;border-radius:2px;padding:0 1px}
.empty{color:var(--mut);text-align:center;padding:40px}

/* simulator */
.sim{background:var(--panel2);border:1px solid var(--line2);border-radius:11px;padding:14px 16px;margin-bottom:20px}
.sim h2{font-size:15px;margin:0 0 4px} .sim p{color:var(--mut);font-size:12.5px;margin:0 0 10px}
.simrow{display:flex;gap:8px;flex-wrap:wrap}
.simrow input{flex:1;min-width:240px}
.btn{background:var(--acc);color:#06121f;border:none;border-radius:8px;padding:9px 16px;
  font-size:14px;font-weight:600;cursor:pointer;font-family:inherit}
.simres{margin-top:12px;display:flex;flex-direction:column;gap:8px}
.hit{background:var(--panel);border:1px solid var(--line);border-radius:9px;padding:9px 12px;font-size:13px}
.hit .h1{display:flex;gap:8px;align-items:center;margin-bottom:3px}
.hit .sc{font-family:ui-monospace,monospace;color:var(--c-domain);font-size:12px}
.hit .ht{color:var(--mut);font-size:12.5px}
.ex{color:var(--mut);font-size:12px;margin-top:4px}
.ex b{color:#bcd;cursor:pointer;font-weight:400;border-bottom:1px dashed var(--line2)}
.foot{color:var(--mut);font-size:12px;margin-top:30px;border-top:1px solid var(--line);padding-top:14px}
</style></head>
<body><div class="wrap">
<h1>PLAY44 · 사고 레코드 뷰어</h1>
<div class="sub">records.jsonl 을 눈으로 검증한다. 측면=네임스페이스, 발동=trigger(검색 키), 본문=사고 무브.</div>
<div class="dash" id="dash"></div>

<div class="sim">
  <h2>🔍 검색 시뮬레이터 — "이 상황이면 무엇이 발동하나"</h2>
  <p>상황 문장을 넣으면 trigger 토큰 기준 BM25 랭킹으로 발동 카드를 보여준다(실제 파이프라인은 dense+BM25 RRF, 여기선 가독용 lexical 프록시). 측면 필터를 켜면 그 네임스페이스 안에서만.</p>
  <div class="simrow">
    <input type="text" id="simq" placeholder="예: 싼 가격이 밸류 트랩인지 판단할 때 / 종목 가격 데이터가 필요할 때">
    <button class="btn" id="simgo">발동시켜</button>
  </div>
  <div class="simres" id="simres"></div>
</div>

<div class="controls">
  <div class="row"><input type="text" id="q" placeholder="본문·trigger·id 전체 검색…"></div>
  <div class="row" id="f-aspect"></div>
  <div class="row" id="f-type"></div>
  <div class="row">
    <span class="lbl-mut">정렬</span>
    <select id="sort">
      <option value="id">id 순</option>
      <option value="use">사용 횟수↓</option>
      <option value="trig">trigger 적합 먼저</option>
      <option value="len">본문 길이↓</option>
    </select>
    <label class="chip" id="coreonly" data-k="g">core만</label>
    <label class="chip" id="badtrig" data-k="g">trigger 미적합만</label>
    <span class="count" id="count"></span>
  </div>
</div>
<div class="grid" id="grid"></div>
<div class="foot">
  생성: build_viewer.py · 데이터: knowledge/records.jsonl · 파이프라인 실동작은 compiler/logs/smoke_report.md 참조.
</div>
</div>
<script>
const DB = __DATA__;
const RECS = DB.records, ST = DB.stats;
const AK = {"사고스타일":"think","도메인규칙":"domain","출력형식":"output","작업유형":"task"};
const SIT = ["때","작업","상황","구간","시점","국면","경우","동안"];
const trigOK = r => SIT.some(s => r.trigger.trim().endsWith(s));
const esc = s => s.replace(/[&<>]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));
function tok(s){ return (s.toLowerCase().match(/[가-힣]+|[a-z]+|[0-9]+/g)||[]); }

/* ---- dashboard ---- */
function bars(obj,total,colorByAspect){
  const max=Math.max(...Object.values(obj));
  return Object.entries(obj).sort((a,b)=>b[1]-a[1]).map(([k,v])=>{
    const col = colorByAspect&&AK[k] ? `var(--c-${AK[k]})` : "var(--acc)";
    return `<div class="bar"><span class="lbl" title="${esc(k)}">${esc(k)}</span>
      <span class="track"><span class="fill" style="width:${v/max*100}%;background:${col}"></span></span>
      <span class="num">${v}</span></div>`;
  }).join("");
}
document.getElementById("dash").innerHTML =
  `<div class="stat"><div class="k">총 레코드</div><div class="v">${ST.total}</div></div>
   <div class="stat"><div class="k">core tier</div><div class="v">${ST.core} <small>/ ${ST.total} · ${(ST.core/ST.total*100).toFixed(1)}%</small></div></div>
   <div class="stat"><div class="k">trigger 적합</div><div class="v">${ST.trig_ok} <small>/ ${ST.total}</small></div></div>
   <div class="stat" style="grid-column:span 2"><div class="k">측면(aspect)</div><div class="bars">${bars(ST.aspects,ST.total,true)}</div></div>
   <div class="stat"><div class="k">타입</div><div class="bars">${bars(ST.types,ST.total,false)}</div></div>
   <div class="stat" style="grid-column:span 2"><div class="k">소스</div><div class="bars">${bars(ST.sources,ST.total,false)}</div></div>`;

/* ---- filters ---- */
const state={q:"",aspect:new Set(),type:new Set(),sort:"id",coreOnly:false,badTrig:false};
function chipRow(id,vals,key,colorAspect){
  const box=document.getElementById(id);
  box.innerHTML=`<span class="lbl-mut">${key==="aspect"?"측면":"타입"}</span>`+
    vals.map(v=>`<span class="chip" data-v="${esc(v)}" ${colorAspect&&AK[v]?`data-k="${AK[v]}"`:`data-k="g"`}>${esc(v)} <small>${ST[key+"s"][v]}</small></span>`).join("");
  box.querySelectorAll(".chip").forEach(c=>c.onclick=()=>{
    const v=c.dataset.v, set=state[key];
    set.has(v)?set.delete(v):set.add(v); c.classList.toggle("on"); render();
  });
}
chipRow("f-aspect",Object.keys(ST.aspects),"aspect",true);
chipRow("f-type",Object.keys(ST.types),"type",false);
document.getElementById("q").oninput=e=>{state.q=e.target.value.trim();render();};
document.getElementById("sort").onchange=e=>{state.sort=e.target.value;render();};
document.getElementById("coreonly").onclick=e=>{state.coreOnly=!state.coreOnly;e.target.classList.toggle("on");render();};
document.getElementById("badtrig").onclick=e=>{state.badTrig=!state.badTrig;e.target.classList.toggle("on");render();};

/* ---- render cards ---- */
function hl(s,q){ if(!q) return esc(s);
  const ts=[...new Set(tok(q))].filter(t=>t.length>1); let out=esc(s);
  ts.forEach(t=>{ out=out.replace(new RegExp("("+t.replace(/[.*+?^${}()|[\\]\\\\]/g,"\\\\$&")+")","gi"),"<mark>$1</mark>"); });
  return out;
}
function card(r){
  const a=AK[r.aspect]||"", core=r.tier==="core";
  const bad=!trigOK(r);
  return `<div class="card ${a} ${core?"core":""}">
    <div class="meta">
      <span class="badge b-id">${r.id}</span>
      <span class="badge b-type">${r.type}</span>
      <span class="badge b-aspect ${a}">${r.aspect}</span>
      ${core?'<span class="badge b-core">CORE</span>':""}
      ${bad?'<span class="badge" style="background:#5a2330;color:#ffb3c0">trig?</span>':""}
      <span class="badge b-src">${esc(r.source)}</span>
      <span class="badge b-use">▲ ${r.usage_count}</span>
    </div>
    <div class="trig">${hl(r.trigger,state.q)}</div>
    <div class="text clamp">${hl(r.text,state.q)}</div>
    <span class="more">＋ 더보기</span>
  </div>`;
}
function applyFilters(){
  let rs=RECS.slice();
  if(state.aspect.size) rs=rs.filter(r=>state.aspect.has(r.aspect));
  if(state.type.size) rs=rs.filter(r=>state.type.has(r.type));
  if(state.coreOnly) rs=rs.filter(r=>r.tier==="core");
  if(state.badTrig) rs=rs.filter(r=>!trigOK(r));
  if(state.q){ const ts=tok(state.q);
    rs=rs.filter(r=>{const h=(r.text+" "+r.trigger+" "+r.id).toLowerCase(); return ts.every(t=>h.includes(t));}); }
  const S=state.sort;
  rs.sort((a,b)=> S==="use"?b.usage_count-a.usage_count : S==="len"?b.text.length-a.text.length :
    S==="trig"?(trigOK(b)-trigOK(a)) : a.id.localeCompare(b.id));
  return rs;
}
function render(){
  const rs=applyFilters();
  document.getElementById("count").textContent=`${rs.length} / ${RECS.length}`;
  const g=document.getElementById("grid");
  g.innerHTML = rs.length? rs.map(card).join("") : '<div class="empty">조건에 맞는 레코드 없음</div>';
  g.querySelectorAll(".more").forEach(m=>m.onclick=()=>{
    const t=m.previousElementSibling; t.classList.toggle("clamp");
    m.textContent=t.classList.contains("clamp")?"＋ 더보기":"－ 접기";
  });
}

/* ---- retrieval simulator (BM25 over triggers) ---- */
const DOCS=RECS.map(r=>tok(r.trigger));
const N=DOCS.length, avgdl=DOCS.reduce((s,d)=>s+d.length,0)/N;
const DF={}; DOCS.forEach(d=>new Set(d).forEach(t=>DF[t]=(DF[t]||0)+1));
function bm25(qtok,idx,k1=1.5,b=0.75){
  const d=DOCS[idx], dl=d.length||1, tf={}; d.forEach(t=>tf[t]=(tf[t]||0)+1);
  let s=0; qtok.forEach(q=>{ if(!tf[q])return;
    const idf=Math.log(1+(N-DF[q]+0.5)/(DF[q]+0.5));
    s+=idf*tf[q]*(k1+1)/(tf[q]+k1*(1-b+b*dl/avgdl)); }); return s;
}
function simulate(){
  const q=document.getElementById("simq").value.trim();
  const box=document.getElementById("simres"); if(!q){box.innerHTML="";return;}
  const qt=tok(q);
  const ns=state.aspect.size?[...state.aspect]:null;
  let scored=RECS.map((r,i)=>({r,s:bm25(qt,i)}))
    .filter(x=>x.s>0 && (!ns||ns.includes(x.r.aspect)))
    .sort((a,b)=>b.s-a.s).slice(0,8);
  if(!scored.length){box.innerHTML='<div class="ht">발동 카드 없음 — 코퍼스에 그 상황 지식이 없다는 신호(스코프 밖).</div>';return;}
  box.innerHTML=scored.map(({r,s})=>{
    const a=AK[r.aspect]||"";
    return `<div class="hit">
      <div class="h1"><span class="badge b-id">${r.id}</span>
        <span class="badge b-aspect ${a}">${r.aspect}</span>
        <span class="sc">bm25=${s.toFixed(3)}</span></div>
      <div class="ht">⟶ ${esc(r.trigger)}</div>
      <div class="ex"><b data-id="${r.id}">사고 무브 펼치기 ▾</b><span hidden>${esc(r.text)}</span></div>
    </div>`;
  }).join("");
  box.querySelectorAll(".ex b").forEach(b=>b.onclick=()=>{
    const sp=b.nextElementSibling; sp.hidden=!sp.hidden;
    b.textContent=sp.hidden?"사고 무브 펼치기 ▾":"접기 ▴";
  });
}
document.getElementById("simgo").onclick=simulate;
document.getElementById("simq").addEventListener("keydown",e=>{if(e.key==="Enter")simulate();});

render();
</script></body></html>"""

OUT.write_text(HTML.replace("__DATA__", DATA), encoding="utf-8")
print(f"[viewer] wrote {OUT}  ({n} records, {OUT.stat().st_size//1024} KB)")
