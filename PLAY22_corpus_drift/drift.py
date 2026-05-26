"""insight_corpus daily/ 파일들을 가로질러 분포 드리프트를 추적한다.

매일 생성되는 LLM_create_YYYY-MM-DD.json 들을 시간순으로 읽어
산업/사고함수/품질점수/promotion 비율이 어떻게 흔들리는지 측정한다.
에코챔버(한 렌즈로 쏠림)·품질 급락·측정 결손을 빨리 잡는 게 목적.

stdlib only. Python 3.9+.
"""
import argparse
import glob
import json
import math
import os
import re
from collections import Counter

DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")


def load_days(daily_dir):
    """daily_dir 안의 LLM_create_*.json 을 날짜순 [(date, data), ...] 로."""
    days = []
    for path in sorted(glob.glob(os.path.join(daily_dir, "LLM_create_*.json"))):
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        m = DATE_RE.search(os.path.basename(path))
        date = data.get("date") or (m.group(1) if m else os.path.basename(path))
        days.append((date, data))
    return days


def hhi(counter):
    """Herfindahl 집중도. 1=완전 독점(한 산업), 1/n=완전 분산. 카드 없으면 None."""
    total = sum(counter.values())
    if total == 0:
        return None
    return sum((v / total) ** 2 for v in counter.values())


def day_metrics(date, data):
    cards = data.get("cards", [])
    industries = Counter()
    funcs = Counter()
    grades = Counter()
    borrowed = Counter()
    scores = []
    promo = 0
    for c in cards:
        if c.get("industry"):
            industries[c["industry"]] += 1
        for f in c.get("activated_R5_functions", []) or []:
            funcs[f] += 1
        pf = c.get("primary_thinking_function")
        if pf:
            funcs[pf] += 1
        aq = c.get("auto_quality") or {}
        if isinstance(aq.get("score"), (int, float)):
            scores.append(aq["score"])
        if aq.get("grade"):
            grades[aq["grade"]] += 1
        if c.get("promotion_candidate"):
            promo += 1
        for e in c.get("borrowed_R4_cards", []) or []:
            borrowed[e] += 1
    summary = data.get("summary") or {}
    anomaly = summary.get("parser_cron_anomaly")
    return {
        "date": date,
        "n_cards": len(cards),
        "mean_score": round(sum(scores) / len(scores), 2) if scores else None,
        "grades": dict(grades),
        "industries": industries,
        "industry_hhi": hhi(industries),
        "funcs": funcs,
        "n_unique_funcs": len(funcs),
        "promotion_rate": round(promo / len(cards), 2) if cards else None,
        "borrowed": borrowed,
        "anomaly": anomaly,
    }


def fmt_counter(counter, top=None):
    items = counter.most_common(top)
    return ", ".join(f"{k}:{v}" for k, v in items) if items else "-"


def report(days):
    metrics = [day_metrics(d, data) for d, data in days]
    lines = []
    lines.append("=" * 64)
    lines.append("insight_corpus DAILY DRIFT REPORT")
    lines.append(f"기간: {metrics[0]['date']} ~ {metrics[-1]['date']}  ({len(metrics)}일)")
    lines.append("=" * 64)

    # 1) 일자별 스냅샷
    lines.append("\n[일자별 스냅샷]")
    for m in metrics:
        hhi_s = f"{m['industry_hhi']:.2f}" if m["industry_hhi"] is not None else "-"
        lines.append(
            f"  {m['date']} | cards={m['n_cards']:2d} | mean_score="
            f"{m['mean_score']!s:>4} | 산업HHI={hhi_s} | 고유함수={m['n_unique_funcs']:2d}"
            f" | promo={m['promotion_rate']}"
        )
        lines.append(f"      산업: {fmt_counter(m['industries'])}")
        if m["anomaly"]:
            lines.append(f"      [!] 측정 이상: {m['anomaly']}")

    # 2) 품질 점수 추세 + 급락 플래그
    scores = [m["mean_score"] for m in metrics]
    lines.append("\n[품질 점수 추세]")
    lines.append("  " + " -> ".join(str(s) for s in scores))
    for prev, cur in zip(metrics, metrics[1:]):
        if prev["mean_score"] is not None and cur["mean_score"] is not None:
            drop = prev["mean_score"] - cur["mean_score"]
            if drop >= 2:
                tag = " (측정 이상 동반)" if cur["anomaly"] else ""
                lines.append(
                    f"  [!] {cur['date']} 점수 급락 {prev['mean_score']}->{cur['mean_score']}{tag}"
                )

    # 3) 사고함수 다양성 / 지속 렌즈
    all_func_days = Counter()
    for m in metrics:
        for f in m["funcs"]:
            all_func_days[f] += 1
    n = len(metrics)
    persistent = sorted(f for f, c in all_func_days.items() if c == n)
    oneoff = sorted(f for f, c in all_func_days.items() if c == 1)
    lines.append("\n[사고함수 활성화]")
    lines.append(f"  전 기간 등장 함수 종류: {len(all_func_days)}개")
    lines.append(f"  매일 등장(지속 렌즈): {', '.join(persistent) if persistent else '-'}")
    lines.append(f"  단발 등장(1일만): {', '.join(oneoff) if oneoff else '-'}")
    if persistent and len(persistent) / max(len(all_func_days), 1) > 0.5:
        lines.append("  [!] 함수 다양성 낮음 — 소수 렌즈로 쏠림(에코챔버) 의심")

    # 4) 산업 집중도 추세
    hhis = [m["industry_hhi"] for m in metrics if m["industry_hhi"] is not None]
    if hhis:
        lines.append("\n[산업 집중도(HHI) 추세]")
        lines.append("  " + " -> ".join(f"{h:.2f}" for h in hhis))
        if hhis[-1] >= 0.5:
            lines.append("  [!] 최근 산업 집중도 높음 — 특정 테마 과편중")

    # 5) 반복 차용된 R4 카드 (베이스 과의존)
    all_borrowed = Counter()
    for m in metrics:
        all_borrowed.update(m["borrowed"])
    lines.append("\n[반복 차용된 R4 베이스 카드 top]")
    lines.append("  " + fmt_counter(all_borrowed, top=8))

    return "\n".join(lines), metrics


def write_csv(metrics, path):
    import csv
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["date", "n_cards", "mean_score", "industry_hhi",
                    "n_unique_funcs", "promotion_rate", "top_industry", "anomaly"])
        for m in metrics:
            top_ind = m["industries"].most_common(1)
            w.writerow([
                m["date"], m["n_cards"], m["mean_score"],
                f"{m['industry_hhi']:.4f}" if m["industry_hhi"] is not None else "",
                m["n_unique_funcs"], m["promotion_rate"],
                top_ind[0][0] if top_ind else "", m["anomaly"] or "",
            ])


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description="insight_corpus daily 드리프트 추적기")
    ap.add_argument("--daily", default=os.path.join(here, "sample", "daily"),
                    help="LLM_create_*.json 들이 있는 폴더 (기본: 동봉 sample)")
    ap.add_argument("--csv", help="일자별 지표를 CSV로 저장할 경로 (선택)")
    args = ap.parse_args()

    days = load_days(args.daily)
    if not days:
        raise SystemExit(f"daily 파일을 찾지 못함: {args.daily}")
    text, metrics = report(days)
    print(text)
    if args.csv:
        write_csv(metrics, args.csv)
        print(f"\n[CSV 저장] {args.csv}")


if __name__ == "__main__":
    main()
