"""B3. 검색 계층 — 측면별 네임스페이스에서 dense(cosine)+BM25 를 RRF(k=60)로 융합.

- 측면당 top-3. 타입별 토큰 예산:
    proposition+tool_card 합산 1,000 / exemplar top-1 만 800 상한 / procedure 검색되면 1개 전문.
- 전체 예산 1,500(procedure 제외), 초과분은 RRF 점수순 컷.
- 각 레코드에 dense 점수·BM25 순위·RRF 점수를 모두 담아 반환(진단용).

dense 는 순수 파이썬 cosine(외부 의존 0). sqlite-vec 가 있으면 가속에 쓸 수 있으나
정확도 동일하므로 기본은 파이썬 경로 — stub 백엔드로 키 없이 검증 가능하게.
"""
import json
import math
import os
import sqlite3
from collections import defaultdict
from pathlib import Path

from embed_store import DB_PATH, get_embedder, tokenize

RRF_K = 60
# off-domain 오발동 방지용 최소 dense(코사인) 하한. 0.0=무동작(기본).
# 실제 임베더(gemini) 연결 후 스모크로 튠: off-domain은 떨어지고 on-domain은 살아남는 값.
MIN_DENSE = float(os.environ.get("MIN_DENSE", "0.0"))
TOP_PER_ASPECT = 3
BUDGET_PROP_TOOL = 1000
BUDGET_EXEMPLAR = 800
BUDGET_TOTAL = 1500  # procedure 제외


def count_tokens(text):
    # 한국어 혼합 거친 근사: 토큰 ≈ 글자수/2 (예산 컷 용도로 충분).
    return max(1, len(text) // 2)


def _cosine(a, b):
    return sum(x * y for x, y in zip(a, b))  # 적재 시 정규화 가정 → 내적=코사인


def _bm25_scores(query_tokens, corpus_tokens, k1=1.5, b=0.75):
    N = len(corpus_tokens)
    if N == 0:
        return []
    avgdl = sum(len(d) for d in corpus_tokens) / N
    df = defaultdict(int)
    for d in corpus_tokens:
        for t in set(d):
            df[t] += 1
    scores = []
    for d in corpus_tokens:
        dl = len(d) or 1
        tf = defaultdict(int)
        for t in d:
            tf[t] += 1
        s = 0.0
        for q in query_tokens:
            if q not in tf:
                continue
            idf = math.log(1 + (N - df[q] + 0.5) / (df[q] + 0.5))
            s += idf * tf[q] * (k1 + 1) / (tf[q] + k1 * (1 - b + b * dl / avgdl))
        scores.append(s)
    return scores


def _load(db_path):
    con = sqlite3.connect(db_path)
    model = con.execute("SELECT v FROM meta WHERE k='embed_model'").fetchone()
    # core 는 assemble 이 무조건 포함하므로 검색 풀에서 제외(중복 채택·예산 낭비 방지).
    rows = con.execute(
        "SELECT r.id,r.type,r.text,r.aspect,r.trigger,r.tier,r.conflict_group,r.source,"
        "r.usage_count,v.embedding,v.tokens FROM records r JOIN vec_triggers v "
        "ON r.id=v.record_id WHERE r.tier!='core'"
    ).fetchall()
    con.close()
    recs = []
    for x in rows:
        recs.append({
            "id": x[0], "type": x[1], "text": x[2], "aspect": x[3], "trigger": x[4],
            "tier": x[5], "conflict_group": x[6], "source": x[7], "usage_count": x[8],
            "_vec": json.loads(x[9]), "_tok": json.loads(x[10])})
    return recs, (model[0] if model else None)


def retrieve(keys_by_aspect, db_path=DB_PATH):
    db_path = Path(db_path)
    emb = get_embedder()
    recs, stored_model = _load(db_path)
    if stored_model and stored_model != emb.name:
        raise SystemExit(
            f"임베딩 모델 불일치: DB={stored_model} != 현재={emb.name}. embed_store 재적재 필요.")

    by_aspect = defaultdict(list)
    for r in recs:
        by_aspect[r["aspect"]].append(r)

    best = {}  # record_id -> 진단 포함 레코드(최고 RRF 생존)
    for aspect, keys in keys_by_aspect.items():
        pool = by_aspect.get(aspect, [])
        if not pool or not keys:
            continue
        corpus_tokens = [r["_tok"] for r in pool]
        qvecs = emb.embed(list(keys), "RETRIEVAL_QUERY")
        agg = {}  # record idx -> {rrf, dense, bm25_rank, key}
        for key, qv in zip(keys, qvecs):
            dense = [(_cosine(qv, r["_vec"]), i) for i, r in enumerate(pool)]
            dense_rank = {i: rank for rank, (_, i) in
                          enumerate(sorted(dense, key=lambda t: -t[0]))}
            bm = _bm25_scores(tokenize(key), corpus_tokens)
            bm_rank = {i: rank for rank, (_, i) in
                       enumerate(sorted([(s, i) for i, s in enumerate(bm)], key=lambda t: -t[0]))}
            for i in range(len(pool)):
                rrf = 1.0 / (RRF_K + dense_rank[i]) + 1.0 / (RRF_K + bm_rank[i])
                cur = agg.get(i)
                if cur is None or rrf > cur["rrf"]:
                    agg[i] = {"rrf": rrf, "dense": dense[i][0],
                              "bm25_rank": bm_rank[i], "key": key}
        # 측면당 top-3 (dense 하한 미달은 off-domain 으로 보고 제외)
        ranked = [(i, d) for i, d in agg.items() if d["dense"] >= MIN_DENSE]
        top = sorted(ranked, key=lambda kv: -kv[1]["rrf"])[:TOP_PER_ASPECT]
        for i, diag in top:
            r = pool[i]
            entry = {**r, "_dense": diag["dense"], "_bm25_rank": diag["bm25_rank"],
                     "_rrf": diag["rrf"], "_aspect_matched": aspect, "_query_key": diag["key"]}
            entry.pop("_vec", None); entry.pop("_tok", None)
            if r["id"] not in best or diag["rrf"] > best[r["id"]]["_rrf"]:
                best[r["id"]] = entry

    cand = sorted(best.values(), key=lambda r: -r["_rrf"])

    # 타입별 예산 적용
    kept, dropped = [], []
    prop_tool_tok = 0
    exemplar_taken = False
    proc_taken = False
    total_tok = 0
    for r in cand:
        t = r["type"]
        tok = count_tokens(r["text"])
        if t == "procedure":
            if proc_taken:
                dropped.append({**r, "_drop": "procedure 1개 제한"}); continue
            proc_taken = True; kept.append(r); continue  # 전문 포함, 전체 예산 제외
        if t == "exemplar":
            if exemplar_taken:
                dropped.append({**r, "_drop": "exemplar top-1 제한"}); continue
            if tok > BUDGET_EXEMPLAR:
                r = {**r, "text": r["text"][:BUDGET_EXEMPLAR * 2], "_truncated": True}
                tok = count_tokens(r["text"])
            exemplar_taken = True
        elif t in ("proposition", "tool_card"):
            if prop_tool_tok + tok > BUDGET_PROP_TOOL:
                dropped.append({**r, "_drop": "prop+tool 1000토큰 예산 초과"}); continue
        if total_tok + tok > BUDGET_TOTAL:
            dropped.append({**r, "_drop": "전체 1500토큰 예산 초과"}); continue
        if t in ("proposition", "tool_card"):
            prop_tool_tok += tok
        total_tok += tok
        kept.append(r)

    return {"kept": kept, "dropped": dropped,
            "budget": {"prop_tool_tokens": prop_tool_tok, "total_tokens": total_tok}}


if __name__ == "__main__":
    demo = {"사고스타일": ["기업 밸류에이션에서 싼 가격이 밸류 트랩인지 판단할 때"],
            "도메인규칙": ["종목의 가격 시계열 데이터가 필요할 때"]}
    res = retrieve(demo)
    for r in res["kept"]:
        print(f"{r['id']} [{r['type']}|{r['_aspect_matched']}] rrf={r['_rrf']:.4f} "
              f"dense={r['_dense']:.3f} bm25#={r['_bm25_rank']}  {r['trigger'][:50]}")
