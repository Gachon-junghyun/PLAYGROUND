"""
PLAYGROUND 트리의 모든 *.md를 Google Drive `PLAYGROUND/` 폴더로 단방향 미러.

사용:
  python -u sync_md.py              # 변경된 MD만 업로드
  python -u sync_md.py --dry-run    # 무엇이 올라갈지만 출력 (네트워크 요청 없음, OAuth만 진행)
  python -u sync_md.py --reset      # 로컬 config.json 백업 후 새로 만듦 (Drive 폴더는 재사용)
  python -u sync_md.py auth         # token.json 삭제하고 OAuth 재실행

설계:
  - drive.file scope: 이 OAuth client가 만든 폴더/파일만 보임. 사용자의 다른 Drive 자료에 접근 안 함.
  - 단방향 (local → Drive). 로컬에서 삭제·이동해도 Drive는 유지됨 (수동 정리).
  - md5 비교로 변경분만 업로드. 매 파일마다 config.json을 즉시 저장해 중간 실패에 강함.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from drive_client import DriveClient

HERE = Path(__file__).resolve().parent
PLAYGROUND_ROOT = HERE.parent  # PLAY1_sync의 상위 디렉토리 = PLAYGROUND/
CONFIG_PATH = HERE / "config.json"
CREDENTIALS_PATH = HERE / "credentials.json"
TOKEN_PATH = HERE / "token.json"

ROOT_FOLDER_NAME = "PLAYGROUND"

# walk 시 무시할 디렉토리 이름들
SKIP_DIR_PARTS = {"__pycache__", ".git", ".venv", "node_modules", ".idea", ".vscode", "output"}


def md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_config() -> dict:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return {"root_folder_id": None, "folders": {}, "files": {}}


def save_config(cfg: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")


def find_md_files() -> list[Path]:
    out: list[Path] = []
    for p in PLAYGROUND_ROOT.rglob("*.md"):
        rel_parts = p.relative_to(PLAYGROUND_ROOT).parts
        if any(part in SKIP_DIR_PARTS for part in rel_parts):
            continue
        out.append(p)
    out.sort()
    return out


def ensure_folder_chain(client: DriveClient, cfg: dict, rel_dir: Path, root_id: str) -> str:
    """rel_dir 경로(Path('.') 또는 Path('PLAY1_sync') 등)에 대응하는 Drive 폴더 체인을 만들고 leaf id 반환."""
    if str(rel_dir) in (".", ""):
        return root_id

    parent_id = root_id
    accumulated = Path()
    for part in rel_dir.parts:
        accumulated = accumulated / part
        key = str(accumulated).replace("\\", "/")
        if key not in cfg["folders"]:
            fid = client.ensure_folder(part, parent_id=parent_id)
            cfg["folders"][key] = fid
            print(f"  [folder] {key} → {fid}", flush=True)
        parent_id = cfg["folders"][key]
    return parent_id


def cmd_sync(reset: bool, dry_run: bool) -> None:
    if reset and CONFIG_PATH.exists():
        bak = CONFIG_PATH.with_suffix(".json.bak")
        if bak.exists():
            bak.unlink()
        CONFIG_PATH.rename(bak)
        print(f"  [reset] config.json → {bak.name}", flush=True)

    cfg = load_config()
    client = DriveClient(CREDENTIALS_PATH, TOKEN_PATH)

    if not cfg.get("root_folder_id"):
        if dry_run:
            print(f"  [dry] would ensure '{ROOT_FOLDER_NAME}' folder on Drive", flush=True)
        else:
            cfg["root_folder_id"] = client.ensure_folder(ROOT_FOLDER_NAME)
            print(f"  [root] {ROOT_FOLDER_NAME} → {cfg['root_folder_id']}", flush=True)
            save_config(cfg)
    root_id = cfg.get("root_folder_id")

    md_files = find_md_files()
    print(f"\nfound {len(md_files)} markdown file(s) under {PLAYGROUND_ROOT}", flush=True)

    pushed = skipped = 0
    for md in md_files:
        rel = md.relative_to(PLAYGROUND_ROOT)
        rel_str = str(rel).replace("\\", "/")
        local_md5 = md5(md)

        entry = cfg["files"].get(rel_str, {})
        if entry.get("md5") == local_md5:
            print(f"  [skip] {rel_str}", flush=True)
            skipped += 1
            continue

        if dry_run:
            print(f"  [dry ] {rel_str}", flush=True)
            continue

        parent_id = ensure_folder_chain(client, cfg, rel.parent, root_id)
        file_id = entry.get("file_id")
        try:
            resp = client.upload_or_update(
                str(md), md.name, folder_id=parent_id, file_id=file_id
            )
        except Exception as e:
            # 저장된 file_id가 Drive에서 삭제됐거나 잘못된 경우 → 새 파일로 재시도
            if file_id:
                print(f"  [retry] {rel_str} (stale file_id, recreating): {e}", flush=True)
                resp = client.upload_or_update(
                    str(md), md.name, folder_id=parent_id, file_id=None
                )
            else:
                save_config(cfg)
                print(f"  [FAIL] {rel_str}: {e}", flush=True)
                raise

        cfg["files"][rel_str] = {"file_id": resp["id"], "md5": local_md5}
        save_config(cfg)
        print(f"  [push] {rel_str}", flush=True)
        pushed += 1

    save_config(cfg)
    print(f"\nDONE: pushed={pushed} skipped={skipped} total={len(md_files)}", flush=True)


def cmd_auth() -> None:
    if TOKEN_PATH.exists():
        TOKEN_PATH.unlink()
        print(f"removed: {TOKEN_PATH.name}", flush=True)
    DriveClient(CREDENTIALS_PATH, TOKEN_PATH)
    print("re-authenticated.", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Mirror PLAYGROUND/*.md → Google Drive")
    parser.add_argument("subcommand", nargs="?", default="sync", choices=["sync", "auth"],
                        help="sync (default) | auth")
    parser.add_argument("--reset", action="store_true",
                        help="config.json 백업 후 새로 만듦 (file_id 매핑 잃음 → 재업로드 발생)")
    parser.add_argument("--dry-run", action="store_true",
                        help="무엇이 올라갈지만 출력")
    args = parser.parse_args()

    try:
        if args.subcommand == "auth":
            cmd_auth()
        else:
            cmd_sync(args.reset, args.dry_run)
    except KeyboardInterrupt:
        print("\nFAILED: interrupted", flush=True)
        sys.exit(130)


if __name__ == "__main__":
    main()
