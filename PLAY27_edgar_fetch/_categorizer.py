"""8-K Item code -> category 매핑.

SEC 8-K 공식 Item 정의 (https://www.sec.gov/fast-answers/answersform8khtm.html) 기준.
KR module_disclosure 의 카테고리(contract/equity/treasury/earnings/exec/other)와
의미상 호환되도록 그룹핑.
"""
from __future__ import annotations

import re
from typing import Optional

# Item -> (category_key, 한 줄 한글 라벨)
ITEM_MAP: dict[str, tuple[str, str]] = {
    # Section 1 - Business and Operations
    "1.01": ("contract",   "Material Definitive Agreement (주요 계약 체결)"),
    "1.02": ("contract",   "Termination of Material Definitive Agreement (계약 해지)"),
    "1.03": ("other",      "Bankruptcy or Receivership"),
    "1.05": ("other",      "Material Cybersecurity Incident"),
    # Section 2 - Financial Information
    "2.01": ("contract",   "Completion of Acquisition or Disposition (인수/매각 완료)"),
    "2.02": ("earnings",   "Results of Operations and Financial Condition (실적 발표)"),
    "2.03": ("equity",     "Creation of a Direct Financial Obligation (채무 발생)"),
    "2.04": ("equity",     "Triggering Events That Accelerate Financial Obligation"),
    "2.05": ("other",      "Costs Associated with Exit or Disposal Activities"),
    "2.06": ("other",      "Material Impairments"),
    # Section 3 - Securities and Trading
    "3.01": ("other",      "Notice of Delisting / Failure to Satisfy Listing Rule"),
    "3.02": ("equity",     "Unregistered Sales of Equity Securities (사모 증자)"),
    "3.03": ("equity",     "Material Modification to Rights of Security Holders"),
    # Section 4 - Matters Related to Accountants and Financial Statements
    "4.01": ("other",      "Changes in Registrant's Certifying Accountant"),
    "4.02": ("other",      "Non-Reliance on Previously Issued Financial Statements"),
    # Section 5 - Corporate Governance and Management
    "5.01": ("exec",       "Changes in Control of Registrant"),
    "5.02": ("exec",       "Departure/Appointment of Directors or Officers (경영진 변경)"),
    "5.03": ("exec",       "Amendments to Articles of Incorporation or Bylaws"),
    "5.04": ("other",      "Temporary Suspension of Trading Under Employee Benefit Plans"),
    "5.05": ("other",      "Amendments to Code of Ethics"),
    "5.07": ("exec",       "Submission of Matters to a Vote of Security Holders"),
    "5.08": ("exec",       "Shareholder Director Nominations"),
    # Section 6 - Asset-Backed Securities (생략)
    # Section 7 - Regulation FD
    "7.01": ("guidance",   "Regulation FD Disclosure (가이던스/IR 공시)"),
    # Section 8 - Other Events
    "8.01": ("other",      "Other Events"),
    # Section 9 - Financial Statements and Exhibits
    "9.01": ("other",      "Financial Statements and Exhibits"),
}

# 비-8K 폼 매핑
FORM_MAP: dict[str, tuple[str, str]] = {
    "10-K":   ("annual_report",    "Annual Report (10-K)"),
    "10-K/A": ("annual_report",    "Annual Report Amendment (10-K/A)"),
    "10-Q":   ("quarterly_report", "Quarterly Report (10-Q)"),
    "10-Q/A": ("quarterly_report", "Quarterly Report Amendment (10-Q/A)"),
    "4":      ("insider",          "Insider Transaction (Form 4)"),
    "4/A":    ("insider",          "Insider Transaction Amendment (Form 4/A)"),
    "S-1":    ("equity",           "Registration Statement (S-1)"),
    "S-3":    ("equity",           "Registration Statement (S-3)"),
    "DEF 14A":("exec",             "Proxy Statement (DEF 14A)"),
    "SC 13G": ("insider",          "Beneficial Ownership Report (SC 13G)"),
    "SC 13D": ("insider",          "Beneficial Ownership Report (SC 13D)"),
}

CATEGORY_ORDER = [
    "contract",         # 수주/계약/M&A
    "earnings",         # 실적
    "guidance",         # 가이던스/IR
    "equity",           # 증자/사모/채무
    "exec",             # 경영진
    "annual_report",    # 10-K
    "quarterly_report", # 10-Q
    "insider",          # Form 4 등
    "other",
]

CATEGORY_LABELS = {
    "contract":         "수주/계약/M&A",
    "earnings":         "실적 발표 (Item 2.02)",
    "guidance":         "가이던스/IR (Item 7.01)",
    "equity":           "증자/채무 (Item 3.02 / 2.03)",
    "exec":             "경영진 변경 (Item 5.02 등)",
    "annual_report":    "연차보고서 (10-K)",
    "quarterly_report": "분기보고서 (10-Q)",
    "insider":          "내부자 거래 (Form 4 / 13G)",
    "other":            "기타",
}

ITEM_RE = re.compile(r"Item\s+(\d+\.\d+)", re.IGNORECASE)


def extract_items_from_html(html: str) -> list[str]:
    """8-K HTML 본문에서 Item N.NN 코드 추출 (중복 제거, 첫 등장 순서 유지)."""
    if not html:
        return []
    seen: list[str] = []
    seen_set: set[str] = set()
    for m in ITEM_RE.finditer(html):
        code = m.group(1)
        if code in seen_set:
            continue
        seen.append(code)
        seen_set.add(code)
        if len(seen) >= 8:  # 8-K 하나에 Item 8개 넘는 경우는 거의 없음
            break
    return seen


def categorize_filing(form: str, items: list[str]) -> tuple[str, str]:
    """필링 한 건 -> (category_key, label).

    8-K 의 경우 추출된 Item 중 *가장 우선순위 높은* 카테고리를 반환.
    우선순위는 CATEGORY_ORDER 순서.
    """
    form_u = form.upper().strip()
    if form_u in FORM_MAP:
        return FORM_MAP[form_u]
    if form_u.startswith("8-K"):
        if not items:
            return ("other", "8-K (Item 미상)")
        # 우선순위에 따라 선택
        best: Optional[tuple[int, str, str]] = None
        for item in items:
            if item not in ITEM_MAP:
                continue
            cat, label = ITEM_MAP[item]
            try:
                rank = CATEGORY_ORDER.index(cat)
            except ValueError:
                rank = 999
            if best is None or rank < best[0]:
                best = (rank, cat, f"Item {item} - {label}")
        if best is None:
            return ("other", f"8-K (Item {', '.join(items)})")
        # 다른 Item도 있으면 라벨에 추가
        extra = [i for i in items if i != best[2].split()[1]]
        label = best[2]
        if extra:
            label += f" [+{', '.join(extra)}]"
        return (best[1], label)
    return ("other", form)
