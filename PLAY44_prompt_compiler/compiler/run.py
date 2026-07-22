"""B5. 실행기 — 원명령 → transform → retrieve → assemble → 실행, 그리고 진단 로그.

CLI:
  python run.py "명령"             # 조립 후 실행(claude -p 또는 Anthropic API)
  python run.py --dry-run "명령"    # 실행 없이 조립 프롬프트 + 로그만
  옵션: --cli (실행을 `claude -p` 서브프로세스로), 기본은 Anthropic API.

요청마다 logs/{timestamp}.json 에 4단계(변환/검색/조립/실행) 전부 기록 →
출력이 나쁠 때 어느 단계 실패인지 이 로그만으로 분리 진단.
"""
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from transform import transform
from retrieve import retrieve
from assemble import assemble
from embed_store import BACKEND

HERE = Path(__file__).resolve().parent
LOGS = HERE / "logs"


def _slim(r):
    """검색 레코드에서 진단에 필요한 필드만."""
    return {"id": r["id"], "type": r["type"], "aspect_matched": r.get("_aspect_matched"),
            "query_key": r.get("_query_key"), "dense": round(r.get("_dense", 0), 4),
            "bm25_rank": r.get("_bm25_rank"), "rrf": round(r.get("_rrf", 0), 5),
            "trigger": r["trigger"], "drop": r.get("_drop")}


def execute_api(prompt, model="claude-sonnet-4-6"):
    import anthropic
    client = anthropic.Anthropic()
    msg = client.messages.create(model=model, max_tokens=2000,
                                 messages=[{"role": "user", "content": prompt}])
    return msg.content[0].text


def execute_cli(prompt):
    p = subprocess.run(["claude", "-p", prompt], capture_output=True, text=True, timeout=300)
    return p.stdout if p.returncode == 0 else f"[claude -p 실패] {p.stderr}"


def run(command, dry_run=False, use_cli=False):
    LOGS.mkdir(exist_ok=True)
    log = {"command": command, "backend": BACKEND, "ts": datetime.now().isoformat()}

    # 1) 변환
    keys, tpath = transform(command)
    log["transform"] = {"path": tpath, "keys": keys}

    # 2) 검색
    res = retrieve(keys)
    log["retrieve"] = {"kept": [_slim(r) for r in res["kept"]],
                       "dropped": [_slim(r) for r in res["dropped"]],
                       "budget": res["budget"]}

    # 3) 조립
    asm = assemble(res, command)
    log["assemble"] = {"adopted_ids": asm["adopted_ids"], "conflict_log": asm["conflict_log"],
                       "block_order": asm["blocks"], "prompt": asm["prompt"]}

    # 4) 실행
    if dry_run:
        log["execute"] = {"path": "dry-run", "response": None}
    elif not os.environ.get("ANTHROPIC_API_KEY"):
        log["execute"] = {"path": "skipped:no_key", "response": None}
    else:
        try:
            resp = execute_cli(asm["prompt"]) if use_cli else execute_api(asm["prompt"])
            log["execute"] = {"path": "cli" if use_cli else "api", "response": resp}
        except Exception as e:
            log["execute"] = {"path": "error", "response": f"{type(e).__name__}: {e}"}

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    log_path = LOGS / f"{stamp}.json"
    log_path.write_text(json.dumps(log, ensure_ascii=False, indent=1), encoding="utf-8")
    return log, log_path


def main():
    args = sys.argv[1:]
    dry = "--dry-run" in args
    cli = "--cli" in args
    rest = [a for a in args if not a.startswith("--")]
    if not rest:
        print('usage: python run.py [--dry-run] [--cli] "명령"'); sys.exit(1)
    command = rest[0]
    log, path = run(command, dry_run=dry, use_cli=cli)
    print(f"[run] backend={log['backend']} transform={log['transform']['path']} "
          f"adopted={len(log['assemble']['adopted_ids'])} log={path}")
    if dry:
        print("\n===== 조립 프롬프트 =====\n")
        print(log["assemble"]["prompt"])
    elif log["execute"]["response"]:
        print("\n===== 모델 응답 =====\n")
        print(log["execute"]["response"])


if __name__ == "__main__":
    main()
