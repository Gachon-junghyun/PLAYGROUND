"""B6. 스모크 테스트 — 키 없이 stub 백엔드로 검색/조립 파이프라인 검증.

transform 은 LLM(Haiku) 이 필요하므로, 여기서는 변환 결과(측면별 행동 키)를 직접
주입해 stage 2~4(검색·조립·예산·conflict·순서)를 검증한다. 성격 다른 3건:
  1) on-domain 종목분석   → 사고스타일·도메인규칙에 직관적 레코드가 상위에 오는가
  2) on-domain 매매/출력   → exemplar(출력형식)+tool_card(도메인규칙)이 잡히는가
  3) off-domain 글쓰기     → core 외엔 거의 안 걸리는가(스코프 오발동 방지 검증)

실행:  EMBED_BACKEND=stub python smoke.py   →  logs/smoke_report.md 생성
"""
import os
from pathlib import Path

os.environ.setdefault("EMBED_BACKEND", "stub")

from embed_store import build_store
from retrieve import retrieve
from assemble import assemble

HERE = Path(__file__).resolve().parent
REPORT = HERE / "logs" / "smoke_report.md"

CASES = [
    ("종목분석 (on-domain)",
     {"사고스타일": ["기업 밸류에이션에서 싼 가격이 밸류 트랩인지 판단할 때",
                  "실적 비트를 매크로 악재 흡수 용량으로 해석할 때"],
      "도메인규칙": ["종목의 가격 시계열 데이터가 필요할 때"]},
     "현대차 3분기 실적에서 싼 밸류가 트랩인지 적대적으로 검토해줘"),
    ("매매/출력 (on-domain)",
     {"출력형식": ["매매 가설을 실행 플랜으로 옮길 때", "사고카드 형태로 분석을 작성할 때"],
      "도메인규칙": ["진입가 손익과 포지션 사이즈를 계산할 때"]},
     "이 가설대로 진입하면 손익과 몇 주 사야 하는지 플랜 만들어줘"),
    ("글쓰기 (off-domain, 스코프 검증)",
     {"사고스타일": ["헤어진 연인에게 감성적인 편지를 쓸 때"],
      "출력형식": ["개인 블로그 포스트를 작성할 때"]},
     "헤어진 연인에게 보낼 편지 써줘"),
]


def main():
    build_store()  # 카운트 리셋 위해 매번 새로 적재
    out = ["# 스모크 리포트 (EMBED_BACKEND=stub)\n"]
    for name, keys, cmd in CASES:
        res = retrieve(keys)
        asm = assemble(res, cmd)
        out.append(f"\n## {name}")
        out.append(f"- 원명령: {cmd}")
        out.append(f"- 주입 키: {keys}")
        out.append(f"- 예산: prop+tool={res['budget']['prop_tool_tokens']}tok "
                   f"total={res['budget']['total_tokens']}tok (한도 1000/1500)")
        out.append(f"- 채택 {len(asm['adopted_ids'])}개, 블록 순서: "
                   + " → ".join(f"{k}{v}" for k, v in asm['blocks'].items() if v))
        out.append("- 검색 상위(측면별 직관 점검):")
        for r in res["kept"]:
            out.append(f"    - `{r['id']}` [{r['type']}|{r['_aspect_matched']}] "
                       f"rrf={r['_rrf']:.4f} dense={r['_dense']:.3f} bm25#={r['_bm25_rank']} "
                       f"| {r['trigger']}")
        if res["dropped"]:
            out.append(f"- 예산컷 탈락 {len(res['dropped'])}개: "
                       + ", ".join(f"{r['id']}({r.get('_drop')})" for r in res["dropped"][:6]))
        if asm["conflict_log"]:
            out.append(f"- conflict 생존: {asm['conflict_log']}")
        out.append("\n  <details><summary>조립 프롬프트</summary>\n")
        out.append("```\n" + asm["prompt"] + "\n```\n  </details>")
    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text("\n".join(out), encoding="utf-8")
    print(f"[smoke] wrote {REPORT}")
    print("[smoke] cases:", ", ".join(c[0] for c in CASES))


if __name__ == "__main__":
    main()
