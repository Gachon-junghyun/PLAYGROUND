"""compose — sources + texts를 batch로 나눠 요약 후 한 권짜리 입문서로 통합.

흐름 (map-reduce):
  [map]    sources를 batch-size 단위로 묶어 각각 핵심 요약 생성
  [reduce] batch 요약들을 모아 최종 입문서 markdown 작성

LLM 선택 (자동 fallback):
  ollama → anthropic → gemini → claude_inline (수동)

claude_inline 모드:
  data/<slug>/_compose/ 안에 prompt 파일들을 dump하고 종료한다.
  사용자(또는 Claude Code 세션)가 각 prompt 옆에 .response.md를 채워 넣은 다음
  `python compose.py "토픽" --collect` 로 응답들을 모아 최종 보고서를 조립한다.

CLI:
  python compose.py "토픽" [--batch-size 8] [--max-chars 4000]
                          [--provider auto|ollama|anthropic|gemini|claude_inline]
                          [--collect] [--clean] [--out reports/<slug>_full.md]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import urllib.request
from pathlib import Path

from _common import REPORTS_ROOT, get_ssl_context, read_jsonl, set_ssl_verify, topic_dir


AUTH_ORDER = {"high": 0, "medium": 1, "low": 2}


# ============================ LLM clients (synthesize.py와 동일 패턴) ============================

def _try_ollama(model: str):
    try:
        from ai.ollama import OllamaClient
        c = OllamaClient(model_name=model)
        _ = c.chat([{"role": "user", "content": "ok"}], format=None)
        return ("ollama", c)
    except Exception as e:
        print(f"[compose] Ollama 사용 불가: {type(e).__name__}: {str(e)[:120]}", file=sys.stderr)
        return None


def _try_gemini():
    try:
        from ai.gemini import GeminiClient
        c = GeminiClient()
        _ = c.chat([{"role": "user", "content": "ok"}])
        return ("gemini", c)
    except Exception as e:
        print(f"[compose] Gemini 사용 불가: {type(e).__name__}: {str(e)[:120]}", file=sys.stderr)
        return None


class _AnthropicClient:
    def __init__(self, model: str = "claude-sonnet-4-6"):
        self.api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY 환경변수 없음")
        self.model = model

    def chat(self, messages, **_):
        system = None
        msgs = []
        for m in messages:
            if m["role"] == "system":
                system = m["content"]
            else:
                msgs.append({"role": m["role"], "content": m["content"]})
        body = {"model": self.model, "max_tokens": 4000, "messages": msgs}
        if system:
            body["system"] = system
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=120, context=get_ssl_context()) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return "\n".join(b["text"] for b in data.get("content", []) if b.get("type") == "text")


def _try_anthropic(model: str):
    try:
        c = _AnthropicClient(model)
        _ = c.chat([{"role": "user", "content": "ok"}])
        return ("anthropic", c)
    except Exception as e:
        print(f"[compose] Anthropic 사용 불가: {type(e).__name__}: {str(e)[:120]}", file=sys.stderr)
        return None


def _pick_client(provider: str, model: str):
    if provider == "claude_inline":
        return ("claude_inline", None)
    candidates = []
    if provider in ("auto", "ollama"):
        candidates.append(lambda: _try_ollama(model))
    if provider in ("auto", "anthropic"):
        candidates.append(lambda: _try_anthropic("claude-sonnet-4-6"))
    if provider in ("auto", "gemini"):
        candidates.append(lambda: _try_gemini())
    for fn in candidates:
        r = fn()
        if r:
            return r
    if provider == "auto":
        return ("claude_inline", None)
    raise RuntimeError(f"provider={provider} 클라이언트 확보 실패")


# ============================ batch 구성 ============================

_META_LINE = re.compile(r"^(year|citations|authors|venue|doi|info|score|comments|tags|site|flair|r/)\s*[:/]", re.I)


def _strip_meta(body: str) -> str:
    if not body:
        return ""
    lines = []
    for ln in body.splitlines():
        s = ln.strip()
        if not s:
            continue
        if _META_LINE.match(s):
            continue
        lines.append(s)
    return "\n".join(lines).strip()


def _excerpt(text: str, max_chars: int) -> str:
    text = _strip_meta(text)
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "…"


def _source_block(src: dict, tdir: Path, max_chars: int) -> str:
    """LLM 컨텍스트에 박을 source 한 건의 표현. id로 인용 가능."""
    abstract = src.get("abstract", "")
    type_ = src.get("type", "")
    body = ""

    prefer_abstract = type_ in ("paper", "survey", "wiki", "standard", "textbook") and len(abstract) >= 150
    if prefer_abstract:
        body = abstract
    else:
        tp = src.get("text_path")
        if tp:
            p = tdir / tp
            if p.exists():
                body = p.read_text(encoding="utf-8")
        if not body:
            body = abstract

    body = _excerpt(body, max_chars)
    meta = []
    if src.get("year"):
        meta.append(f"year={src['year']}")
    if src.get("score") is not None:
        meta.append(f"score={src['score']}")
    meta.append(f"auth={src['authority']}")
    meta.append(f"type={src['type']}")
    meta_str = " ".join(meta)
    return (
        f"[{src['id']}] {src['title']}\n"
        f"  url: {src['url']}\n"
        f"  {meta_str}\n"
        f"  body: {body}\n"
    )


def _build_batches(sources: list[dict], tdir: Path, batch_size: int, max_chars: int) -> list[list[dict]]:
    """offtopic 제외, 권위·score 정렬, batch_size 단위로 묶기."""
    ontopic = [s for s in sources if not s.get("offtopic")]
    ontopic.sort(
        key=lambda s: (AUTH_ORDER[s["authority"]], -(s.get("score") or 0), -(s.get("year") or 0))
    )
    return [ontopic[i:i + batch_size] for i in range(0, len(ontopic), batch_size)]


# ============================ prompts ============================

BATCH_SYSTEM = (
    "당신은 한 토픽에 대한 자료 batch를 받아 핵심을 한국어로 요약하는 어시스턴트다. "
    "주어진 자료(SOURCES) 외 정보는 가져오지 마라(환각 금지). "
    "각 주장 끝에 [src_xxx] 인용을 반드시 붙여라. 마크다운만 출력하고 인사말은 쓰지 마라."
)

BATCH_USER_TEMPLATE = """\
다음 자료 batch를 읽고 한국어로 정리하라. 형식:

## 이 batch의 핵심
- bullet 5~8개. 각 bullet 끝에 [src_xxx] 인용.
- 자료 간 의견이 갈리거나 보완하는 부분이 있으면 명시.

## 등장한 고유 명사·기술·기업
- bullet. 출처 [src_xxx] 포함.

자료에 없는 내용은 쓰지 말 것.

---
TOPIC: {topic}
BATCH: {batch_no}/{batch_total}

SOURCES:
{ctx}
"""

COMPOSE_SYSTEM = (
    "당신은 한 토픽에 대한 batch 요약 묶음을 받아 입문서 한 편을 한국어로 합성하는 어시스턴트다. "
    "주어진 요약(BATCH SUMMARIES)의 정보만 쓰고 환각하지 마라. "
    "각 주장 끝에 [src_xxx] 인용을 붙이고, 인용이 없으면 그 문장은 쓰지 마라. "
    "마크다운 출력. 머릿글이나 인사말 없이 바로 본문으로 시작."
)

COMPOSE_USER_TEMPLATE = """\
다음 batch 요약들을 통합해 입문서 한 편을 한국어로 작성하라. 형식:

# {topic}

## TL;DR
- 3~5문장. 토픽이 뭔지, 왜 중요한지, 핵심 갈래는.

## 정의와 범위
- 여러 자료가 정의한 방식을 비교·정합. [src_xxx] 인용.

## 핵심 구성 요소·기술
- 자료에서 반복적으로 등장한 기술·구성 요소를 묶어 설명. 각 요소에 [src_xxx].

## 주요 플레이어 (기업·인물·기관)
- 표 형식. 컬럼: 이름 / 역할 / 근거. 근거는 [src_xxx].

## 연구·학술 동향
- 학술 자료에서 드러나는 연구 흐름·쟁점. [src_xxx].

## 산업·시장·정책
- 산업/투자/규제 측면에서 언급된 것들. [src_xxx].

## 비판·논쟁·미해결 문제
- 자료들 사이의 긴장이나 한계 지적. [src_xxx].

## 학습 경로
- 입문→심화 순서로 5~8건 추천. 각 줄: [src_xxx] 제목 — 한 줄 설명.

자료 없으면 빈 섹션으로 두지 말고 "(이 자료 묶음에서는 다루어지지 않음)"이라 명시.

---
TOPIC: {topic}

BATCH SUMMARIES:
{summaries}
"""


# ============================ map (batch summarize) ============================

def _compose_dir(tdir: Path) -> Path:
    d = tdir / "_compose"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _write_batch_prompt(cdir: Path, batch_no: int, batch_total: int, topic: str, ctx: str) -> Path:
    user = BATCH_USER_TEMPLATE.format(
        topic=topic, batch_no=batch_no, batch_total=batch_total, ctx=ctx
    )
    prompt_path = cdir / f"batch_{batch_no:02d}.prompt.md"
    prompt_path.write_text(
        f"<!-- SYSTEM -->\n{BATCH_SYSTEM}\n\n<!-- USER -->\n{user}\n",
        encoding="utf-8",
    )
    return prompt_path


def _run_llm(client_kind: str, client, system: str, user: str) -> str:
    msgs = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    try:
        return client.chat(msgs, format=None)
    except TypeError:
        return client.chat(msgs)


def cmd_dispatch(args) -> int:
    """1단계: batch 만들고 LLM 호출 또는 prompt 파일 dump."""
    tdir = topic_dir(args.topic)
    sources = list(read_jsonl(tdir / "sources.jsonl"))
    if not sources:
        print("[compose] sources.jsonl 없음 — aggregate 먼저", file=sys.stderr)
        return 1

    if args.clean:
        cdir = tdir / "_compose"
        if cdir.exists():
            shutil.rmtree(cdir)
    cdir = _compose_dir(tdir)

    client_kind, client = _pick_client(args.provider, args.model)
    print(f"[compose] provider={client_kind}")

    batches = _build_batches(sources, tdir, args.batch_size, args.max_chars)
    print(f"[compose] sources(ontopic)={sum(len(b) for b in batches)}  batches={len(batches)}  size={args.batch_size}")

    for i, batch in enumerate(batches, start=1):
        ctx = "\n".join(_source_block(s, tdir, args.max_chars) for s in batch)
        user = BATCH_USER_TEMPLATE.format(topic=args.topic, batch_no=i, batch_total=len(batches), ctx=ctx)

        if client_kind == "claude_inline":
            ppath = _write_batch_prompt(cdir, i, len(batches), args.topic, ctx)
            rpath = cdir / f"batch_{i:02d}.response.md"
            print(f"  batch {i:02d} prompt → {ppath.name}  (응답 채울 곳: {rpath.name})")
            continue

        print(f"  batch {i:02d}/{len(batches)} — LLM 호출 ({len(ctx)}B)…")
        try:
            out = _run_llm(client_kind, client, BATCH_SYSTEM, user)
        except Exception as e:
            print(f"    실패: {type(e).__name__}: {e}", file=sys.stderr)
            continue
        rpath = cdir / f"batch_{i:02d}.response.md"
        rpath.write_text(out.strip() + "\n", encoding="utf-8")
        print(f"    → {rpath.name} ({len(out)}B)")

    if client_kind == "claude_inline":
        print()
        print("[compose] 다음 단계:")
        print(f"  1) {cdir} 안의 batch_NN.prompt.md 들을 Claude/사람이 읽고")
        print(f"     같은 자리에 batch_NN.response.md 로 응답을 저장")
        print(f"  2) python compose.py \"{args.topic}\" --collect")
    else:
        # 자동 collect까지
        return cmd_collect(args)

    return 0


# ============================ reduce (collect → compose) ============================

def cmd_collect(args) -> int:
    tdir = topic_dir(args.topic)
    cdir = tdir / "_compose"
    if not cdir.exists():
        print(f"[compose] {cdir} 없음 — dispatch 먼저", file=sys.stderr)
        return 1

    responses = sorted(cdir.glob("batch_*.response.md"))
    if not responses:
        print(f"[compose] {cdir} 안에 batch_NN.response.md 없음", file=sys.stderr)
        return 1

    parts = []
    for r in responses:
        t = r.read_text(encoding="utf-8").strip()
        if not t:
            continue
        parts.append(f"### {r.stem}\n{t}")
    summaries = "\n\n".join(parts)
    user = COMPOSE_USER_TEMPLATE.format(topic=args.topic, summaries=summaries)

    client_kind, client = _pick_client(args.provider, args.model)
    print(f"[compose --collect] provider={client_kind}  responses={len(responses)}")

    if client_kind == "claude_inline":
        cpath = cdir / "compose.prompt.md"
        cpath.write_text(
            f"<!-- SYSTEM -->\n{COMPOSE_SYSTEM}\n\n<!-- USER -->\n{user}\n",
            encoding="utf-8",
        )
        rpath = cdir / "compose.response.md"
        print(f"  최종 합성 prompt → {cpath.name}")
        print(f"  Claude/사람이 응답을 {rpath.name}에 저장한 뒤:")
        print(f"    python compose.py \"{args.topic}\" --finalize")
        return 0

    out = _run_llm(client_kind, client, COMPOSE_SYSTEM, user)
    return _write_final(args.topic, out, args.out)


def cmd_finalize(args) -> int:
    """claude_inline 흐름에서 compose.response.md → reports/<slug>_full.md."""
    tdir = topic_dir(args.topic)
    cdir = tdir / "_compose"
    cresp = cdir / "compose.response.md"
    if not cresp.exists():
        print(f"[compose --finalize] {cresp} 없음 — Claude/사람이 채워야 함", file=sys.stderr)
        return 1
    return _write_final(args.topic, cresp.read_text(encoding="utf-8"), args.out)


def _write_final(topic: str, content: str, out_arg: str | None) -> int:
    tdir = topic_dir(topic)
    out_path = Path(out_arg) if out_arg else (REPORTS_ROOT / f"{tdir.name}_full.md")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content.strip() + "\n", encoding="utf-8")
    print(f"[compose] {out_path}  ({len(content)} chars)")
    return 0


# ============================ CLI ============================

def main():
    p = argparse.ArgumentParser(description="batch 요약 → 통합 입문서 합성 (map-reduce)")
    p.add_argument("topic")
    p.add_argument("--batch-size", type=int, default=8)
    p.add_argument("--max-chars", type=int, default=4000, help="batch 내 source당 본문 cap")
    p.add_argument("--provider", choices=["auto", "ollama", "anthropic", "gemini", "claude_inline"], default="auto")
    p.add_argument("--model", default="gemma3", help="Ollama 모델명")
    p.add_argument("--out", help="최종 보고서 경로 (기본 reports/<slug>_full.md)")
    p.add_argument("--clean", action="store_true", help="_compose/ 디렉토리 비우고 시작")
    p.add_argument("--collect", action="store_true", help="batch 응답들 모아 최종 합성")
    p.add_argument("--finalize", action="store_true", help="compose.response.md → reports/<slug>_full.md")
    p.add_argument("--insecure", action="store_true", help="SSL 검증 비활성화")
    args = p.parse_args()

    if args.insecure:
        set_ssl_verify(False)

    if args.finalize:
        return cmd_finalize(args)
    if args.collect:
        return cmd_collect(args)
    return cmd_dispatch(args)


if __name__ == "__main__":
    sys.exit(main())
