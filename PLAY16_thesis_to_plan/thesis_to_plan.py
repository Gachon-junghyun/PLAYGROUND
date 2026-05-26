"""thesis state_report.md → PLAY14 trade_planner 입력 JSON 어댑터.

mvp `research_Mvp/llm_outputs/.../state_report.md`의 *Block 6* 표
(`| 종목 | 현재가 | 시총 | TTM/Fwd PER | 컨센 상승여력 | ... |`)에서
종목별 entry(=현재가), direction(=상승여력 부호), confidence(=상승여력 magnitude 정규화)를
추출. 권유가 아니라 *thesis가 시사하는 매매 가정을 PLAY14 입력 형식으로 옮기는 어댑터*.

PLAY14가 받을 수 있는 JSON 한 줄(또는 array)을 출력.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


# Block 6 시작 휴리스틱: 머리글에 "현재가" + "상승여력" 둘 다 등장하는 표.
HEADER_KEYS = ("현재가", "상승여력")

# 종목명(코드) 패턴: "효성중(298040)" 또는 "효성중공업 298040" 모두 잡기.
TICKER_RE = re.compile(r"(?P<name>[가-힣A-Za-z0-9·\s]+?)\s*[\(（]?(?P<code>\d{6})[\)）]?")
# % 추출 (선택적 부호, **bold**, *italic*)
PCT_RE = re.compile(r"([+\-]?\s*\d+(?:\.\d+)?)\s*%")


def parse_state_report(text):
    """state_report.md 텍스트 → list[dict]. 각 dict는 PLAY14 입력 후보."""
    lines = text.splitlines()
    # Block 6 표 찾기
    header_idx = None
    for i, line in enumerate(lines):
        if line.lstrip().startswith("|") and all(k in line for k in HEADER_KEYS):
            header_idx = i
            break
    if header_idx is None:
        raise ValueError("Block 6 표를 찾지 못함 (헤더에 '현재가'+'상승여력' 동시 매칭 실패)")

    header_cols = [c.strip() for c in lines[header_idx].strip("|").split("|")]
    # 표 본문은 헤더 + 구분선 다음
    body_start = header_idx + 2
    rows = []
    for j in range(body_start, len(lines)):
        line = lines[j]
        if not line.lstrip().startswith("|"):
            break
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < len(header_cols):
            continue
        rows.append(dict(zip(header_cols, cells)))

    candidates = []
    for r in rows:
        first_col = next(iter(r.values()))
        m = TICKER_RE.search(first_col)
        if not m:
            continue
        name, code = m.group("name").strip(), m.group("code")

        # 현재가 — 콤마 제거 후 float
        price_raw = r.get("현재가", "").replace(",", "").replace("**", "").strip()
        try:
            entry = float(price_raw)
        except ValueError:
            continue

        # 상승여력 — bold/italic 제거 후 % 추출 (첫 번째 매칭)
        upside_raw = r.get("컨센 상승여력", "")
        m_pct = PCT_RE.search(upside_raw.replace("**", "").replace("*", ""))
        if not m_pct:
            continue
        upside = float(m_pct.group(1).replace(" ", ""))

        direction = "long" if upside >= 0 else "short"
        # confidence: |upside| / 50 cap 1.0  — 50% 이상이면 max confidence
        confidence = round(min(abs(upside) / 50.0, 1.0), 3)

        # atr_mult_suggested: confidence가 낮을수록 타이트한 stop(작은 mult), 높을수록 여유.
        # 0.5R~2.0R 사이 매핑. confidence 0 → 0.8, 1.0 → 2.0
        atr_mult = round(0.8 + confidence * 1.2, 2)

        candidates.append({
            "ticker": code,
            "name": name,
            "entry": entry,
            "direction": direction,
            "confidence": confidence,
            "upside_pct": upside,
            "atr_mult_suggested": atr_mult,
            "source_row": {k: v for k, v in r.items() if k in (header_cols[0], "현재가", "컨센 상승여력")},
        })

    return candidates


def main(argv=None):
    p = argparse.ArgumentParser(description="state_report.md → PLAY14 입력 JSON")
    p.add_argument("path", help="state_report.md 경로")
    p.add_argument("--ticker", default=None, help="특정 종목만 필터 (6자리 코드)")
    p.add_argument("--out", default=None, help="출력 경로. 미지정 시 stdout.")
    p.add_argument("--pretty", action="store_true")
    args = p.parse_args(argv)

    text = Path(args.path).read_text(encoding="utf-8")
    candidates = parse_state_report(text)
    if args.ticker:
        candidates = [c for c in candidates if c["ticker"] == args.ticker]

    js = json.dumps(candidates, ensure_ascii=False, indent=2 if args.pretty else None)
    if args.out:
        Path(args.out).write_text(js, encoding="utf-8")
        print(f"[adapter] wrote {args.out} ({len(candidates)} plans)", file=sys.stderr)
    else:
        print(js)
    return candidates


if __name__ == "__main__":
    main()
