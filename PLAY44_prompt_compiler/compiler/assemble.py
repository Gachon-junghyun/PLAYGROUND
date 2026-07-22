"""B4. 조립 계층 — LLM 호출 없는 순수 코드.

1. tier=core 무조건 포함
2. 검색 레코드 추가
3. 같은 conflict_group 내에서는 RRF 최고 하나만 생존(core 는 항상 생존)
4. 배치 순서: [core → 작업유형 → 도메인규칙(tool_card·procedure) → 사고스타일 → 출력형식 → 원명령]
   — 출력형식을 원명령 직전에 두는 것은 lost-in-the-middle 대응.
5. 채택된 레코드의 usage_count +1

procedure 라우팅 훅: MVP 는 procedure 전문을 컨텍스트에 주입한다. 단계 실패가 후속
단계를 무효화하는 절차는 추후 오케스트레이터가 단계별 분리 실행하도록 아래
`procedure_hook` 자리를 비워 둔다(현재는 패스스루).
"""
import sqlite3
from pathlib import Path

from embed_store import DB_PATH


def procedure_hook(proc_record):
    """추후 단계별 분리 실행 진입점. 지금은 전문 패스스루."""
    return proc_record["text"]


def _load_core(con):
    rows = con.execute(
        "SELECT id,type,text,aspect,trigger,tier,conflict_group,source,usage_count "
        "FROM records WHERE tier='core'").fetchall()
    cols = ["id", "type", "text", "aspect", "trigger", "tier", "conflict_group", "source", "usage_count"]
    return [dict(zip(cols, r)) for r in rows]


def _bucket(rec):
    if rec["type"] in ("tool_card", "procedure") or rec["aspect"] == "도메인규칙":
        return "도메인규칙"
    return rec["aspect"]  # 작업유형 / 사고스타일 / 출력형식


def assemble(retrieved, command, db_path=DB_PATH):
    db_path = Path(db_path)
    con = sqlite3.connect(db_path)
    core = _load_core(con)
    kept = retrieved["kept"]

    # 3) conflict_group 생존: core 우선, 그 외 RRF 최고. group 이 None 이면 모두 통과.
    survivors, conflict_log = [], []
    by_group = {}
    seen = set()
    for r in core + kept:
        if r["id"] in seen:        # id 중복 방어(core/검색 겹침)
            continue
        seen.add(r["id"])
        g = r.get("conflict_group")
        if not g:
            survivors.append(r); continue
        champ = by_group.get(g)
        is_core = r.get("tier") == "core"
        score = float("inf") if is_core else r.get("_rrf", 0.0)
        if champ is None or score > champ[0]:
            if champ is not None:
                conflict_log.append({"group": g, "dropped": champ[1]["id"], "kept": r["id"]})
            by_group[g] = (score, r)
        else:
            conflict_log.append({"group": g, "dropped": r["id"], "kept": champ[1]["id"]})
    survivors.extend(v[1] for v in by_group.values())

    # 4) 순서 배치
    order = ["core_block", "작업유형", "도메인규칙", "사고스타일", "출력형식"]
    blocks = {k: [] for k in order}
    for r in survivors:
        if r.get("tier") == "core":
            blocks["core_block"].append(r)
        else:
            blocks.setdefault(_bucket(r), []).append(r)

    LABEL = {"core_block": "## 핵심 원칙(항상 적용)", "작업유형": "## 작업 성격",
             "도메인규칙": "## 도메인 규칙·도구", "사고스타일": "## 사고 스타일",
             "출력형식": "## 출력 형식"}
    parts = []
    for k in order:
        items = blocks.get(k) or []
        if not items:
            continue
        parts.append(LABEL[k])
        for r in items:
            body = procedure_hook(r) if r["type"] == "procedure" else r["text"]
            parts.append(f"- {body}")
    parts.append("## 요청")
    parts.append(command.strip())
    prompt = "\n".join(parts)

    # 5) usage_count +1 (채택분)
    adopted_ids = [r["id"] for r in survivors]
    con.executemany("UPDATE records SET usage_count=usage_count+1 WHERE id=?",
                    [(i,) for i in adopted_ids])
    con.commit(); con.close()

    return {"prompt": prompt, "adopted_ids": adopted_ids, "conflict_log": conflict_log,
            "blocks": {k: [r["id"] for r in (blocks.get(k) or [])] for k in order}}


if __name__ == "__main__":
    from retrieve import retrieve
    r = retrieve({"사고스타일": ["싼 가격이 밸류 트랩인지 판단할 때"]})
    out = assemble(r, "현대차 밸류에이션 점검해줘")
    print(out["prompt"])
    print("\n--- adopted:", out["adopted_ids"])
