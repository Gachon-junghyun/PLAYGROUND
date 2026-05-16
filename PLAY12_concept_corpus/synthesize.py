"""synthesize — Ollama / Gemini / Anthropic로 보고서 LLM 합성 섹션 추가.

기본 동작: report.md 끝에 다음 섹션을 LLM 합성해서 append.
  - "## LLM 요약 (자동 합성)" — 3~5문장 토픽 요약
  - "## 핵심 논점 / 트레이드오프" — bullet
  - "## 학습 경로 추천" — 자료 ID 기반 추천 순서

옵션:
  --provider ollama|gemini|anthropic|auto
      auto: ollama → anthropic → gemini 순서로 시도
  --model <name>            Ollama / Anthropic 모델명
                            (Ollama 기본 gemma3, Anthropic 기본 claude-sonnet-4-6)
  --max-sources N           LLM에 던질 source 개수 (기본 12, 권위 high 우선)

자격증명:
  - Ollama: localhost:11434 에 서버 떠 있어야 함
  - Gemini: GEMINI_API_KEY 또는 GOOGLE_API_KEY (crawling/.env 또는 환경변수)
  - Anthropic: ANTHROPIC_API_KEY (환경변수)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

from _common import REPORTS_ROOT, get_ssl_context, read_jsonl, slugify, topic_dir


AUTH_ORDER = {"high": 0, "medium": 1, "low": 2}


def _try_ollama(model: str):
    try:
        from ai.ollama import OllamaClient
        c = OllamaClient(model_name=model)
        _ = c.chat([{"role": "user", "content": "ok"}], format=None)
        return ("ollama", c)
    except Exception as e:
        print(f"[synthesize] Ollama 사용 불가: {type(e).__name__}: {str(e)[:120]}", file=sys.stderr)
        return None


def _try_gemini():
    try:
        from ai.gemini import GeminiClient
        c = GeminiClient()
        # 짧은 ping으로 key 검증
        _ = c.chat([{"role": "user", "content": "ok"}])
        return ("gemini", c)
    except Exception as e:
        print(f"[synthesize] Gemini 사용 불가: {type(e).__name__}: {str(e)[:120]}", file=sys.stderr)
        return None


class _AnthropicClient:
    """anthropic SDK 없이 urllib로 직접 호출하는 미니 클라이언트."""

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
        body = {
            "model": self.model,
            "max_tokens": 2000,
            "messages": msgs,
        }
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
        with urllib.request.urlopen(req, timeout=60, context=get_ssl_context()) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        parts = [b["text"] for b in data.get("content", []) if b.get("type") == "text"]
        return "\n".join(parts)


def _try_anthropic(model: str):
    try:
        c = _AnthropicClient(model)
        _ = c.chat([{"role": "user", "content": "ok"}])
        return ("anthropic", c)
    except Exception as e:
        print(f"[synthesize] Anthropic 사용 불가: {type(e).__name__}: {str(e)[:120]}", file=sys.stderr)
        return None


def _client_chat(client, system: str, user: str, format: str | None = None) -> str:
    msgs = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    try:
        return client.chat(msgs, format=format)
    except TypeError:
        return client.chat(msgs)


def _pick_sources(sources: list[dict], max_n: int) -> list[dict]:
    sorted_ = sorted(
        sources,
        key=lambda s: (
            AUTH_ORDER[s["authority"]],
            -(s.get("score") or 0),
            -(s.get("year") or 0),
        ),
    )
    return sorted_[:max_n]


def _format_context(topic: str, picks: list[dict], tdir: Path, text_chars_per_src: int = 1200) -> str:
    lines = [f"TOPIC: {topic}", "", "SOURCES:"]
    for s in picks:
        lines.append(f"\n[{s['id']}] ({s['authority']}, {s['type']}, "
                     f"score={s.get('score','-')}, year={s.get('year','-')}) {s['title']}")
        lines.append(f"  url: {s['url']}")
        # 본문이 있으면 일부 첨부
        text_path = s.get("text_path")
        if text_path:
            p = tdir / text_path
            if p.exists():
                t = p.read_text(encoding="utf-8")
                lines.append("  text: " + t[:text_chars_per_src].replace("\n", " "))
                continue
        # fallback: abstract
        if s.get("abstract"):
            lines.append("  abstract: " + s["abstract"][:text_chars_per_src].replace("\n", " "))
    return "\n".join(lines)


SYSTEM_PROMPT = (
    "당신은 한 토픽에 대한 자료 묶음을 받아 한국어 입문서를 합성하는 어시스턴트다. "
    "주어진 SOURCES 외의 정보는 절대 가져오지 말고(환각 금지), "
    "각 주장 끝에 자료를 인용할 때는 반드시 [src_xxx] 형식만 사용한다. "
    "답변은 마크다운만, 머릿글이나 인사말 없이 바로 내용으로 시작한다."
)


USER_TEMPLATE = """\
다음 자료를 읽고 세 섹션을 마크다운으로 작성하라.

1) "## LLM 요약 (자동 합성)" — 토픽의 핵심을 3~5문장.
2) "## 핵심 논점 / 트레이드오프" — bullet 5개 이하. 자료 간 의견 차이나 긴장 관계가 있으면 명시.
3) "## 학습 경로 추천" — 자료 ID([src_xxx])를 입문→심화 순서로 5~8개 정렬, 각 1줄 설명.

각 주장에 [src_xxx] 인용 필수. SOURCES에 없는 내용은 쓰지 마라.

---
{ctx}
"""


def synthesize(topic: str, provider: str, model: str, max_sources: int) -> str:
    tdir = topic_dir(topic)
    sources = list(read_jsonl(tdir / "sources.jsonl"))
    if not sources:
        print("[synthesize] sources.jsonl 없음 — aggregate 먼저", file=sys.stderr)
        sys.exit(1)

    # client 선택 (auto: ollama → anthropic → gemini)
    candidates: list = []
    if provider == "auto":
        candidates = [
            lambda: _try_ollama(model),
            lambda: _try_anthropic("claude-sonnet-4-6"),
            lambda: _try_gemini(),
        ]
    elif provider == "ollama":
        candidates = [lambda: _try_ollama(model)]
    elif provider == "anthropic":
        candidates = [lambda: _try_anthropic(model if model != "gemma3" else "claude-sonnet-4-6")]
    elif provider == "gemini":
        candidates = [lambda: _try_gemini()]

    used, client = None, None
    for fn in candidates:
        r = fn()
        if r:
            used, client = r
            break
    if not client:
        print("[synthesize] 사용 가능한 LLM 클라이언트 없음. 건너뜀.", file=sys.stderr)
        return ""

    picks = _pick_sources(sources, max_sources)
    ctx = _format_context(topic, picks, tdir)
    user = USER_TEMPLATE.format(ctx=ctx)
    print(f"[synthesize] provider={used}  sources_used={len(picks)}  ctx_bytes={len(ctx)}")

    text = _client_chat(client, SYSTEM_PROMPT, user, format=None)
    text = text.strip()

    # report.md 끝에 append (이미 존재 가정)
    report_path = REPORTS_ROOT / f"{tdir.name}.md"
    sep = f"\n\n---\n\n_LLM 합성 by {used} ({model if used=='ollama' else 'gemini'})_\n\n"
    if report_path.exists():
        existing = report_path.read_text(encoding="utf-8")
        # 기존 합성 섹션이 있으면 잘라내고 새로 붙임
        marker = "\n---\n\n_LLM 합성 by"
        if marker in existing:
            existing = existing.split(marker, 1)[0].rstrip() + "\n"
        report_path.write_text(existing.rstrip() + sep + text + "\n", encoding="utf-8")
    else:
        report_path.write_text(f"# {topic}\n" + sep + text + "\n", encoding="utf-8")

    print(f"[synthesize] {report_path}  (+{len(text)} chars)")
    return text


def main():
    p = argparse.ArgumentParser()
    p.add_argument("topic")
    p.add_argument("--provider", choices=["auto", "ollama", "anthropic", "gemini"], default="auto")
    p.add_argument("--model", default="gemma3", help="Ollama 모델명")
    p.add_argument("--max-sources", type=int, default=12)
    args = p.parse_args()
    synthesize(args.topic, args.provider, args.model, args.max_sources)
    return 0


if __name__ == "__main__":
    sys.exit(main())
