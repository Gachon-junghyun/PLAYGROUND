"""enrich — sources.jsonl을 돌면서 본문(raw_text)을 채운다.

3가지 정책 다 지원:
  --mode full      : 모든 source 통원문 (--max-bytes 까지)
  --mode digest    : 모든 source 발췌만 (--digest-target 바이트)
  --mode hybrid    : authority=high만 full, 나머진 digest (기본)

per-source override:
  sources.jsonl의 enrich_policy 필드가 "force_full" / "force_digest" / "skip"이면
  CLI --mode를 이긴다.

본문은 texts/<src_id>.{full|digest}.txt 로 저장 (jsonl을 가볍게 유지).
실제 fetch는 urllib + html.parser (표준 라이브러리). 차단되거나 JS 렌더링 필요면 실패.
--dry-run 으로 외부 fetch 없이 abstract를 raw_text로 흉내내기 (시연용).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

from _common import get_ssl_context, read_jsonl, set_ssl_verify, topic_dir, write_jsonl


def _raw_body_for(src: dict, raw_hits_by_url: dict) -> str:
    """sources에 대응하는 raw_hit의 raw_body를 찾아 반환. 없으면 빈 문자열."""
    hit = raw_hits_by_url.get(src["url"])
    if not hit:
        return ""
    return hit.get("raw_body") or hit.get("abstract") or ""


USER_AGENT = "Mozilla/5.0 (compatible; PLAY12-concept-corpus/0.1)"


# -------------- HTML → text --------------

class _TextExtractor(HTMLParser):
    SKIP_TAGS = {"script", "style", "noscript", "svg", "head"}

    def __init__(self):
        super().__init__()
        self._chunks: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP_TAGS:
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag in self.SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1
        # 단락 구분
        if tag in {"p", "br", "li", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "div"}:
            self._chunks.append("\n")

    def handle_data(self, data):
        if self._skip_depth:
            return
        if data.strip():
            self._chunks.append(data)

    def text(self) -> str:
        raw = "".join(self._chunks)
        # 공백 정리
        raw = re.sub(r"[ \t]+", " ", raw)
        raw = re.sub(r"\n\s*\n+", "\n\n", raw)
        return raw.strip()


def _ascii_safe_url(url: str) -> str:
    """비ASCII 문자가 든 URL을 percent-encode. 이미 인코딩된 %XX는 안 건드림."""
    return urllib.parse.quote(url, safe=":/?&=#%@!$()*+,;~")


def fetch_text(url: str, timeout: float = 10.0, max_bytes: int = 500_000) -> str:
    safe_url = _ascii_safe_url(url)
    req = urllib.request.Request(safe_url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout, context=get_ssl_context()) as resp:
        ctype = resp.headers.get("Content-Type", "")
        raw = resp.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raw = raw[:max_bytes]
    # 인코딩 추론
    enc = "utf-8"
    m = re.search(r"charset=([\w\-]+)", ctype, re.I)
    if m:
        enc = m.group(1)
    try:
        html = raw.decode(enc, errors="replace")
    except LookupError:
        html = raw.decode("utf-8", errors="replace")

    if "html" not in ctype.lower() and not html.lstrip().startswith("<"):
        return html  # plain text
    ex = _TextExtractor()
    ex.feed(html)
    return ex.text()


# -------------- digest 만들기 --------------

def make_digest(full_text: str, target_bytes: int, abstract: str = "") -> str:
    """abstract + 본문에서 정보 밀도 높은 문장 골라 target_bytes 근처까지 채움.

    정밀한 요약 아님 — 표준 라이브러리만 쓰는 휴리스틱.
    스코어링: 길이(너무 짧은 줄 패널티) + 키워드 신호 + 본문 앞쪽 가산점.
    """
    pieces = [s.strip() for s in re.split(r"(?<=[.!?。!?])\s+|\n+", full_text) if s.strip()]
    if not pieces:
        return abstract

    SIGNAL_RE = re.compile(
        r"\b(definition|defined|introduce|propose|method|standard|"
        r"survey|review|overview|conclude|result|"
        r"개요|정의|분류|종류|구성|원리|방법|결과|결론|특징)\b",
        re.I,
    )

    scored = []
    for i, s in enumerate(pieces):
        if len(s) < 20:
            continue
        score = 0.0
        score += min(len(s), 240) / 240.0
        score += 1.5 if SIGNAL_RE.search(s) else 0.0
        score += max(0.0, 1.0 - i / 50.0)  # 앞쪽 가산점
        scored.append((score, i, s))

    scored.sort(key=lambda t: -t[0])

    selected_idx = set()
    buf = []
    total = 0
    if abstract:
        buf.append("[ABSTRACT]")
        buf.append(abstract.strip())
        buf.append("")
        total += len(abstract.encode("utf-8")) + 16

    for _, i, s in scored:
        b = len(s.encode("utf-8")) + 1
        if total + b > target_bytes:
            continue
        selected_idx.add(i)
        total += b
        if total >= target_bytes * 0.95:
            break

    # 원래 순서대로 정렬해 재조립
    body = [pieces[i] for i in sorted(selected_idx)]
    if body:
        buf.append("[EXCERPTS]")
        buf.extend(body)
    return "\n".join(buf).strip()


# -------------- mode 결정 --------------

def resolve_mode(src: dict, cli_mode: str) -> str:
    """per-source override > CLI mode."""
    pol = src.get("enrich_policy")
    if pol == "force_full":
        return "full"
    if pol == "force_digest":
        return "digest"
    if pol == "skip":
        return "skip"
    if cli_mode == "hybrid":
        return "full" if src.get("authority") == "high" else "digest"
    return cli_mode


# -------------- 메인 --------------

def parse_where(expr: str | None) -> dict[str, str]:
    if not expr:
        return {}
    out = {}
    for clause in expr.split(","):
        if "=" not in clause:
            continue
        k, v = clause.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def match_where(src: dict, where: dict) -> bool:
    for k, v in where.items():
        if str(src.get(k)) != v:
            return False
    return True


def enrich(args) -> int:
    tdir = topic_dir(args.topic)
    src_path = tdir / "sources.jsonl"
    if not src_path.exists():
        print(f"[enrich] {src_path} 없음 — 먼저 aggregate", file=sys.stderr)
        return 1

    sources = list(read_jsonl(src_path))
    where = parse_where(args.where)
    only = set(args.only) if args.only else None

    # raw_hits.jsonl 로드 → URL 별 raw_body 재활용
    raw_hits_by_url: dict[str, dict] = {}
    rh_path = tdir / "raw_hits.jsonl"
    if rh_path.exists():
        for h in read_jsonl(rh_path):
            raw_hits_by_url[h["url"]] = h

    n_full = n_digest = n_skip = n_fail = n_already = n_reused = 0

    for src in sources:
        sid = src["id"]
        if only and sid not in only:
            continue
        if where and not match_where(src, where):
            continue

        mode = resolve_mode(src, args.mode)
        if mode == "skip":
            n_skip += 1
            continue

        if not args.force and src.get("text_mode") == mode and src.get("text_path"):
            n_already += 1
            continue

        # --- 본문 확보
        if args.dry_run:
            full_text = src.get("abstract", "") + "\n\n" + (src.get("title", "") + " (dry-run stub).")
        else:
            # 1순위: raw_hits에 이미 받은 body가 충분히 길면 그걸 활용 (이중 fetch 회피)
            raw_body = _raw_body_for(src, raw_hits_by_url)
            if not args.force_fetch and len(raw_body) >= args.reuse_threshold:
                full_text = raw_body
                n_reused += 1
            else:
                try:
                    full_text = fetch_text(src["url"], timeout=args.timeout, max_bytes=args.max_bytes)
                    # raw_body가 더 길면 본문을 합쳐서 활용
                    if raw_body and len(raw_body) > len(full_text):
                        full_text = raw_body
                except (urllib.error.URLError, TimeoutError, ConnectionError, ValueError) as e:
                    msg = f"{type(e).__name__}: {e}"
                    # raw_body라도 있으면 그걸로 fallback
                    if raw_body:
                        print(f"  [{sid}] fetch 실패 ({msg}) — raw_body로 대체")
                        full_text = raw_body
                    elif args.fallback_abstract and src.get("abstract"):
                        print(f"  [{sid}] fetch 실패 ({msg}) — abstract로 대체")
                        full_text = src["abstract"]
                    else:
                        print(f"  [{sid}] fetch 실패 ({msg}) — 건너뜀")
                        src["text_mode"] = "none"
                        src["text_path"] = None
                        src["text_bytes"] = 0
                        src["enriched_at"] = dt.date.today().isoformat()
                        n_fail += 1
                        continue

        # --- mode별 가공
        if mode == "full":
            body = full_text[: args.max_bytes] if len(full_text) > args.max_bytes else full_text
            suffix = "full"
        else:  # digest
            body = make_digest(full_text, args.digest_target, abstract=src.get("abstract", ""))
            suffix = "digest"

        rel_path = Path("texts") / f"{sid}.{suffix}.txt"
        abs_path = tdir / rel_path
        abs_path.write_text(body, encoding="utf-8")

        src["text_path"] = str(rel_path).replace("\\", "/")
        src["text_mode"] = mode
        src["text_bytes"] = len(body.encode("utf-8"))
        src["enriched_at"] = dt.date.today().isoformat()

        if mode == "full":
            n_full += 1
            print(f"  [{sid}] full  {src['text_bytes']:>7d}B  {src['title'][:60]}")
        else:
            n_digest += 1
            print(f"  [{sid}] digest {src['text_bytes']:>6d}B  {src['title'][:60]}")

    write_jsonl(src_path, sources)

    print(f"[enrich] mode={args.mode}  full={n_full}  digest={n_digest}  "
          f"reused={n_reused}  skip={n_skip}  fail={n_fail}  already={n_already}")
    print(f"  texts: {tdir / 'texts'}")
    return 0


def main():
    p = argparse.ArgumentParser(description="sources.jsonl 본문 보강 (mode-aware)")
    p.add_argument("topic")
    p.add_argument("--mode", choices=["full", "digest", "hybrid"], default="hybrid")
    p.add_argument("--max-bytes", type=int, default=200_000,
                   help="full 모드 source당 최대 바이트 (기본 200KB)")
    p.add_argument("--digest-target", type=int, default=6_000,
                   help="digest 모드 목표 바이트 (기본 6KB)")
    p.add_argument("--timeout", type=float, default=10.0)
    p.add_argument("--only", nargs="+", help="특정 src_id만")
    p.add_argument("--where", help="단순 필터, 예: 'authority=high,type=survey'")
    p.add_argument("--force", action="store_true", help="이미 enrich된 것도 덮어씀")
    p.add_argument("--dry-run", action="store_true",
                   help="외부 fetch 없이 abstract를 본문으로 흉내내기 (시연용)")
    p.add_argument("--fallback-abstract", action="store_true",
                   help="fetch 실패 시 abstract를 본문으로 대체 (arxiv PDF 등에 유용)")
    p.add_argument("--insecure", action="store_true",
                   help="SSL 인증서 검증 비활성화 (Windows에서 시스템 CA 못 잡을 때 우회)")
    p.add_argument("--reuse-threshold", type=int, default=1500,
                   help="raw_hits.raw_body가 이 바이트 이상이면 외부 fetch 없이 그대로 활용 (기본 1500)")
    p.add_argument("--force-fetch", action="store_true",
                   help="raw_body가 있어도 항상 외부 fetch 강행")
    args = p.parse_args()
    if args.insecure:
        set_ssl_verify(False)
    return enrich(args)


if __name__ == "__main__":
    sys.exit(main())
