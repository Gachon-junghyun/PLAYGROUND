"""R6 Phase B — R5 44함수에 4 신규 필드(data_sources, indicators, action_at_trigger, backtest_log) 추가.

기존 11필드 보존, v1 -> v2 스키마 변경.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

# Force UTF-8 stdout
sys.stdout.reconfigure(encoding="utf-8")

DATA_DIR = Path("C:/Users/fivep/OneDrive/Desktop/PLAYGROUND/PLAY13_insight_distill/data")
MVP_DIR = Path("C:/Users/fivep/OneDrive/Desktop/mvp/research_Mvp/insight_corpus")

R5_PATH = DATA_DIR / "r5_thinking_functions.json"
DS_PATH = DATA_DIR / "r6_data_sources.json"
IND_PATH = DATA_DIR / "r6_indicators.json"
ACT_PATH = DATA_DIR / "r6_action_templates.json"
MVP_R5_PATH = MVP_DIR / "r5_thinking_functions.json"


def load(p: Path) -> dict[str, Any]:
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


# ---- Load all ----
r5 = load(R5_PATH)
ds = load(DS_PATH)
ind = load(IND_PATH)
act = load(ACT_PATH)

ds_ids = {s["source_id"] for s in ds["sources"]}
ind_ids = {i["indicator_id"] for i in ind["indicators"]}
act_ids = {a["action_id"] for a in act["actions"]}

# Reverse map (catalog -> R5)
fn_to_ds: dict[str, list[str]] = {}
for s in ds["sources"]:
    for fid in s.get("related_R5_functions", []):
        fn_to_ds.setdefault(fid, []).append(s["source_id"])

fn_to_ind: dict[str, list[str]] = {}
for i in ind["indicators"]:
    for fid in i.get("related_R5_functions", []):
        fn_to_ind.setdefault(fid, []).append(i["indicator_id"])

# ---- Domain fallback for sparse coverage ----
# Domain -> default DS list (for functions w/ ds<2)
DOMAIN_DS_FALLBACK: dict[str, list[str]] = {
    "consumer": ["DS_MVP_NEWS_ALERT_DB", "DS_KOSTAT", "DS_WEBSEARCH_CONSUMER_TRENDS"],
    "brand_strategy": ["DS_MVP_NEWS_ALERT_DB", "DS_MVP_MODULE_VALUATION", "DS_WEBSEARCH_CONSUMER_TRENDS"],
    "F&B": ["DS_MVP_MODULE_DISCLOSURE", "DS_MVP_NEWS_ALERT_DB", "DS_WEBSEARCH_CONSUMER_TRENDS"],
    "consumer_goods": ["DS_MVP_MODULE_DISCLOSURE", "DS_MVP_MODULE_VALUATION"],
    "real_estate": ["DS_KOSTAT", "DS_MVP_NEWS_ALERT_DB"],
    "luxury_inventory": ["DS_MVP_NEWS_ALERT_DB", "DS_WEBSEARCH_CONSUMER_TRENDS"],
    "luxury": ["DS_MVP_NEWS_ALERT_DB", "DS_WEBSEARCH_CONSUMER_TRENDS"],
    "M&A": ["DS_MVP_MODULE_DISCLOSURE", "DS_SP_CAPITAL_IQ"],
    "game_industry": ["DS_MVP_NEWS_ALERT_DB", "DS_SENSORTOWER", "DS_MVP_MODULE_VALUATION"],
    "media": ["DS_MVP_NEWS_ALERT_DB", "DS_WEBSEARCH_CONSUMER_TRENDS"],
    "media_rights": ["DS_MVP_NEWS_ALERT_DB", "DS_WEBSEARCH_CONSUMER_TRENDS"],
    "real_estate_leases": ["DS_MVP_NEWS_ALERT_DB", "DS_MVP_MODULE_DISCLOSURE"],
    "long_term_contracts": ["DS_MVP_MODULE_DISCLOSURE", "DS_MVP_NEWS_ALERT_DB"],
    "biotech": ["DS_MVP_MODULE_DISCLOSURE", "DS_MVP_NEWS_ALERT_DB", "DS_WEBSEARCH_INDUSTRY_OUTLOOK"],
    "consumer_health": ["DS_MVP_MODULE_DISCLOSURE", "DS_MVP_NEWS_ALERT_DB"],
    "specialty_chemicals": ["DS_MVP_MODULE_DISCLOSURE", "DS_WEBSEARCH_INDUSTRY_OUTLOOK"],
    "consumer_electronics": ["DS_MVP_MODULE_VALUATION", "DS_SENSORTOWER", "DS_WEBSEARCH_CONSUMER_TRENDS"],
    "industrial_cluster": ["DS_MVP_MODULE_DISCLOSURE", "DS_KOSTAT"],
    "ai_tech": ["DS_WEBSEARCH_VC_STARTUP", "DS_WEBSEARCH_INDUSTRY_OUTLOOK", "DS_SENSORTOWER"],
    "infrastructure": ["DS_MVP_MODULE_DISCLOSURE", "DS_KEEI", "DS_WEBSEARCH_INDUSTRY_OUTLOOK"],
    "semiconductor": ["DS_MVP_MODULE_DISCLOSURE", "DS_DART_OPENAPI", "DS_WEBSEARCH_INDUSTRY_OUTLOOK"],
    "tech_themes": ["DS_MVP_NEWS_ALERT_DB", "DS_WEBSEARCH_VC_STARTUP", "DS_SENSORTOWER"],
    "consumer_tech": ["DS_SENSORTOWER", "DS_WEBSEARCH_CONSUMER_TRENDS"],
    "startup_business": ["DS_WEBSEARCH_VC_STARTUP", "DS_MVP_NEWS_ALERT_DB"],
    "compliance": ["DS_FSC_FSS", "DS_WEBSEARCH_POLICY_CATALYST", "DS_MVP_NEWS_ALERT_DB"],
    "corporate_strategy": ["DS_MVP_MODULE_DISCLOSURE", "DS_MVP_NEWS_ALERT_DB"],
}

# Domain -> default IND list
DOMAIN_IND_FALLBACK: dict[str, list[str]] = {
    "real_estate": ["IND_SEOUL_REZONING_DESIGNATION"],
    "luxury_inventory": ["IND_KOLMAR_CLIENT_CONCENTRATION"],
    "M&A": ["IND_SEOUL_REZONING_DESIGNATION"],
    "game_industry": ["IND_GLOBAL_GAME_GROWTH"],
    "media": ["IND_BERKSHIRE_13F_NYT"],
    "consumer": ["IND_KOREA_30S_NEW_ACCOUNTS"],
    "F&B": ["IND_KOREA_GIM_EXPORT_PRICE"],
    "tourism": ["IND_FOREIGN_KR_FUND_FLOW"],
    "retail": ["IND_KOREA_30S_NEW_ACCOUNTS"],
    "consumer_health": ["IND_BOTOX_STRAIN_RULING"],
    "biotech": ["IND_BOTOX_STRAIN_RULING"],
    "specialty_chemicals": ["IND_BOTOX_STRAIN_RULING"],
    "media_rights": ["IND_JTBC_OLYMPIC_AD_RATE"],
    "real_estate_leases": ["IND_SEOUL_REZONING_DESIGNATION"],
    "long_term_contracts": ["IND_JTBC_OLYMPIC_AD_RATE"],
    "consumer_electronics": ["IND_SAMSUNG_LG_HOME_APPLIANCE_OPM"],
    "industrial_cluster": ["IND_SEOUL_REZONING_DESIGNATION"],
    "brand_strategy": ["IND_KOLMAR_CLIENT_CONCENTRATION"],
    "consumer_goods": ["IND_ORION_OP_MARGIN"],
    "ai_tech": ["IND_OPENROUTER_TOKEN_VOLUME"],
    "tech_themes": ["IND_META_REALITY_LABS_LOSS"],
    "consumer_tech": ["IND_REVENUE_PER_HEADCOUNT_AI"],
    "compliance": ["IND_OFAC_KR_BANK_FINES"],
}

# Macro/single-card classification
MACRO_FNS = {"F01", "F04", "F09", "F10", "F11", "F12", "F22", "F26", "F28", "F29", "F30", "F34", "F35", "F43"}
# Functions with "regime_shift" in resonance get higher weight for new_thesis_research
REGIME_SHIFT_FNS = set()
for fn in r5["functions"]:
    res = fn.get("framework_resonance", [])
    if "regime_shift" in res:
        REGIME_SHIFT_FNS.add(fn["function_id"])


def build_data_sources(fn: dict[str, Any]) -> list[str]:
    fid = fn["function_id"]
    out: list[str] = list(dict.fromkeys(fn_to_ds.get(fid, [])))  # dedupe preserving order
    if len(out) < 2:
        domains = fn.get("applies_to_domain", [])
        for d in domains:
            for s in DOMAIN_DS_FALLBACK.get(d, []):
                if s not in out:
                    out.append(s)
                if len(out) >= 3:
                    break
            if len(out) >= 3:
                break
    # Cap at 5
    return out[:5]


def build_indicators(fn: dict[str, Any]) -> list[str]:
    fid = fn["function_id"]
    out: list[str] = list(dict.fromkeys(fn_to_ind.get(fid, [])))
    if len(out) < 1:
        domains = fn.get("applies_to_domain", [])
        for d in domains:
            for i in DOMAIN_IND_FALLBACK.get(d, []):
                if i not in out:
                    out.append(i)
                if len(out) >= 2:
                    break
            if len(out) >= 2:
                break
    return out[:5]


def build_action_at_trigger(fn: dict[str, Any]) -> dict[str, list[str]]:
    fid = fn["function_id"]
    is_macro = fid in MACRO_FNS
    is_single_card = fn.get("source_card_count", 0) == 1
    is_regime = fid in REGIME_SHIFT_FNS

    # Watch level — applies to all (DART_ALERT only if company-applicable)
    # company-applicable = not pure macro
    watch = []
    if not is_macro or fid in {"F11", "F35"}:  # central bank policy still needs disclosure-style alerts in KR scope
        # Actually, only DART-applicable functions get ACT_DART_ALERT_REGISTER
        # Per the action catalog, applicable_R5_functions=['F20','F33','F37']; broader interpretation: all corp-touching functions
        watch.append("ACT_DART_ALERT_REGISTER")
    watch.append("ACT_WATCHLIST_ADD")
    watch.append("ACT_MONITORING_SIGNAL_TIMESERIES")

    # Warn level
    warn = [
        "ACT_T2_PROMOTION_FLAG",
        "ACT_WEBSEARCH_AUTO_QUERY",
        "ACT_TELEGRAM_ALERT_WARN",
        "ACT_NEWS_DEEP_FETCH",
    ]
    # Macro adds peer baseline snapshot too
    if is_macro:
        warn.append("ACT_PEER_BASELINE_SNAPSHOT")

    # Critical level
    critical = [
        "ACT_USER_DISPATCH",
        "ACT_PHASE_D_WEBSEARCH_BATCH",
        "ACT_STATE_REPORT_URGENT_UPDATE",
    ]
    # regime_shift functions get new thesis research trigger
    if is_regime:
        critical.append("ACT_NEW_THESIS_RESEARCH_TRIGGER")

    # Cross-ref — common to all
    cross_ref = [
        "ACT_CROSS_REF_R4_CARDS",
        "ACT_FRAMEWORK_RESONANCE_SCAN",
        "ACT_RELATED_FUNCTIONS_GRAPH",
        "ACT_DOMAIN_FUNCTION_LOOKUP",
        "ACT_T2_SAME_THESIS_CLUSTER",
    ]

    # Backtest — common
    backtest = [
        "ACT_BACKTEST_LOG_ENTRY",
        "ACT_BACKTEST_CRON_REGISTER",
        "ACT_FUNCTION_HIT_RATE_CALC",
    ]
    # Single-card functions add redesign candidate
    if is_single_card:
        backtest.append("ACT_FUNCTION_REDESIGN_CANDIDATE")

    return {
        "watch_level": watch,
        "warn_level": warn,
        "critical_level": critical,
        "cross_ref": cross_ref,
        "backtest": backtest,
    }


# ---- Apply transformation ----
new_functions: list[dict[str, Any]] = []
for fn in r5["functions"]:
    # Preserve original 11 fields exactly
    new_fn: dict[str, Any] = dict(fn)
    new_fn["data_sources"] = build_data_sources(fn)
    new_fn["indicators"] = build_indicators(fn)
    new_fn["action_at_trigger"] = build_action_at_trigger(fn)
    new_fn["backtest_log"] = []
    new_functions.append(new_fn)


# ---- Validation: every ID in catalogs ----
violations: list[str] = []
for fn in new_functions:
    fid = fn["function_id"]
    for s in fn["data_sources"]:
        if s not in ds_ids:
            violations.append(f"{fid} data_sources invalid: {s}")
    for i in fn["indicators"]:
        if i not in ind_ids:
            violations.append(f"{fid} indicators invalid: {i}")
    for level, acts in fn["action_at_trigger"].items():
        for a in acts:
            if a not in act_ids:
                violations.append(f"{fid} action_at_trigger.{level} invalid: {a}")

if violations:
    print("VIOLATIONS:")
    for v in violations:
        print(" -", v)
    sys.exit(1)
print(f"Validation OK — {len(new_functions)} functions, 0 ID violations.")


# ---- Build v2 metadata ----
new_r5: dict[str, Any] = {
    "dataset_name": r5.get("dataset_name", "r5_thinking_functions"),
    "version": "v2",
    "created_at": r5.get("created_at", "2026-05-18"),
    "updated_at": "2026-05-18",
    "schema_change": "v1 -> v2: data_sources, indicators, action_at_trigger, backtest_log 4필드 추가 (R6 실행 가능 layer)",
    "source": r5.get("source"),
    "external_catalogs": {
        "data_sources": "r6_data_sources.json (34 sources)",
        "indicators": "r6_indicators.json (61 KPIs)",
        "action_templates": "r6_action_templates.json (22 actions)",
    },
    "principles": list(r5.get("principles", [])) + [
        "실행 가능 layer (R6) — data_sources/indicators/action_at_trigger/backtest_log로 어디·무엇·어떻게·검증을 명시"
    ],
    "total_functions": 44,
    "card_coverage": r5.get("card_coverage"),
    "functions": new_functions,
}

# Strip None keys (e.g. source if not present)
new_r5 = {k: v for k, v in new_r5.items() if v is not None}


# ---- Save ----
def save(p: Path, data: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


save(R5_PATH, new_r5)
save(MVP_R5_PATH, new_r5)

# Sanity reload
for p in [R5_PATH, MVP_R5_PATH]:
    with p.open("r", encoding="utf-8") as f:
        chk = json.load(f)
    assert chk["total_functions"] == 44, f"total_functions mismatch in {p}"
    assert len(chk["functions"]) == 44, f"functions count mismatch in {p}"
    size_kb = p.stat().st_size / 1024
    print(f"Saved: {p}  ({size_kb:.1f} KB)")


# ---- Stats report ----
from collections import Counter

ds_counter: Counter[str] = Counter()
ind_counter: Counter[str] = Counter()
act_counter: Counter[str] = Counter()
sev_counter: Counter[str] = Counter()

for fn in new_functions:
    ds_counter.update(fn["data_sources"])
    ind_counter.update(fn["indicators"])
    for level, acts in fn["action_at_trigger"].items():
        sev_counter[level] += len(acts)
        act_counter.update(acts)

print("\n=== Data sources top-5 ===")
for s, c in ds_counter.most_common(5):
    print(f"  {s}: {c}")

print("\n=== Indicators top-5 ===")
for i, c in ind_counter.most_common(5):
    print(f"  {i}: {c}")

print("\n=== Severity totals ===")
for s, c in sev_counter.most_common():
    print(f"  {s}: {c}")

print("\n=== Action ID frequency (top-10) ===")
for a, c in act_counter.most_common(10):
    print(f"  {a}: {c}")

# Single-card check
single_card_count = sum(1 for fn in new_functions if fn.get("source_card_count") == 1)
single_card_with_redesign = sum(
    1
    for fn in new_functions
    if fn.get("source_card_count") == 1
    and "ACT_FUNCTION_REDESIGN_CANDIDATE" in fn["action_at_trigger"]["backtest"]
)
print(f"\nSingle-card functions: {single_card_count}, with REDESIGN_CANDIDATE: {single_card_with_redesign}")

# F20 full dump
print("\n=== F20 (full 15 fields) ===")
for fn in new_functions:
    if fn["function_id"] == "F20":
        print(json.dumps(fn, ensure_ascii=False, indent=2))
        break

# Single-card example: F22 (game industry, 1 card)
print("\n=== F22 (single-card, full 15 fields) ===")
for fn in new_functions:
    if fn["function_id"] == "F22":
        print(json.dumps(fn, ensure_ascii=False, indent=2))
        break
