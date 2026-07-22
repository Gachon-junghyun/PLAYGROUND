"""뉴스 다이제스트 파이프라인 — 1회 실행으로 종합 리포트 마크다운 하나를 만든다.

핵심: **정보 누락 제로**. 샘플된 제목을 cap 으로 버리지 않고, 전부를 청크로 나눠
LLM 스크리닝에 통과시킨다(map-reduce). 최종적으로 빠지는 건 'LLM 이 보고 안 중요하다고
판단한 것'뿐이며, '본 적도 없이 잘린 것'은 없다.

흐름:
  1. sample_news: 최근 4h 뉴스에서 랜덤 frac(기본 35%) 제목 샘플
  2. 청크 스크리닝: 샘플 전체를 chunk_size 씩 LLM 에 통과 → 중요 후보 집계 (누락 없음)
  3. fetch_bodies: 중요 후보 본문 조회 (상위 important_k 는 본문, 나머지는 제목/summary)
  4. active_watchlist + text_chart: 워치리스트와 상위 종목 텍스트차트
  5. LLM 합성(스트리밍): 위 재료를 하나의 한국어 데스크 리포트로 정리
  6. reports/report_YYYYMMDD_HHMM.md 저장 (+ latest.md, state.json)

진행상황은 on_event(dict) 콜백으로 흘려서 GUI(gui.py)가 실시간으로 볼 수 있다.

CLI:
    python digest.py --once                 # 1회 실행 (LLM 호출)
    python digest.py --once --dry-run       # LLM 없이 키워드 스크리닝만 (크레딧 0)
    python digest.py --once --frac 1.0      # 35% 대신 전체(진짜 무손실)
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import sources

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = Path(__file__).parent
REPORTS_DIR = HERE / "reports"
STATE_FILE = HERE / "state.json"


class StopRequested(Exception):
    """should_stop() 가 True 를 반환하면 파이프라인을 협조적으로 중단."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _default_event(ev: dict) -> None:
    """CLI 기본 이벤트 출력. GUI 는 자체 핸들러를 넘긴다."""
    t = ev.get("type")
    if t == "stage":
        print(f"\n[{ev['stage']}] {ev.get('msg', '')}", flush=True)
    elif t == "log":
        print(f"      {ev['msg']}", flush=True)
    elif t == "delta":
        sys.stdout.write(ev["text"])
        sys.stdout.flush()
    elif t == "done":
        print(f"\n[완료] {ev['msg']}", flush=True)
    elif t == "error":
        print(f"\n[오류] {ev['msg']}", flush=True)


def _check_stop(should_stop):
    if should_stop and should_stop():
        raise StopRequested()


# ── 스크리닝 ────────────────────────────────────────────────────────────────

def _heuristic_pick(titles: list[str], wl_terms: list[str]) -> list[int]:
    """LLM 없이(=dry-run/폴백): 워치리스트 용어가 제목에 등장하는 것."""
    terms = [t.lower() for t in wl_terms if t]
    out = []
    for i, t in enumerate(titles):
        low = t.lower()
        if any(term in low for term in terms):
            out.append(i)
    return out


def _llm_pick_chunk(titles: list[str], wl_terms: list[str], emit, model=None) -> list[int]:
    """한 청크(제목 리스트)에서 시장에 중요한 것의 index 를 LLM 이 고른다. 실패 시 휴리스틱."""
    from nv_client import chat

    numbered = "\n".join(f"{i}: {t}" for i, t in enumerate(titles))
    terms = ", ".join(wl_terms[:40]) or "(없음)"
    system = ("너는 뉴스 선별가다. 제목 중 '설명할 가치가 있는 중요한 뉴스·시사'를 고른다 — "
              "거시경제·정책·금리·지정학·산업/기술 동향·주요 기업/시장 이벤트 등. "
              "연예/스포츠/가십/광고/중복/의미 없는 단순시황은 버린다.")
    user = (f"사용자 관심 키워드/티커(가중치): {terms}\n\n"
            f"아래 제목 중 지금 이해할 가치가 있는 중요 뉴스의 번호만 골라라. "
            f"위 관심사와 관련되면 우선 포함하되, 관심사 밖이라도 시사적으로 중요하면 포함해라. "
            f"JSON 정수 배열만 출력. 예: [1, 5, 9]\n\n{numbered}")
    try:
        _, text = chat(user, system=system, max_tokens=300, temperature=0.1,
                       verbose=False, models=[model] if model else None)
        m = re.search(r"\[[\d,\s]*\]", text)
        if m:
            idxs = json.loads(m.group(0))
            return [i for i in idxs if isinstance(i, int) and 0 <= i < len(titles)]
    except Exception as e:
        emit({"type": "log", "msg": f"청크 LLM 실패 → 휴리스틱 폴백: {e}"})
    return _heuristic_pick(titles, wl_terms)


def screen_all(sampled: list[dict], wl_terms: list[str], chunk_size: int,
               dry_run: bool, emit, should_stop, model=None) -> list[int]:
    """샘플 전체를 청크로 나눠 스크리닝. 버리는 제목 없이 전부 LLM(또는 휴리스틱)에 통과.

    중요 후보의 (원본 sampled 기준) 전역 index 리스트를 반환한다.
    """
    titles = [s["title"] for s in sampled]
    n = len(titles)
    if n == 0:
        return []
    n_chunks = math.ceil(n / chunk_size)
    picked: list[int] = []
    for ci in range(n_chunks):
        _check_stop(should_stop)
        start = ci * chunk_size
        batch = titles[start:start + chunk_size]
        mode = "휴리스틱" if dry_run else "LLM"
        emit({"type": "log", "msg": f"스크리닝 {mode} 청크 {ci + 1}/{n_chunks} "
                                    f"(제목 {start + 1}~{start + len(batch)}) ..."})
        local = (_heuristic_pick(batch, wl_terms) if dry_run
                 else _llm_pick_chunk(batch, wl_terms, emit, model=model))
        picked.extend(start + i for i in local)
        emit({"type": "log", "msg": f"  → 이 청크에서 {len(local)}건 중요, 누적 {len(picked)}건"})
    return picked


# ── 재료 수집 ────────────────────────────────────────────────────────────────

def _watchlist_terms(wl: list[dict]) -> list[str]:
    terms = []
    for w in wl:
        terms.extend(str(t) for t in w.get("tickers", []))
        item = (w.get("item") or "").strip()
        if item:
            terms.append(item.split("(")[0].split()[0][:12])
    seen, out = set(), []
    for t in terms:
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return out


def gather(window_hours, frac, chunk_size, important_k, chart_tickers,
           dry_run, seed, emit, should_stop, screen_model=None):
    emit({"type": "stage", "stage": "1/4 뉴스 샘플링", "msg": ""})
    sampled, stats = sources.sample_news(window_hours, frac, cap=10 ** 9, seed=seed)
    emit({"type": "log", "msg": f"풀 {stats['pool_total']}건 → {int(frac * 100)}% 샘플 "
                                f"{stats['used']}건 (전부 스크리닝, 사전 절단 없음)"})

    emit({"type": "stage", "stage": "2/4 워치리스트", "msg": ""})
    wl = sources.active_watchlist(limit=30)
    wl_terms = _watchlist_terms(wl)
    emit({"type": "log", "msg": f"active {len(wl)}건, 키워드 {len(wl_terms)}개"})

    emit({"type": "stage", "stage": "3/4 중요 뉴스 선별 (무손실 청크 스크리닝)", "msg": ""})
    picked_idx = screen_all(sampled, wl_terms, chunk_size, dry_run, emit,
                            should_stop, model=screen_model)
    important = [sampled[i] for i in picked_idx]
    # 상위 important_k 만 본문을 읽는다(토큰 관리). 나머지 중요건은 제목/summary 로 합성에 포함.
    body_targets = important[:important_k]
    bodies = sources.fetch_bodies([s["url_hash"] for s in body_targets])
    for s in important:
        s["body"] = bodies.get(s["url_hash"], "")
    emit({"type": "log", "msg": f"중요 후보 {len(important)}건 (본문 {len(bodies)}건 확보, "
                                f"나머지는 제목/summary 로 반영)"})

    emit({"type": "stage", "stage": f"4/4 텍스트차트 (상위 {chart_tickers}종목)", "msg": ""})
    charts, used = [], []
    for w in wl:
        if len(used) >= chart_tickers:
            break
        for tk in w.get("tickers", []):
            _check_stop(should_stop)
            if tk in used or len(used) >= chart_tickers:
                continue
            emit({"type": "log", "msg": f"차트 요청: {tk} ..."})
            ch = sources.text_chart(tk)
            used.append(tk)
            if ch:
                charts.append(ch)
    emit({"type": "log", "msg": f"차트 {len(charts)}개 생성 (시도 {len(used)}종목)"})

    return {"sampled": sampled, "stats": stats, "watchlist": wl,
            "important": important, "charts": charts, "n_bodies": len(bodies)}


# ── 합성 ────────────────────────────────────────────────────────────────────

def _build_synthesis_prompt(ctx: dict) -> tuple[str, str]:
    wl_block = "\n".join(
        f"- [{w['importance']}] {w['item']}  (티커 {w.get('tickers')})"
        f"\n    트리거: {(w.get('trigger_criteria') or '').strip()[:200]}"
        for w in ctx["watchlist"]
    )
    with_body = [s for s in ctx["important"] if s.get("body")]
    no_body = [s for s in ctx["important"] if not s.get("body")]
    imp_block = "\n\n".join(
        f"### {s['title']}  ({s.get('source', '')})\n{s['body'][:1200]}" for s in with_body
    ) or "(본문 확보된 중요 뉴스 없음)"
    more_imp = "\n".join(
        f"- {s['title']}  — {(s.get('summary') or '').strip()[:160]}" for s in no_body[:150]
    ) or "(없음)"
    charts_block = "\n\n".join(ctx["charts"]) or "(차트 없음)"

    system = (
        "너는 뉴스·시사 해설자다. 오늘 수집된 뉴스를 한국의 일반 투자자/독자가 이해하도록 "
        "'무슨 일이 일어났는지 → 배경과 맥락 → 왜 중요하고 무엇에 영향을 주는지'를 쉬우면서도 "
        "깊이 있게 설명한다. 전문용어는 풀어 쓰고, 사건들을 연결해 큰 그림을 보여준다.\n"
        "규칙(엄수): (1) 구체적 수치(가격·환율·지수·%·날짜·인명·직함)는 **재료에 실제로 있는 것만** "
        "인용한다. 재료에 없으면 숫자를 만들지 말고 '유가 급등' 같은 정성적 표현으로 쓰거나 생략한다. "
        "(2) 배경 설명에 일반 상식을 쓸 수 있으나, 재료로 확인 안 된 최신 사실을 단정하지 마라 "
        "('~로 알려져 있다/일반적으로' 로 구분). (3) 사실과 해석(네 추론)을 분리해서 써라."
    )
    user = f"""아래 재료로, '뉴스·시사 해설'에 초점을 둔 한국어 브리핑을 작성해라.
(최근 수집 {ctx['stats']['used']}건 전량을 스크리닝해 중요 {len(ctx['important'])}건을 추렸다.)
핵심은 **설명**이다 — 독자가 이 글만 읽어도 지금 세상에서 무슨 일이 벌어지는지 이해하게.

# 중요 뉴스 — 본문 확보 (해설의 주 재료)
{imp_block}

# 중요 뉴스 — 제목/요약만 (흐름 파악용)
{more_imp}

# 참고: 사용자 워치리스트 (관심 종목/테마 — 해설을 이 관심사와 연결할 때만 사용)
{wl_block}

# 참고: 워치리스트 종목 텍스트차트
{charts_block}

---
아래 형식으로 작성(설명 중심, 각 이슈는 충분히 풀어서):
## 한 줄 요약
## 오늘의 핵심 이슈  (3~6개. 각 이슈마다 → **무슨 일**인지 / **배경·맥락**(왜 지금, 어떤 흐름 속에서) / **왜 중요한가·파급**을 문단으로 설명. 전문용어는 괄호로 풀이)
## 흐름과 맥락  (개별 뉴스를 관통하는 큰 그림·시사 해설 — 사건들을 하나의 서사로 연결)
## 내 관심사와의 연결  (위 뉴스가 워치리스트 종목/테마에 주는 함의. 근거 명시. 관련 없으면 '뚜렷한 연결 없음')
## 차트 한눈에  (텍스트차트에서 읽히는 것만 간단히)
## 지금 눈여겨볼 것  (다음 4시간~며칠 체크포인트)
근거 없는 단정 금지. 사실과 해석을 구분해서 써라."""
    return system, user


def run_once(window_hours=4.0, frac=0.35, chunk_size=200, important_k=15,
             chart_tickers=6, dry_run=False, seed=None, on_event=None,
             should_stop=None, screen_model=None, synth_model=None) -> Path:
    """다이제스트 1회 실행 → 저장된 리포트 경로 반환. on_event(dict) 로 진행상황 방출.

    screen_model / synth_model 로 스크리닝·합성 모델을 각각 고정할 수 있다(None=기본 체인).
    """
    emit = on_event or _default_event
    REPORTS_DIR.mkdir(exist_ok=True)
    try:
        ctx = gather(window_hours, frac, chunk_size, important_k, chart_tickers,
                     dry_run, seed, emit, should_stop, screen_model=screen_model)

        stamp = datetime.now().strftime("%Y%m%d_%H%M")
        header = (f"# 뉴스 다이제스트 — {_now_iso()}\n\n"
                  f"- 윈도우 최근 {window_hours}h · 풀 {ctx['stats']['pool_total']}건 · "
                  f"샘플 {ctx['stats']['used']}건({int(frac * 100)}%, 전량 스크리닝) · "
                  f"중요 {len(ctx['important'])}건(본문 {ctx['n_bodies']}) · "
                  f"차트 {len(ctx['charts'])}개\n\n")

        system, user = _build_synthesis_prompt(ctx)
        if dry_run:
            emit({"type": "stage", "stage": "합성", "msg": "dry-run: LLM 생략, 재료 저장"})
            body = header + "> (DRY-RUN: 합성 안 함. 아래는 LLM 에 넘길 재료)\n\n" + user
            model_note = "dry-run (LLM 미호출)"
        else:
            emit({"type": "stage", "stage": "합성", "msg": "LLM 스트리밍 종합..."})
            from nv_client import chat, SYNTH_CHAIN
            model, text = chat(user, system=system, max_tokens=3500, temperature=0.35,
                               stream=True,
                               models=[synth_model] if synth_model else SYNTH_CHAIN,
                               on_delta=lambda p, k: emit(
                                   {"type": "delta", "text": p, "kind": k}))
            body = header + text
            model_note = model

        out = REPORTS_DIR / f"report_{stamp}.md"
        final = body + f"\n\n---\n_모델: {model_note}_\n"
        out.write_text(final, encoding="utf-8")
        (REPORTS_DIR / "latest.md").write_text(final, encoding="utf-8")
        STATE_FILE.write_text(json.dumps({"last_run": _now_iso(), "report": out.name},
                                         ensure_ascii=False, indent=2), encoding="utf-8")
        emit({"type": "done", "msg": str(out)})
        return out
    except StopRequested:
        emit({"type": "error", "msg": "사용자 중단(Stop)"})
        raise


def main():
    ap = argparse.ArgumentParser(description="뉴스+워치리스트+차트 종합 다이제스트 1회 실행")
    ap.add_argument("--once", action="store_true", help="1회 실행(기본 동작)")
    ap.add_argument("--window-hours", type=float, default=4.0)
    ap.add_argument("--frac", type=float, default=0.35, help="제목 랜덤 샘플 비율(1.0=전체)")
    ap.add_argument("--chunk-size", type=int, default=200, help="스크리닝 청크당 제목 수")
    ap.add_argument("--important-k", type=int, default=15, help="본문 읽을 상위 중요 뉴스 수")
    ap.add_argument("--chart-tickers", type=int, default=6, help="텍스트차트 생성 종목 수")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--screen-model", default=None, help="스크리닝 모델 고정(기본 체인 대신)")
    ap.add_argument("--synth-model", default=None,
                    help="합성 모델 고정. 깊이 원하면 deepseek-ai/deepseek-v4-pro (느림)")
    ap.add_argument("--dry-run", action="store_true",
                    help="LLM 없이 키워드 스크리닝만 (크레딧 0, 배관 검증용)")
    args = ap.parse_args()
    run_once(args.window_hours, args.frac, args.chunk_size, args.important_k,
             args.chart_tickers, args.dry_run, args.seed,
             screen_model=args.screen_model, synth_model=args.synth_model)


if __name__ == "__main__":
    main()
