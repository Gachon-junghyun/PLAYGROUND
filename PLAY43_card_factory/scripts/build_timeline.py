"""PLAY43 타임라인 빌더 — 코퍼스가 어떻게 자라왔나를 한 장으로.

세 시대를 모아 자체완결 HTML(viewer/timeline.html, file:// OK)로 굽는다:
  ① 기원   — PLAY13 한국 금융 유튜브 5채널 → E시리즈 44함수
  ② 부트스트랩 — PLAY31 한국 증권 리포트 26건 → B시리즈 43함수 (2026-05)
  ③ 라이브 — PLAY43 신규 수집(seen_reports + cards + stress)

  python scripts/build_timeline.py        # timeline.json + viewer/timeline.html 생성

원본 폴더는 읽기만. 새 리포트가 추가되면 다시 돌리면 라이브 시대에 누적된다.
"""
import json
import datetime
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import (PLAY13_DIR, PLAY31_DIR, V4_LIB, V5_WORKING, SEEN_REPORTS,
                    CARDS_DIR, STRESS_DIR, DATA_DIR, PLAY43_DIR)


def _load_jsonl(p):
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


# ── ① 기원: PLAY13 유튜브 5채널 ──
def era_origin():
    channels = [
        ("오선의 미국증시 라이프", "미국증시·매크로"),
        ("머니그라피", "비즈니스·부동산"),
        ("머니코믹스", "금융 해설·토론"),
        ("지식부장관", "지정학·정책"),
        ("김단테 월가아재", "주식 분석"),
    ]
    ncards = 0
    p = PLAY13_DIR / "data" / "r4_all_cards.jsonl"
    if p.exists():
        ncards = len([1 for l in p.read_text(encoding="utf-8").splitlines() if l.strip()])
    items = [{"date": "2026-05-18", "source_type": "youtube_kr", "actor": ch,
              "title": topic, "n_cards": None, "tags": ["E시리즈"]} for ch, topic in channels]
    return {"id": "origin", "label": "① 기원 — 한국 금융 유튜브 5채널 → E시리즈 44함수",
            "note": f"PLAY13: 자막 1,060명제 → R4 {ncards or 64}카드 → 사고함수 F01~F44", "items": items}


# ── ② 부트스트랩: PLAY31 증권 리포트 26건 ──
def era_bootstrap():
    reports = {}
    for fp in (PLAY31_DIR / "data" / "cards").glob("*.jsonl"):
        if ".bak" in fp.name:
            continue
        for c in _load_jsonl(fp):
            ra = c.get("report_attribution", {}) or {}
            srcs = c.get("source_reports") or []
            rid = (srcs[0].get("report_id") if srcs and isinstance(srcs[0], dict)
                   else f"{ra.get('broker','?')}|{ra.get('publish_date','?')}")
            d = reports.setdefault(rid, {"broker": ra.get("broker"), "date": ra.get("publish_date"),
                                         "target": ra.get("target"), "type": ra.get("report_type"),
                                         "stance": ra.get("stance_vs_consensus"), "n_cards": 0})
            d["n_cards"] += 1
    items = []
    for rid, d in reports.items():
        items.append({"date": d["date"] or "2026-05", "source_type": "broker_kr",
                      "actor": d["broker"] or "?", "title": (d.get("target") or "") + (f" · {d['type']}" if d.get("type") else ""),
                      "n_cards": d["n_cards"], "tags": ["B시리즈"] + ([d["stance"]] if d.get("stance") else [])})
    items.sort(key=lambda x: str(x["date"]))
    return {"id": "bootstrap", "label": f"② 부트스트랩 — 한국 증권 리포트 {len(items)}건 → B시리즈 43함수",
            "note": "PLAY31: 2026-05, 전부 국내 증권사. 결론 아닌 사고 경로 역추출.", "items": items}


# ── ③ 라이브: PLAY43 신규 ──
def era_live():
    seen = json.loads(SEEN_REPORTS.read_text(encoding="utf-8")) if SEEN_REPORTS.exists() else {}
    # 카드화된 리포트별 신규/매칭 함수 카운트
    fn_by_report = {}
    for fp in CARDS_DIR.glob("*.functions.jsonl"):
        new = matched = 0
        for f in _load_jsonl(fp):
            if f.get("is_new"):
                new += 1
            else:
                matched += 1
        fn_by_report[fp.name] = {"new": new, "matched": matched}
    # 스트레스 판정
    verdicts = {}
    sr = STRESS_DIR / "stress_report.json"
    if sr.exists():
        for r in json.loads(sr.read_text(encoding="utf-8")).get("results", []):
            verdicts[r["id"]] = "survived" if r.get("verdict", {}).get("survives") else "cut"
    cand = {c.get("function_id") for c in _load_jsonl(STRESS_DIR / "candidates_pending.jsonl")}

    items = []
    for rid, meta in seen.items():
        st = meta.get("source", "?")
        stype = "broker_kr" if st == "naver" else ("broker_foreign" if st == "seekingalpha" else st)
        # 카드 파일 매칭 (파일명에 rid 앞부분 포함)
        cardfile = next((n for n in fn_by_report if rid[:8] in n), None)
        fc = fn_by_report.get(cardfile, {"new": 0, "matched": 0}) if cardfile else None
        tags = [{"naver": "국내·네이버", "seekingalpha": "외국·SeekingAlpha"}.get(st, st)]
        if fc is None:
            tags.append("미카드화")
        items.append({"date": meta.get("date") or "", "source_type": stype, "actor": meta.get("source"),
                      "title": meta.get("title", "")[:90],
                      "n_cards": None, "n_new": fc["new"] if fc else 0, "n_matched": fc["matched"] if fc else 0,
                      "stress_survived": sum(1 for fid, v in verdicts.items() if v == "survived"),
                      "candidate": len(cand), "tags": tags})
    items.sort(key=lambda x: str(x["date"]))
    return {"id": "live", "label": f"③ 라이브 — PLAY43 신규 수집 {len(items)}건",
            "note": "계속 최신만 가져옴(증분). 카드화→스트레스→통과 시 v5 라이브러리 진화.", "items": items}


def build():
    v4n = json.loads(V4_LIB.read_text(encoding="utf-8")).get("total_functions", 87)
    vw = json.loads(V5_WORKING.read_text(encoding="utf-8")) if V5_WORKING.exists() else {}
    eras = [era_origin(), era_bootstrap(), era_live()]
    data = {
        "generated_at": str(datetime.datetime.now().replace(microsecond=0)),
        "summary": {
            "official_functions": vw.get("total_functions", v4n),
            "candidates": len(vw.get("candidates", [])),
            "v4_base": v4n,
            "bootstrap_reports": len(eras[1]["items"]),
            "live_reports": len(eras[2]["items"]),
        },
        "eras": eras,
    }
    (DATA_DIR / "timeline.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    out = PLAY43_DIR / "viewer" / "timeline.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(_HTML.replace("/*__DATA__*/", json.dumps(data, ensure_ascii=False)), encoding="utf-8")
    print(f"[timeline] {out}")
    print(f"  정식함수 {data['summary']['official_functions']} + 후보 {data['summary']['candidates']} / "
          f"부트스트랩 {data['summary']['bootstrap_reports']} / 라이브 {data['summary']['live_reports']}")


_HTML = r"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PLAY43 사고카드 팩토리 — 코퍼스 타임라인</title>
<style>
:root{--bg:#0d1117;--panel:#161b22;--line:#30363d;--tx:#e6edf3;--mut:#8b949e;
--yt:#a371f7;--kr:#58a6ff;--fg:#3fb950;--new:#3fb950;--mat:#d29922;--cut:#f85149;--cand:#db61a2}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--tx);
font:14px/1.5 -apple-system,'Segoe UI',Roboto,'Malgun Gothic',sans-serif}
header{padding:22px 26px;border-bottom:1px solid var(--line);position:sticky;top:0;background:var(--bg);z-index:5}
h1{margin:0 0 4px;font-size:19px}.sub{color:var(--mut);font-size:13px}
.kpis{display:flex;gap:18px;margin-top:12px;flex-wrap:wrap}
.kpi{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:10px 16px;min-width:96px}
.kpi b{font-size:22px;display:block}.kpi span{color:var(--mut);font-size:12px}
.filters{padding:12px 26px;display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.chip{border:1px solid var(--line);background:var(--panel);color:var(--tx);border-radius:20px;
padding:5px 13px;cursor:pointer;font-size:12.5px}.chip.off{opacity:.35}
.wrap{max-width:1000px;margin:0 auto;padding:8px 26px 70px}
.era{margin:26px 0 8px}.era h2{font-size:15px;margin:0 0 2px}.era .note{color:var(--mut);font-size:12.5px;margin-bottom:10px}
.tl{position:relative;margin-left:14px;border-left:2px solid var(--line);padding-left:22px}
.node{position:relative;margin:0 0 12px}.node::before{content:'';position:absolute;left:-29px;top:6px;
width:11px;height:11px;border-radius:50%;background:var(--kr);border:2px solid var(--bg)}
.node.youtube_kr::before{background:var(--yt)}.node.broker_kr::before{background:var(--kr)}
.node.broker_foreign::before{background:var(--fg)}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:11px 14px}
.card .top{display:flex;justify-content:space-between;gap:10px;align-items:baseline}
.actor{font-weight:600}.date{color:var(--mut);font-size:12px;white-space:nowrap}
.title{color:#c9d1d9;margin-top:3px;font-size:13px}
.badges{margin-top:7px;display:flex;gap:6px;flex-wrap:wrap}
.b{font-size:11.5px;border-radius:6px;padding:2px 8px;border:1px solid var(--line);color:var(--mut)}
.b.new{color:var(--new);border-color:#1f6f37}.b.mat{color:var(--mat);border-color:#6b5418}
.b.cut{color:var(--cut);border-color:#7a2620}.b.cand{color:var(--cand);border-color:#7a3358}
.b.src{color:var(--tx)}.legend{color:var(--mut);font-size:12px;padding:0 26px 14px}
.dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin:0 4px 0 12px;vertical-align:middle}
</style></head><body>
<header>
<h1>🏭 사고카드 팩토리 — 코퍼스 타임라인</h1>
<div class="sub" id="gen"></div>
<div class="kpis" id="kpis"></div>
</header>
<div class="legend">
<span class="dot" style="background:var(--yt)"></span>유튜브(KR)
<span class="dot" style="background:var(--kr)"></span>증권 리포트(KR)
<span class="dot" style="background:var(--fg)"></span>외국 리포트
&nbsp;·&nbsp; 배지: <b style="color:var(--new)">신규함수</b> / <b style="color:var(--mat)">기존매칭</b> / <b style="color:var(--cand)">후보보류</b> / <b style="color:var(--cut)">cut</b>
</div>
<div class="filters" id="filters"></div>
<div class="wrap" id="wrap"></div>
<script>
const DATA = /*__DATA__*/;
const S=DATA.summary;
document.getElementById('gen').textContent='생성 '+DATA.generated_at+'  ·  원본 불변, 새 리포트는 ③ 라이브에 누적';
document.getElementById('kpis').innerHTML=[
 ['정식 사고함수',S.official_functions],['후보 보류',S.candidates],
 ['부트스트랩 리포트',S.bootstrap_reports],['라이브 신규',S.live_reports]
].map(k=>`<div class="kpi"><b>${k[1]}</b><span>${k[0]}</span></div>`).join('');
const SRC={youtube_kr:'유튜브(KR)',broker_kr:'증권(KR)',broker_foreign:'외국'};
let active=new Set(Object.keys(SRC));
function render(){
 const w=document.getElementById('wrap');w.innerHTML='';
 DATA.eras.forEach(era=>{
  const items=era.items.filter(it=>active.has(it.source_type));
  if(!items.length) return;
  const d=document.createElement('div');d.className='era';
  d.innerHTML=`<h2>${era.label}</h2><div class="note">${era.note}</div>`;
  const tl=document.createElement('div');tl.className='tl';
  items.forEach(it=>{
   const badges=[];
   (it.tags||[]).forEach(t=>badges.push(`<span class="b src">${t}</span>`));
   if(it.n_cards!=null)badges.push(`<span class="b">카드 ${it.n_cards}</span>`);
   if(it.n_new)badges.push(`<span class="b new">신규함수 ${it.n_new}</span>`);
   if(it.n_matched)badges.push(`<span class="b mat">기존매칭 ${it.n_matched}</span>`);
   const n=document.createElement('div');n.className='node '+it.source_type;
   n.innerHTML=`<div class="card"><div class="top"><span class="actor">${it.actor||''}</span>
     <span class="date">${it.date||''}</span></div>
     ${it.title?`<div class="title">${it.title}</div>`:''}
     <div class="badges">${badges.join('')}</div></div>`;
   tl.appendChild(n);
  });
  d.appendChild(tl);w.appendChild(d);
 });
}
document.getElementById('filters').innerHTML=Object.entries(SRC)
 .map(([k,v])=>`<span class="chip" data-k="${k}">${v}</span>`).join('')
 +`<span style="color:var(--mut);font-size:12px;margin-left:6px">소스 토글</span>`;
document.querySelectorAll('.chip').forEach(c=>c.onclick=()=>{
 const k=c.dataset.k;if(active.has(k)){active.delete(k);c.classList.add('off')}else{active.add(k);c.classList.remove('off')}render();
});
render();
</script></body></html>"""


if __name__ == "__main__":
    build()
