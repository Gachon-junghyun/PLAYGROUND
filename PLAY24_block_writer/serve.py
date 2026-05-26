"""Block Writer local server. Stdlib only — no Flask, no pip install.

Run:
    python serve.py
Then a browser opens at http://127.0.0.1:8765/
"""
from __future__ import annotations
import http.server
import json
import socketserver
import sys
import threading
import urllib.parse
import webbrowser
from pathlib import Path

import db

HERE = Path(__file__).parent
PORT = 8765

_MIME = {
    ".html": "text/html; charset=utf-8",
    ".js":   "application/javascript; charset=utf-8",
    ".css":  "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg":  "image/svg+xml",
    ".png":  "image/png",
    ".ico":  "image/x-icon",
}


class Handler(http.server.BaseHTTPRequestHandler):

    # ---------- routing ----------

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        path = url.path
        qs = urllib.parse.parse_qs(url.query)
        if path in ("/", "/index.html"):
            return self._send_file("index.html")
        if path == "/api/documents":
            return self._send_json({
                "documents": db.list_documents(),
                "currentId": db.get_current_doc_id(),
            })
        if path == "/api/state":
            doc_id = (qs.get("doc") or [None])[0]
            try:
                return self._send_json(db.get_state(doc_id))
            except ValueError as e:
                return self._send_json({"error": str(e)}, status=404)
        if path == "/api/export":
            doc_id = (qs.get("doc") or [None])[0]
            try:
                state = db.get_state(doc_id)
            except ValueError as e:
                return self._send_json({"error": str(e)}, status=404)
            body = json.dumps(state, ensure_ascii=False, indent=2).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header(
                "Content-Disposition",
                f'attachment; filename="block-writer.json"',
            )
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        # Fall through: try to serve as static file under this dir
        fp = (HERE / path.lstrip("/")).resolve()
        try:
            fp.relative_to(HERE.resolve())  # prevent path traversal
        except ValueError:
            return self.send_error(403)
        if fp.is_file():
            return self._send_file(fp.name, fp=fp)
        return self.send_error(404)

    def do_PUT(self):
        url = urllib.parse.urlparse(self.path)
        path = url.path
        qs = urllib.parse.parse_qs(url.query)
        if path == "/api/state":
            doc_id = (qs.get("doc") or [None])[0]
            try:
                payload = self._read_json()
                db.set_state(payload, doc_id=doc_id)
                return self._send_json({"ok": True})
            except Exception as e:
                return self._send_json({"error": str(e)}, status=400)
        # Match /api/documents/:id (rename)
        if path.startswith("/api/documents/"):
            doc_id = path[len("/api/documents/"):]
            try:
                payload = self._read_json()
                title = payload.get("title", "")
                ok = db.rename_document(doc_id, title)
                if not ok:
                    return self._send_json({"error": "no such document"}, status=404)
                return self._send_json({"ok": True})
            except Exception as e:
                return self._send_json({"error": str(e)}, status=400)
        if path == "/api/current":
            try:
                payload = self._read_json()
                doc_id = payload.get("id")
                if not doc_id:
                    return self._send_json({"error": "missing id"}, status=400)
                ok = db.set_current_doc(doc_id)
                if not ok:
                    return self._send_json({"error": "no such document"}, status=404)
                return self._send_json({"ok": True, "currentId": doc_id})
            except Exception as e:
                return self._send_json({"error": str(e)}, status=400)
        return self.send_error(404)

    def do_POST(self):
        url = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(url.query)
        if url.path == "/api/documents":
            try:
                payload = self._read_json()
                title = (payload or {}).get("title", "") or ""
                new_id = db.create_document(title)
                return self._send_json({"id": new_id, "title": title})
            except Exception as e:
                return self._send_json({"error": str(e)}, status=400)
        if url.path == "/api/import":
            mode = (qs.get("mode") or ["replace"])[0]
            doc_id = (qs.get("doc") or [None])[0]
            new_doc = (qs.get("new_doc") or [None])[0]  # "1" = create a fresh doc for the import
            try:
                payload = self._read_json()
                if new_doc:
                    inc_title = (payload or {}).get("title", "") or ""
                    doc_id = db.create_document(inc_title)
                    db.set_current_doc(doc_id)
                if mode == "merge":
                    db.merge_state(payload, doc_id=doc_id)
                else:
                    db.set_state(payload, doc_id=doc_id)
                state = db.get_state(doc_id)
                return self._send_json({**state, "documentId": doc_id or db.get_current_doc_id()})
            except Exception as e:
                return self._send_json({"error": str(e)}, status=400)
        return self.send_error(404)

    def do_DELETE(self):
        url = urllib.parse.urlparse(self.path)
        if url.path.startswith("/api/documents/"):
            doc_id = url.path[len("/api/documents/"):]
            try:
                ok = db.delete_document(doc_id)
                if not ok:
                    return self._send_json({"error": "no such document"}, status=404)
                return self._send_json({"ok": True, "currentId": db.get_current_doc_id()})
            except Exception as e:
                return self._send_json({"error": str(e)}, status=400)
        return self.send_error(404)

    # ---------- helpers ----------

    def _read_json(self):
        ln = int(self.headers.get("Content-Length", "0") or "0")
        if ln <= 0:
            return {}
        raw = self.rfile.read(ln)
        return json.loads(raw.decode("utf-8"))

    def _send_json(self, obj, status: int = 200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, name: str, fp: Path | None = None):
        fp = fp or (HERE / name)
        try:
            data = fp.read_bytes()
        except FileNotFoundError:
            return self.send_error(404)
        ext = fp.suffix.lower()
        mime = _MIME.get(ext, "application/octet-stream")
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        sys.stderr.write("[server] " + (fmt % args) + "\n")


class _Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def main():
    db.init()
    addr = ("127.0.0.1", PORT)
    httpd = _Server(addr, Handler)
    url = f"http://{addr[0]}:{addr[1]}/"
    print(f"Block Writer @ {url}   (Ctrl+C to stop)")
    if "--no-browser" not in sys.argv:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nbye.")
        httpd.shutdown()


if __name__ == "__main__":
    main()
