"""CLI to manage the block-writer SQLite DB (multi-document).

This is the operational surface for Claude (or the user) to read/write
content without going through the browser.

Examples (글 단위):
    python manage.py list-docs                                # list all writing pieces
    python manage.py add-doc --title "투자 리포트"             # create a new doc
    python manage.py rename-doc <id> --title "..."
    python manage.py switch-doc <id>                          # set current
    python manage.py delete-doc <id>

Examples (state per doc — defaults to current):
    python manage.py state [--doc <id>]
    python manage.py export --out backup.json [--doc <id>]
    python manage.py import incoming.json [--doc <id>] [--new-doc]    # REPLACE
    python manage.py merge inbox.json     [--doc <id>] [--new-doc]    # APPEND remap
    python manage.py search "키워드" [--doc <id> | --all]
    python manage.py list-blocks [--doc <id>]
    python manage.py add-guideline    --title "..." [--doc <id>]
    python manage.py add-proposition  --title "..." [--parent <id>] [--doc <id>]
    python manage.py update-block <id> --title "..."
    python manage.py delete-block <id>
    python manage.py clear --yes [--doc <id>]                 # wipe ONE doc (not all)
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

# Force UTF-8 stdout/stderr so Korean (and em-dashes) don't crash on Windows cp949 consoles.
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

import db


def _print_state(state):
    print(json.dumps(state, indent=2, ensure_ascii=False))


def _doc_id(args) -> str | None:
    return getattr(args, "doc", None)


# ---------- doc-level ----------
def cmd_list_docs(args):
    docs = db.list_documents()
    cur = db.get_current_doc_id()
    if not docs:
        print("(no documents)")
        return
    for d in docs:
        mark = "*" if d["id"] == cur else " "
        title = (d["title"] or "(untitled)")[:60]
        print(f"{mark} {d['id']}  {title}")


def cmd_add_doc(args):
    did = db.create_document(args.title or "")
    if args.switch:
        db.set_current_doc(did)
    print(did)


def cmd_rename_doc(args):
    ok = db.rename_document(args.id, args.title)
    print("ok" if ok else "no such doc", file=sys.stderr)
    sys.exit(0 if ok else 1)


def cmd_switch_doc(args):
    ok = db.set_current_doc(args.id)
    print("ok" if ok else "no such doc", file=sys.stderr)
    sys.exit(0 if ok else 1)


def cmd_delete_doc(args):
    if not args.yes:
        ans = input(f"Delete doc {args.id} and all its blocks? [y/N] ").strip().lower()
        if ans != "y":
            print("aborted", file=sys.stderr)
            return
    ok = db.delete_document(args.id)
    print("deleted" if ok else "no such doc", file=sys.stderr)
    sys.exit(0 if ok else 1)


# ---------- state per doc ----------
def cmd_state(args):
    _print_state(db.get_state(_doc_id(args)))


def cmd_export(args):
    state = db.get_state(_doc_id(args))
    blob = json.dumps(state, indent=2, ensure_ascii=False)
    if args.out:
        Path(args.out).write_text(blob, encoding="utf-8")
        print(f"-> {args.out}", file=sys.stderr)
    else:
        print(blob)


def _load_json_arg(path: str):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def cmd_import(args):
    data = _load_json_arg(args.file)
    if args.new_doc:
        did = db.create_document(data.get("title", "") or "")
        db.set_current_doc(did)
        db.set_state(data, doc_id=did)
        print(f"new doc {did} created and replaced from {args.file}", file=sys.stderr)
        print(did)
    else:
        db.set_state(data, doc_id=_doc_id(args))
        print(f"replaced state from {args.file}", file=sys.stderr)


def cmd_merge(args):
    data = _load_json_arg(args.file)
    if args.new_doc:
        did = db.create_document(data.get("title", "") or "")
        db.set_current_doc(did)
        db.merge_state(data, doc_id=did)
        print(f"new doc {did} created and merged from {args.file}", file=sys.stderr)
        print(did)
    else:
        db.merge_state(data, doc_id=_doc_id(args))
        print(f"merged state from {args.file}", file=sys.stderr)


def cmd_search(args):
    hits = db.search_blocks(args.query, doc_id=None if args.all else _doc_id(args))
    if not hits:
        print("(no matches)")
        return
    for b in hits:
        tag = "[GDL]" if b["type"] == "guideline" else "[PRP]"
        parent = f"  ↳in {b['parentId'][:6]}…" if b.get("parentId") else ""
        doc_tag = f"  [{b.get('documentId', '')[:6]}…]" if args.all else ""
        title = b["title"] or "(no title)"
        print(f"{tag} {b['id']}{doc_tag}  {title}{parent}")
        body = (b["body"] or "").replace("\n", " ").strip()
        if body:
            preview = body[:140] + ("…" if len(body) > 140 else "")
            print(f"        {preview}")


def cmd_list_blocks(args):
    state = db.get_state(_doc_id(args))
    if not state["blocks"]:
        print("(empty)")
        return
    for b in state["blocks"]:
        tag = "[GDL]" if b["type"] == "guideline" else "[PRP]"
        parent = f"  ↳in {b['parentId'][:6]}…" if b.get("parentId") else ""
        title = (b["title"] or "(no title)")[:60]
        print(f"{tag} {b['id']}  {title}{parent}")


def cmd_add_guideline(args):
    bid = db.add_block(
        type="guideline",
        title=args.title or "",
        body=args.body or "",
        role=args.role,
        source=args.source,
        note=args.note,
        doc_id=_doc_id(args),
    )
    print(bid)


def cmd_add_proposition(args):
    bid = db.add_block(
        type="proposition",
        title=args.title or "",
        body=args.body or "",
        parent_id=args.parent,
        role=args.role,
        source=args.source,
        note=args.note,
        doc_id=_doc_id(args),
    )
    print(bid)


def cmd_update_block(args):
    fields = {}
    if args.title is not None:
        fields["title"] = args.title
    if args.body is not None:
        fields["body"] = args.body
    if args.parent is not None:
        fields["parent_id"] = args.parent or None
    if args.role is not None:
        fields["role"] = args.role or None
    if args.source is not None:
        fields["source"] = args.source or None
    if args.note is not None:
        fields["note"] = args.note or None
    if not fields:
        print("nothing to update (pass --title/--body/--parent/--role/--source/--note)", file=sys.stderr)
        sys.exit(2)
    ok = db.update_block(args.id, **fields)
    print("ok" if ok else "no such block", file=sys.stderr)
    sys.exit(0 if ok else 1)


def cmd_delete_block(args):
    ok = db.delete_block(args.id)
    print("deleted" if ok else "no such block", file=sys.stderr)
    sys.exit(0 if ok else 1)


def cmd_clear(args):
    if not args.yes:
        ans = input("Really clear this document's data? [y/N] ").strip().lower()
        if ans != "y":
            print("aborted", file=sys.stderr)
            return
    db.set_state({"title": "", "blocks": [], "doc": []}, doc_id=_doc_id(args))
    print("cleared", file=sys.stderr)


def _add_doc_opt(p):
    p.add_argument("--doc", help="target document id (default: current)")
    return p


def build_parser():
    p = argparse.ArgumentParser(description="block-writer DB management CLI (multi-document)")
    sub = p.add_subparsers(dest="cmd", required=True)

    # doc-level
    sub.add_parser("list-docs", help="list all documents (* = current)").set_defaults(func=cmd_list_docs)

    ad = sub.add_parser("add-doc", help="create a new document (prints id)")
    ad.add_argument("--title", default="")
    ad.add_argument("--switch", action="store_true", help="also switch current to the new doc")
    ad.set_defaults(func=cmd_add_doc)

    rn = sub.add_parser("rename-doc", help="rename a document")
    rn.add_argument("id")
    rn.add_argument("--title", required=True)
    rn.set_defaults(func=cmd_rename_doc)

    sw = sub.add_parser("switch-doc", help="set the current document")
    sw.add_argument("id")
    sw.set_defaults(func=cmd_switch_doc)

    dd = sub.add_parser("delete-doc", help="delete a document and all its blocks")
    dd.add_argument("id")
    dd.add_argument("--yes", action="store_true")
    dd.set_defaults(func=cmd_delete_doc)

    # per-doc state
    _add_doc_opt(sub.add_parser("state", help="dump state JSON for a doc")).set_defaults(func=cmd_state)

    ex = _add_doc_opt(sub.add_parser("export", help="export state JSON for a doc"))
    ex.add_argument("--out", help="output file (default: stdout)")
    ex.set_defaults(func=cmd_export)

    im = _add_doc_opt(sub.add_parser("import", help="REPLACE state from JSON"))
    im.add_argument("file")
    im.add_argument("--new-doc", action="store_true", help="create a fresh doc using the file's title")
    im.set_defaults(func=cmd_import)

    mg = _add_doc_opt(sub.add_parser("merge", help="APPEND state from JSON (id remap)"))
    mg.add_argument("file")
    mg.add_argument("--new-doc", action="store_true", help="create a fresh doc using the file's title")
    mg.set_defaults(func=cmd_merge)

    sr = _add_doc_opt(sub.add_parser("search", help="substring search across block title/body"))
    sr.add_argument("query")
    sr.add_argument("--all", action="store_true", help="search across all documents")
    sr.set_defaults(func=cmd_search)

    _add_doc_opt(sub.add_parser("list-blocks", help="list scratch blocks for a doc")).set_defaults(func=cmd_list_blocks)

    ag = _add_doc_opt(sub.add_parser("add-guideline", help="create a new guideline block"))
    ag.add_argument("--title", default="")
    ag.add_argument("--body", default="")
    ag.add_argument("--role", help="claim/evidence/counter/definition/example/quote/implication/emotion/question/hypothesis")
    ag.add_argument("--source", help="1차 출처 (URL, 인용, 사건명)")
    ag.add_argument("--note", help="자기 메모 (캔버스에 안 보임)")
    ag.set_defaults(func=cmd_add_guideline)

    ap = _add_doc_opt(sub.add_parser("add-proposition", help="create a new proposition block"))
    ap.add_argument("--title", default="")
    ap.add_argument("--body", default="")
    ap.add_argument("--parent", help="guideline id to nest under")
    ap.add_argument("--role")
    ap.add_argument("--source")
    ap.add_argument("--note")
    ap.set_defaults(func=cmd_add_proposition)

    ub = sub.add_parser("update-block", help="update fields of a block (cross-doc)")
    ub.add_argument("id")
    ub.add_argument("--title")
    ub.add_argument("--body")
    ub.add_argument("--parent", help="set parent guideline id (empty string to unset)")
    ub.add_argument("--role", help="set role (empty string to unset)")
    ub.add_argument("--source", help="set source (empty string to unset)")
    ub.add_argument("--note", help="set note (empty string to unset)")
    ub.set_defaults(func=cmd_update_block)

    db_ = sub.add_parser("delete-block", help="delete a block by id (cross-doc)")
    db_.add_argument("id")
    db_.set_defaults(func=cmd_delete_block)

    cl = _add_doc_opt(sub.add_parser("clear", help="wipe one document's data (not the doc itself)"))
    cl.add_argument("--yes", action="store_true")
    cl.set_defaults(func=cmd_clear)

    return p


def main():
    db.init()
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
