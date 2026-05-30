"""필링 리스트 -> markdown 렌더링.

KR module_disclosure 출력 포맷(섹션 그룹 + 표) 을 흉내낸다.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Optional

from _categorizer import CATEGORY_LABELS, CATEGORY_ORDER


@dataclass
class Filing:
    ticker: str
    cik: int
    form: str
    filing_date: str          # YYYY-MM-DD
    accession_no: str         # 0000320193-24-000123
    primary_doc: str
    items: list[str] = field(default_factory=list)
    category: str = "other"
    label: str = ""
    summary: str = ""         # 8-K 본문에서 추출한 짧은 요약 (한 줄)
    url: str = ""             # 본문 .htm 직접 링크
    filing_index_url: str = ""  # filing index 페이지 (목록)


def _section(rows: list[Filing], cat: str) -> str:
    items = [r for r in rows if r.category == cat]
    label = CATEGORY_LABELS.get(cat, cat)
    if not items:
        return f"### {label}\n_해당 기간 공시 없음._\n\n"
    out = [f"### {label} ({len(items)}건)\n"]
    out.append("| 일자 | Form | 카테고리/Item | 요약 | 원문 |\n")
    out.append("|---|---|---|---|---|\n")
    for r in items:
        summary = (r.summary or "—").replace("\n", " ").strip()
        if len(summary) > 80:
            summary = summary[:77] + "..."
        # markdown table 깨짐 방지
        summary = summary.replace("|", "\\|")
        label_cell = r.label.replace("|", "\\|")
        out.append(
            f"| {r.filing_date} | {r.form} | {label_cell} | {summary} | [link]({r.url or r.filing_index_url}) |\n"
        )
    out.append("\n")
    return "".join(out)


def render_markdown(
    ticker: str,
    cik: int,
    rows: list[Filing],
    days: int,
    company_name: Optional[str] = None,
) -> str:
    title = f"# {ticker} EDGAR 공시 ({company_name or '—'})  \nCIK: {cik:010d} | 최근 {days}일\n\n"
    if not rows:
        return title + "_해당 기간 공시 없음._\n"

    # 통계
    form_counts = Counter(r.form for r in rows)
    cat_counts = Counter(r.category for r in rows)
    summary_lines = [
        "## 요약",
        f"- 총 필링 수: **{len(rows)}**",
        "- Form 별: " + ", ".join(f"{f}={c}" for f, c in sorted(form_counts.items(), key=lambda x: -x[1])),
        "- 카테고리 별: " + ", ".join(
            f"{CATEGORY_LABELS.get(k, k)}={v}"
            for k, v in sorted(cat_counts.items(), key=lambda x: -x[1])
        ),
        "",
    ]

    body = [title, "\n".join(summary_lines), "\n## 카테고리별 상세\n\n"]
    for cat in CATEGORY_ORDER:
        body.append(_section(rows, cat))
    return "".join(body)
