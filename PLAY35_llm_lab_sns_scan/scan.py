# FILE: PLAY35_llm_lab_sns_scan/scan.py
# LLM lab SNS 스캔의 "결정론적 플러밍" CLI.
# 조사(웹서치)는 Claude Code 세션이 subagent로 하고(PROTOCOL.md 참고),
# 이 스크립트는 그 결과 JSON을 읽어 합치고 report.md로 렌더하기만 한다.
#
# 사용:
#   python scan.py labs                # lab 설정(JSON) 출력 — subagent에게 먹일 입력
#   python scan.py validate            # results/*.json 스키마 점검
#   python scan.py collect             # results/*.json → report.md 렌더
#
# 외부 의존성 없음(표준 라이브러리만). Python 3.8+.

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

HERE = Path(__file__).parent
LABS_FILE = HERE / "labs.json"
RESULTS_DIR = HERE / "results"
REPORT_FILE = HERE / "report.md"

# results/<slug>.json 한 개가 가져야 할 필수 키. subagent 출력 계약 = PROTOCOL.md의 스키마.
REQUIRED_KEYS = ("lab", "official_accounts", "people")

if hasattr(sys.stdout, "reconfigure"):  # Windows cp949 콘솔 한글 깨짐 방지
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def load_labs():
    return json.loads(LABS_FILE.read_text(encoding="utf-8"))


def load_results():
    """results/*.json 전부 로드. (filename, dict) 리스트. 깨진 파일은 경고 후 스킵."""
    out = []
    if not RESULTS_DIR.exists():
        return out
    for f in sorted(RESULTS_DIR.glob("*.json")):
        try:
            out.append((f.name, json.loads(f.read_text(encoding="utf-8"))))
        except Exception as e:
            print(f"[warn] {f.name} 파싱 실패 — 스킵: {e}", file=sys.stderr)
    return out


def cmd_labs(args):
    print(json.dumps(load_labs(), ensure_ascii=False, indent=2))


def cmd_validate(args):
    results = load_results()
    if not results:
        print("[validate] results/*.json 없음. 먼저 subagent 조사 결과를 저장하라.")
        return 1
    ok = True
    for name, data in results:
        missing = [k for k in REQUIRED_KEYS if k not in data]
        n_people = len(data.get("people", []) or [])
        n_acct = len(data.get("official_accounts", []) or [])
        if missing:
            ok = False
            print(f"[FAIL] {name}: 필수 키 누락 {missing}")
        else:
            print(f"[ok]   {name}: lab='{data.get('lab')}' 공식계정 {n_acct}개, 인물 {n_people}명")
    return 0 if ok else 1


def _fmt_accounts(accounts):
    """[{platform, handle, url, verified?}] → 한 줄 문자열."""
    parts = []
    for a in accounts or []:
        h = a.get("handle") or a.get("url") or "?"
        plat = a.get("platform", "")
        v = " ✓" if a.get("verified") else ""
        url = a.get("url")
        label = f"{plat}:{h}{v}" if plat else f"{h}{v}"
        parts.append(f"[{label}]({url})" if url else label)
    return ", ".join(parts) if parts else "—"


def cmd_collect(args):
    results = load_results()
    if not results:
        print("[collect] results/*.json 없음. 렌더할 게 없다.")
        return 1

    # lab 순서는 labs.json 순서를 따르고, 없는 건 뒤에 알파벳순.
    order = {l["lab"]: i for i, l in enumerate(load_labs())}
    results.sort(key=lambda x: (order.get(x[1].get("lab", ""), 999), x[0]))

    today = datetime.now().strftime("%Y-%m-%d")
    lines = [
        f"# LLM Lab SNS 스캔 리포트",
        "",
        f"- 생성: {today}",
        f"- 수집 lab 수: {len(results)}",
        "",
        "> ⚠ 웹서치 기반 스냅샷. X 등 직접 스크랩이 아니라 공개 검색 결과에서 모은 것이라 "
        "핸들/발언이 시점에 따라 부정확하거나 secondhand일 수 있음. 신뢰 전 직접 확인 권장.",
        "",
        "---",
        "",
    ]

    all_sources = []
    for name, d in results:
        lab = d.get("lab", name)
        lines.append(f"## {lab}")
        lines.append("")
        lines.append(f"**공식 계정:** {_fmt_accounts(d.get('official_accounts'))}")
        if d.get("notes"):
            lines.append("")
            lines.append(f"> {d['notes']}")
        lines.append("")
        people = d.get("people", []) or []
        if people:
            for p in people:
                name_ = p.get("name", "?")
                role = p.get("role", "")
                lines.append(f"### {name_} — {role}")
                lines.append(f"- 계정: {_fmt_accounts(p.get('accounts'))}")
                themes = p.get("recent_themes") or []
                if themes:
                    lines.append(f"- 최근 화제: {', '.join(themes)}")
                posts = p.get("notable_posts") or []
                for post in posts:
                    s = post.get("summary", "")
                    dt = post.get("approx_date", "")
                    src = post.get("source_url", "")
                    suffix = f" ([출처]({src}))" if src else ""
                    date_p = f"_{dt}_ — " if dt else ""
                    lines.append(f"  - {date_p}{s}{suffix}")
                lines.append("")
        else:
            lines.append("_인물 정보 없음._")
            lines.append("")
        for s in d.get("sources", []) or []:
            all_sources.append((lab, s))
        lines.append("---")
        lines.append("")

    if all_sources:
        lines.append("## 출처 전체")
        lines.append("")
        for lab, s in all_sources:
            lines.append(f"- ({lab}) {s}")
        lines.append("")

    REPORT_FILE.write_text("\n".join(lines), encoding="utf-8")
    print(f"[collect] 렌더 완료 → {REPORT_FILE}  ({len(results)} labs, 출처 {len(all_sources)}개)")
    return 0


def main():
    parser = argparse.ArgumentParser(description="LLM lab SNS 스캔 플러밍 CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("labs", help="lab 설정(JSON) 출력")
    sub.add_parser("validate", help="results/*.json 스키마 점검")
    sub.add_parser("collect", help="results/*.json → report.md 렌더")
    args = parser.parse_args()

    dispatch = {"labs": cmd_labs, "validate": cmd_validate, "collect": cmd_collect}
    rc = dispatch[args.cmd](args)
    sys.exit(rc or 0)


if __name__ == "__main__":
    main()
