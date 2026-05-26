"""thesis 예측 채점 모듈.

mvp refine_recommend.md §2-1 양식에 따라 박제된 예측을 채점한다.
각 예측은:
  - prediction_id: YYYY-MM-DD-INDUSTRY-Fxx-NN
  - claim: 명제 한 줄
  - direction: bull | bear | neutral
  - judge_at: ISO date (판정 시점)
  - hit_when: dict {field, op, threshold} — boolean 임계
  - miss_when: dict — 반대 조건 (optional, 자동 도출 가능)
  - observed: dict {field: value} — 판정 시점 관측값
  - notes: 채점 근거 1줄

본 모듈은 채점 logic만 담당. 데이터 수집·thesis 박제는 별도 layer (mvp).

출력: refine_recommend.md §2-2 누적 ledger에 추가 가능한 markdown row.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path


OPS = {
    ">=": lambda a, b: a >= b,
    "<=": lambda a, b: a <= b,
    ">":  lambda a, b: a > b,
    "<":  lambda a, b: a < b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
}


def _to_date(s):
    if isinstance(s, date) and not isinstance(s, datetime):
        return s
    if isinstance(s, datetime):
        return s.date()
    return datetime.strptime(s, "%Y-%m-%d").date()


def score(prediction, as_of=None):
    """단일 prediction dict 채점.

    반환:
      {
        "prediction_id", "status": "hit"|"miss"|"pending"|"invalid",
        "reason": 한 줄,
        "judge_at", "as_of"
      }
    """
    as_of = _to_date(as_of) if as_of else date.today()
    judge = _to_date(prediction["judge_at"])
    pid = prediction["prediction_id"]
    obs = prediction.get("observed") or {}

    if as_of < judge and not obs:
        return {
            "prediction_id": pid,
            "status": "pending",
            "reason": f"판정 시점 {judge} 미도래 (as_of={as_of})",
            "judge_at": str(judge),
            "as_of": str(as_of),
        }

    hit_rule = prediction.get("hit_when") or {}
    miss_rule = prediction.get("miss_when") or {}

    def _eval(rule):
        if not rule:
            return None
        field, op, threshold = rule.get("field"), rule.get("op"), rule.get("threshold")
        if field not in obs:
            return None
        if op not in OPS:
            return None
        return OPS[op](obs[field], threshold)

    hit = _eval(hit_rule)
    miss = _eval(miss_rule) if miss_rule else (False if hit else None)

    if hit is None and miss is None:
        return {
            "prediction_id": pid,
            "status": "invalid",
            "reason": f"observed에 필요한 field 없음 (hit_when.field={hit_rule.get('field')})",
            "judge_at": str(judge),
            "as_of": str(as_of),
        }

    if hit:
        return {
            "prediction_id": pid,
            "status": "hit",
            "reason": f"{hit_rule.get('field')}={obs.get(hit_rule.get('field'))} "
                      f"{hit_rule.get('op')} {hit_rule.get('threshold')}  ✓  {prediction.get('notes', '').strip()}",
            "judge_at": str(judge),
            "as_of": str(as_of),
        }
    return {
        "prediction_id": pid,
        "status": "miss",
        "reason": f"{hit_rule.get('field')}={obs.get(hit_rule.get('field'))} "
                  f"NOT {hit_rule.get('op')} {hit_rule.get('threshold')}  ✗  {prediction.get('notes', '').strip()}",
        "judge_at": str(judge),
        "as_of": str(as_of),
    }


def to_ledger_row(prediction, result):
    """refine_recommend.md §2-2 ledger markdown row 1줄."""
    return (f"| {result['prediction_id']} | {result['judge_at']} | "
            f"{'도래' if result['status'] in ('hit','miss') else 'pending'} | "
            f"{result['status']} | {result['reason']} |")


def render_ledger(predictions, results):
    out = ["| 예측 ID | 판정 시점 | 도래 여부 | hit/miss/pending | 채점 근거 |",
           "|---|---|---|---|---|"]
    for p, r in zip(predictions, results):
        out.append(to_ledger_row(p, r))
    return "\n".join(out)


def main(argv=None):
    p = argparse.ArgumentParser(description="thesis 예측 채점 (refine_recommend.md 양식)")
    p.add_argument("predictions", help="prediction JSON (단일 또는 배열) 경로")
    p.add_argument("--as-of", default=None, help="채점 기준일 YYYY-MM-DD. 미지정 시 today.")
    p.add_argument("--format", choices=["json", "ledger"], default="ledger")
    args = p.parse_args(argv)

    data = json.loads(Path(args.predictions).read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = [data]

    results = [score(pred, as_of=args.as_of) for pred in data]

    if args.format == "json":
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print(render_ledger(data, results))


if __name__ == "__main__":
    main()
