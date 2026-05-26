"""R4 인사이트 카드의 방향성 콜이 실제로 맞았는지 채점한다.

코퍼스는 카드별 expected_direction + time_horizon 을 주지만 *종목*도 *기준일*도
없다. 그래서 사용자가 predictions.csv 에 (card_id, ticker, as_of_date) 만 채우면
카드의 방향/호라이즌은 코퍼스에서 자동 조인하고, prices.csv 와 맞춰 적중 여부를 센다.

핵심 설계 결정:
- conditional / mixed / neutral 은 '방향성 베팅'이 아니므로 적중률에서 제외하고 따로 집계.
  (R4 64장 중 약 절반이 여기 해당 — 전체 카드 단순 적중률은 무의미하다.)
- horizon -> 평가 창(거래일): short=5, mid=20, long=60, mid_to_long=40.
- 거래일은 prices.csv에 실재하는 행 기준으로 forward 인덱싱(휴일/달력 계산 회피).

stdlib only. Python 3.9+.
"""
import argparse
import csv
import json
import os
from collections import defaultdict

HORIZON_DAYS = {"short": 5, "mid": 20, "long": 60, "mid_to_long": 40}


def direction_sign(d):
    """방향 문자열 -> +1(상승베팅) / -1(하락베팅) / None(방향성 아님)."""
    d = (d or "").lower()
    if "conditional" in d or "mixed" in d or "neutral" in d:
        return None
    if "bull" in d:
        return 1
    if "bear" in d:
        return -1
    return None


def load_cards(path):
    cards = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            c = json.loads(line)
            cards[c["card_id"]] = c
    return cards


def load_prices(path):
    """{ticker: [(date_str, close), ...]} 날짜 오름차순."""
    by_ticker = defaultdict(list)
    with open(path, encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            by_ticker[row["ticker"]].append((row["date"], float(row["close"])))
    for t in by_ticker:
        by_ticker[t].sort()
    return by_ticker


def eval_one(series, as_of_date, window):
    """as_of_date 이후 첫 거래일을 시작점으로, window 거래일 뒤 수익률 반환.
    데이터 부족하면 None 사유 문자열."""
    start_idx = next((i for i, (d, _) in enumerate(series) if d >= as_of_date), None)
    if start_idx is None:
        return None, "as_of_date 이후 가격 없음"
    target_idx = start_idx + window
    if target_idx >= len(series):
        return None, f"window({window}거래일) 만큼의 미래 가격 부족"
    p0 = series[start_idx][1]
    p1 = series[target_idx][1]
    if p0 == 0:
        return None, "시작가 0"
    return (p1 / p0 - 1.0), None


def score(cards, predictions, prices):
    results = []
    for pred in predictions:
        cid = pred["card_id"]
        card = cards.get(cid)
        if not card:
            results.append({"card_id": cid, "status": "skip", "why": "코퍼스에 카드 없음"})
            continue
        direction = pred.get("direction") or card.get("expected_direction", "")
        horizon = (pred.get("horizon") or card.get("time_horizon", "")).strip()
        sgn = direction_sign(direction)
        if sgn is None:
            results.append({"card_id": cid, "status": "non_directional",
                            "direction": direction, "framework": card.get("framework_used")})
            continue
        window = HORIZON_DAYS.get(horizon)
        if window is None:
            results.append({"card_id": cid, "status": "skip",
                            "why": f"horizon 미정/미지원: {horizon!r}"})
            continue
        series = prices.get(pred["ticker"])
        if not series:
            results.append({"card_id": cid, "status": "skip",
                            "why": f"prices에 ticker 없음: {pred['ticker']}"})
            continue
        ret, err = eval_one(series, pred["as_of_date"], window)
        if err:
            results.append({"card_id": cid, "status": "skip", "why": err})
            continue
        hit = (ret > 0 and sgn > 0) or (ret < 0 and sgn < 0)
        results.append({
            "card_id": cid, "status": "scored", "ticker": pred["ticker"],
            "direction": direction, "horizon": horizon, "window": window,
            "ret": ret, "expected_sign": sgn, "hit": hit,
            "framework": card.get("framework_used"),
        })
    return results


def aggregate(results):
    scored = [r for r in results if r["status"] == "scored"]
    by_dir, by_hor, by_fw = defaultdict(list), defaultdict(list), defaultdict(list)
    for r in scored:
        by_dir["bullish" if r["expected_sign"] > 0 else "bearish"].append(r["hit"])
        by_hor[r["horizon"]].append(r["hit"])
        by_fw[r.get("framework") or "?"].append(r["hit"])
    return scored, by_dir, by_hor, by_fw


def rate(hits):
    return sum(hits) / len(hits) if hits else None


def report(results):
    scored, by_dir, by_hor, by_fw = aggregate(results)
    non_dir = [r for r in results if r["status"] == "non_directional"]
    skipped = [r for r in results if r["status"] == "skip"]
    L = []
    L.append("=" * 60)
    L.append("R4 카드 방향성 적중률 SCORECARD")
    L.append("=" * 60)
    L.append(f"입력 예측: {len(results)}건 | 채점됨: {len(scored)} | "
             f"방향성아님(제외): {len(non_dir)} | 스킵: {len(skipped)}")

    if scored:
        overall = rate([r["hit"] for r in scored])
        L.append(f"\n[전체 방향성 적중률] {overall:.0%}  ({sum(r['hit'] for r in scored)}/{len(scored)})")
        L.append("\n[방향별]")
        for k, v in by_dir.items():
            L.append(f"  {k:9s}: {rate(v):.0%}  ({sum(v)}/{len(v)})")
        L.append("\n[호라이즌별]")
        for k, v in sorted(by_hor.items()):
            L.append(f"  {k:9s}: {rate(v):.0%}  ({sum(v)}/{len(v)})")
        L.append("\n[프레임워크별]")
        for k, v in sorted(by_fw.items(), key=lambda x: -len(x[1])):
            L.append(f"  {k:24s}: {rate(v):.0%}  ({sum(v)}/{len(v)})")
        L.append("\n[카드별 상세]")
        for r in scored:
            mark = "HIT " if r["hit"] else "MISS"
            L.append(f"  {mark} {r['card_id']} {r['ticker']} {r['direction']}/{r['horizon']}"
                     f" -> {r['ret']:+.1%} ({r['window']}거래일)")
    else:
        L.append("\n채점된 예측이 없음 — predictions/prices/horizon 입력을 확인.")

    if non_dir:
        L.append("\n[방향성 아님 — 적중률에서 제외]")
        L.append("  " + ", ".join(f"{r['card_id']}({r['direction']})" for r in non_dir))
    if skipped:
        L.append("\n[스킵 — 데이터 부족]")
        for r in skipped:
            L.append(f"  {r['card_id']}: {r['why']}")
    return "\n".join(L)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    sdir = os.path.join(here, "sample")
    ap = argparse.ArgumentParser(description="R4 카드 방향성 백테스터")
    ap.add_argument("--cards", default=os.path.join(sdir, "cards.jsonl"),
                    help="R4 카드 jsonl (expected_direction/time_horizon 보유)")
    ap.add_argument("--predictions", default=os.path.join(sdir, "predictions.csv"),
                    help="card_id,ticker,as_of_date[,direction,horizon]")
    ap.add_argument("--prices", default=os.path.join(sdir, "prices.csv"),
                    help="date,ticker,close")
    args = ap.parse_args()

    cards = load_cards(args.cards)
    with open(args.predictions, encoding="utf-8") as fh:
        predictions = list(csv.DictReader(fh))
    prices = load_prices(args.prices)
    print(report(score(cards, predictions, prices)))


if __name__ == "__main__":
    main()
