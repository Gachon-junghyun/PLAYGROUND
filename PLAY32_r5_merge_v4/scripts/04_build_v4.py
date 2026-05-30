"""Phase 4: dup_pairs.jsonl + level_audit.md를 적용해 r5_v4_thinking_functions.json 생성.

처리 규칙:
1. dup_pairs.jsonl merge → primary에 흡수된 함수의 source_cards 추가, 흡수된 함수 제거
2. dup_pairs.jsonl link → primary의 related_functions에 link 대상 추가
3. level_audit.md fail → standalone fail 함수는 정식 등재 제외 (rejected.jsonl 별도)
4. function_id 재할당:
   - A 풀 F01~F44 보존 (머지 primary로 받았으면 그대로)
   - B 풀 정식 등재: F45부터 순차 (출현 순)
5. B 풀에 R6 빈 layer 추가 (data_sources, indicators, action_at_trigger, backtest_log, indicators_examples_specific)
6. 메타데이터 v3 → v4 갱신

산출물:
- data/r5_v4_thinking_functions.json — v4 정식 등재
- data/rejected.jsonl — fail standalone (재작성 또는 폐기 대상)
- data/absorbed.jsonl — 머지로 흡수된 B 함수 (이력)
- data/merge_report.md — 사람용 변경 요약
"""
import json
import os
import re
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POOL = os.path.join(ROOT, "data", "pool_combined.jsonl")
DUP = os.path.join(ROOT, "data", "dup_pairs.jsonl")
AUDIT = os.path.join(ROOT, "data", "level_audit.md")
OUT_V4 = os.path.join(ROOT, "data", "r5_v4_thinking_functions.json")
OUT_REJECTED = os.path.join(ROOT, "data", "rejected.jsonl")
OUT_ABSORBED = os.path.join(ROOT, "data", "absorbed.jsonl")
OUT_REPORT = os.path.join(ROOT, "data", "merge_report.md")

R6_EMPTY = {
    "data_sources": [],
    "indicators": [],
    "action_at_trigger": {},
    "backtest_log": [],
    "indicators_examples_specific": [],
}


def load_pool():
    funcs = {}
    order_a, order_b = [], []
    with open(POOL, "rb") as f:
        for line in f:
            fn = json.loads(line)
            fid = fn["function_id"]
            funcs[fid] = fn
            if fn["_origin"] == "A_mvp_v3":
                order_a.append(fid)
            else:
                order_b.append(fid)
    return funcs, order_a, order_b


def load_dup_pairs():
    merges = []
    links = []
    with open(DUP, "rb") as f:
        for line in f:
            if not line.strip():
                continue
            d = json.loads(line)
            if d.get("decision") == "merge":
                merges.append(d)
            elif d.get("decision") == "link":
                links.append(d)
    return merges, links


def parse_audit_fail():
    """level_audit.md에서 fail 함수 ID 집합 추출."""
    fail = set()
    with open(AUDIT, "rb") as f:
        for line in f:
            line = line.decode("utf-8")
            m = re.match(r"^### (\S+) \| fail$", line.strip())
            if m:
                fail.add(m.group(1))
    return fail


def apply_merges(funcs, merges):
    """merge 적용: primary에 흡수된 source_cards 추가, 흡수된 함수는 제거 대상으로 표시."""
    absorbed_ids = set()
    absorbed_log = []  # (absorbed_id, primary_id, reason)
    for m in merges:
        primary = m["primary"]
        if primary not in funcs:
            print(f"WARN: merge cluster {m.get('cluster_id')} primary {primary} not in pool — skip")
            continue
        for member in m["members"]:
            if member == primary:
                continue
            if member not in funcs:
                print(f"WARN: merge cluster {m.get('cluster_id')} member {member} not in pool — skip")
                continue
            # add member.source_cards to primary
            p_cards = set(funcs[primary].get("source_cards", []))
            p_cards.update(funcs[member].get("source_cards", []))
            funcs[primary]["source_cards"] = sorted(p_cards)
            funcs[primary]["source_card_count"] = len(p_cards)
            # also merge applies_to_domain (extend, dedup, preserve order)
            p_doms = list(funcs[primary].get("applies_to_domain", []))
            for d in funcs[member].get("applies_to_domain", []):
                if d not in p_doms:
                    p_doms.append(d)
            funcs[primary]["applies_to_domain"] = p_doms
            absorbed_ids.add(member)
            absorbed_log.append({
                "absorbed": member,
                "primary": primary,
                "cluster_id": m.get("cluster_id"),
                "reason": m.get("reason", ""),
                "absorbed_origin": funcs[member]["_origin"],
            })
    return absorbed_ids, absorbed_log


def apply_links(funcs, links, id_map):
    """link 적용: 양방향으로 related_functions에 추가. id_map은 임시→정식 매핑."""
    for l in links:
        a = l.get("from")
        b = l.get("to")
        if not (a and b):
            continue
        # 머지로 사라진 함수면 skip
        a_final = id_map.get(a)
        b_final = id_map.get(b)
        if not a_final or not b_final:
            continue
        for x, y in [(a_final, b_final), (b_final, a_final)]:
            related = funcs[x].setdefault("related_functions", [])
            if y not in related:
                related.append(y)


def reassign_ids(funcs, order_a, order_b, absorbed_ids, fail_ids):
    """function_id 재할당.
    - A: F01~F44 유지 (절대 변경 금지)
    - B (정식 등재): F45부터 순차, 출현 순(order_b 유지)
    - 흡수된 B: 매핑 = primary의 (재할당된) ID
    - fail standalone B: 매핑 없음 (rejected)
    """
    id_map = {}  # 원본 ID → 최종 ID

    # A: 그대로
    for fid in order_a:
        id_map[fid] = fid

    # B 정식 등재 후보 (흡수 안 됨 + fail 아님)
    next_fid = 45
    for fid in order_b:
        if fid in absorbed_ids:
            continue  # 흡수된 건 별도 매핑
        if fid in fail_ids:
            continue  # fail standalone은 v4에서 제외
        new_id = f"F{next_fid:02d}"
        id_map[fid] = new_id
        next_fid += 1

    # 흡수된 함수는 primary의 매핑을 따라감
    # primary 자체가 B면 위에서 이미 매핑됨 → 흡수된 멤버도 primary의 새 ID로 매핑
    # 두 패스 필요
    return id_map


def build_v4(funcs, id_map, order_a, order_b, absorbed_ids, fail_ids, merges, links):
    """v4 함수 리스트 생성."""
    v4_funcs = []

    # A 풀 (F01~F44)
    for fid in order_a:
        fn = dict(funcs[fid])
        fn.pop("_origin", None)
        fn.pop("_origin_file", None)
        fn.pop("_origin_batch", None)
        # related_functions 정리 (id_map 적용)
        rel = fn.get("related_functions", [])
        fn["related_functions"] = [id_map.get(r, r) for r in rel]
        v4_funcs.append(fn)

    # B 풀 (F45+), 정식 등재만
    for fid in order_b:
        if fid in absorbed_ids or fid in fail_ids:
            continue
        fn = dict(funcs[fid])
        fn["function_id"] = id_map[fid]
        # related_functions: 임시 ID → 최종 ID
        rel = fn.get("related_functions", [])
        fn["related_functions"] = [id_map.get(r, r) for r in rel if id_map.get(r, r) != fn["function_id"]]
        # R6 빈 layer 추가 (없는 키만)
        for k, v in R6_EMPTY.items():
            if k not in fn:
                fn[k] = v
        fn.pop("_origin", None)
        fn.pop("_origin_file", None)
        fn.pop("_origin_batch", None)
        v4_funcs.append(fn)

    # link 적용 (id_map 통해 최종 ID로)
    v4_index = {fn["function_id"]: fn for fn in v4_funcs}
    for l in links:
        a = l.get("from")
        b = l.get("to")
        a_final = id_map.get(a)
        b_final = id_map.get(b)
        if not a_final or not b_final:
            continue
        if a_final not in v4_index or b_final not in v4_index:
            continue
        for x, y in [(a_final, b_final), (b_final, a_final)]:
            rel = v4_index[x].setdefault("related_functions", [])
            if y not in rel:
                rel.append(y)

    return v4_funcs


def main():
    funcs, order_a, order_b = load_pool()
    print(f"loaded pool: A={len(order_a)} B={len(order_b)}")

    merges, links = load_dup_pairs()
    print(f"dup_pairs: merges={len(merges)} links={len(links)}")

    fail_ids = parse_audit_fail()
    print(f"fail: {sorted(fail_ids)}")

    absorbed_ids, absorbed_log = apply_merges(funcs, merges)
    print(f"absorbed: {len(absorbed_ids)}")

    id_map = reassign_ids(funcs, order_a, order_b, absorbed_ids, fail_ids)
    # absorbed 멤버는 primary의 새 ID로 매핑
    for entry in absorbed_log:
        entry["primary_new_id"] = id_map.get(entry["primary"], entry["primary"])
        id_map[entry["absorbed"]] = entry["primary_new_id"]

    v4_funcs = build_v4(funcs, id_map, order_a, order_b, absorbed_ids, fail_ids, merges, links)
    print(f"v4 정식 등재: {len(v4_funcs)}")

    # rejected (fail standalone)
    rejected = []
    for fid in order_b:
        if fid in fail_ids and fid not in absorbed_ids:
            fn = dict(funcs[fid])
            fn["_rejected_reason"] = "fail in level_audit"
            rejected.append(fn)
    print(f"rejected: {len(rejected)}")
    print(f"absorbed_log: {len(absorbed_log)}")

    # 메타데이터
    v4_doc = {
        "dataset_name": "r5_thinking_functions",
        "version": "v4",
        "created_at": "2026-05-19",
        "updated_at": "2026-05-27",
        "source": "PLAY32_r5_merge_v4: mvp R5 v3 (44) + PLAY31 신규 (66) 결합, 중복 제거 + 레벨 검증",
        "external_catalogs": {
            "data_sources": "r6_data_sources.json (34 sources)",
            "indicators": "r6_indicators.json (120 KPIs, v2)",
            "action_templates": "r6_action_templates.json (22 actions)",
        },
        "principles": [
            "시점 독립 — 사건이 outdated 돼도 함수는 영구 유효",
            "사고 함수 단위 — 카드 ID·사건 이름 아닌 점프 구조",
            "추상화 균형 — 너무 일반(무용) 또는 너무 구체(시점 종속) 회피",
            "단일 카드 함수도 보존 — 강제 클러스터링 금지",
            "자동 템플릿 금지 패턴 위반 X",
            "실행 가능 layer (R6) — data_sources/indicators/action_at_trigger/backtest_log",
        ],
        "total_functions": len(v4_funcs),
        "card_coverage": {
            "comment": "A 풀(E*)과 B 풀(B*) source_cards 혼재. Phase 5에서 코퍼스별 분리 인덱싱 필요.",
        },
        "merge_summary": {
            "absorbed_from_B": len(absorbed_log),
            "rejected_from_B": len(rejected),
            "B_standalone_promoted_to_F45_plus": len([f for f in order_b if f not in absorbed_ids and f not in fail_ids]),
            "links_added": len(links),
        },
        "schema_change_history": [
            "v1 -> v2: data_sources, indicators, action_at_trigger, backtest_log 4필드 추가 (R6 layer)",
            "v2 -> v3: indicators 필드 Tier 1 abstract 재매핑 + indicators_examples_specific 분리",
            "v3 -> v4: mvp R5 v3 (44) + PLAY31 신규 (66) 결합. B 19개 흡수, 4개 reject, 43개 신규 등재 → 총 87 함수",
        ],
        "functions": v4_funcs,
    }

    with open(OUT_V4, "w", encoding="utf-8") as f:
        json.dump(v4_doc, f, ensure_ascii=False, indent=2)
    print(f"wrote {OUT_V4}")

    with open(OUT_REJECTED, "w", encoding="utf-8") as f:
        for r in rejected:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {OUT_REJECTED}")

    with open(OUT_ABSORBED, "w", encoding="utf-8") as f:
        for a in absorbed_log:
            f.write(json.dumps(a, ensure_ascii=False) + "\n")
    print(f"wrote {OUT_ABSORBED}")

    # merge_report.md
    with open(OUT_REPORT, "w", encoding="utf-8") as f:
        f.write("# PLAY32 v4 Merge Report\n\n")
        f.write(f"## 요약\n")
        f.write(f"- 입력 풀: A 44 + B 66 = 110\n")
        f.write(f"- 머지 클러스터: {len(merges)} (흡수된 B: {len(absorbed_log)}개)\n")
        f.write(f"- 링크 쌍: {len(links)}\n")
        f.write(f"- 레벨 검증 fail: {len(fail_ids)} (standalone fail로 rejected: {len(rejected)})\n")
        f.write(f"- **v4 정식 등재: {len(v4_funcs)} 함수**\n\n")

        f.write(f"## 흡수 매핑 (B → primary)\n\n")
        f.write(f"| 흡수된 B | primary (원본 → 최종 ID) | cluster | reason |\n")
        f.write(f"|---|---|---|---|\n")
        for e in absorbed_log:
            f.write(f"| {e['absorbed']} | {e['primary']} → {e['primary_new_id']} | {e['cluster_id']} | {e['reason'][:80]} |\n")

        f.write(f"\n## Rejected (fail standalone)\n\n")
        for r in rejected:
            f.write(f"- **{r['function_id']}** ({r.get('_origin_batch','?')}): {r['name']}\n")

        f.write(f"\n## 신규 정식 등재 (B → F45+)\n\n")
        f.write(f"| 원본 ID | 최종 ID | name |\n")
        f.write(f"|---|---|---|\n")
        for fid in order_b:
            if fid not in absorbed_ids and fid not in fail_ids:
                new_id = id_map.get(fid)
                name = funcs[fid].get("name", "")[:80]
                f.write(f"| {fid} | {new_id} | {name} |\n")

        f.write(f"\n## Link 쌍 (related_functions로 연결)\n\n")
        for l in links:
            a = l.get("from")
            b = l.get("to")
            a_final = id_map.get(a, a)
            b_final = id_map.get(b, b)
            f.write(f"- {a} ({a_final}) ↔ {b} ({b_final}): {l.get('reason','')[:100]}\n")
    print(f"wrote {OUT_REPORT}")


if __name__ == "__main__":
    main()
