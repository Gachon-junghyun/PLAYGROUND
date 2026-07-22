"""뉴스 다이제스트 GUI (Tkinter, 표준 라이브러리 — 설치 불필요).

파이프라인이 '돌아가는 것'과 LLM 이 '생각하며 써 내려가는 것'을 실시간으로 본다.
  - 왼쪽 패널  : 진행 로그 (샘플링 / 스크리닝 청크 n/N / 차트 / 스테이지)
  - 오른쪽 패널: 리포트 스트리밍 (content=검정, reasoning=회색)

    python gui.py

파이프라인은 백그라운드 스레드에서 돌고, 이벤트는 Queue 로 넘어와 메인 스레드에서만
위젯을 건드린다(Tkinter 규칙). Stop 은 청크/스테이지 경계에서 협조적으로 멈춘다.
"""
from __future__ import annotations

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import scrolledtext, ttk

import digest

HERE = Path(__file__).parent


class DigestGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.q: queue.Queue = queue.Queue()
        self.stop_event = threading.Event()
        self.worker: threading.Thread | None = None
        root.title("NVIDIA 뉴스 다이제스트 — 데스크")
        root.geometry("1180x760")
        self._build()
        self.root.after(80, self._drain)

    # ── UI ───────────────────────────────────────────────────────────────
    def _build(self):
        top = ttk.Frame(self.root, padding=8)
        top.pack(fill="x")

        self.vars = {
            "window_hours": tk.StringVar(value="4"),
            "frac": tk.StringVar(value="0.35"),
            "chunk_size": tk.StringVar(value="200"),
            "important_k": tk.StringVar(value="15"),
            "chart_tickers": tk.StringVar(value="6"),
        }
        labels = {"window_hours": "윈도우(h)", "frac": "샘플비율", "chunk_size": "청크",
                  "important_k": "본문수", "chart_tickers": "차트수"}
        for key in self.vars:
            ttk.Label(top, text=labels[key]).pack(side="left", padx=(6, 2))
            ttk.Entry(top, textvariable=self.vars[key], width=6).pack(side="left")

        self.dry = tk.BooleanVar(value=False)
        ttk.Checkbutton(top, text="dry-run(크레딧0)", variable=self.dry).pack(side="left", padx=10)

        self.run_btn = ttk.Button(top, text="▶ 실행", command=self._start)
        self.run_btn.pack(side="left", padx=4)
        self.stop_btn = ttk.Button(top, text="■ 중단", command=self._stop, state="disabled")
        self.stop_btn.pack(side="left", padx=4)
        ttk.Button(top, text="📄 latest 열기", command=self._open_latest).pack(side="left", padx=4)

        self.status = ttk.Label(self.root, text="대기 중", anchor="w",
                                relief="sunken", padding=4)
        self.status.pack(fill="x", side="bottom")

        pane = ttk.PanedWindow(self.root, orient="horizontal")
        pane.pack(fill="both", expand=True, padx=8, pady=6)

        left = ttk.Frame(pane)
        ttk.Label(left, text="진행 로그 — 돌아가는 거", font=("", 10, "bold")).pack(anchor="w")
        self.log = scrolledtext.ScrolledText(left, wrap="word", width=52,
                                             font=("Consolas", 9))
        self.log.pack(fill="both", expand=True)
        self.log.tag_config("stage", foreground="#1a56db", font=("Consolas", 9, "bold"))
        self.log.tag_config("err", foreground="#c81e1e")
        pane.add(left, weight=1)

        right = ttk.Frame(pane)
        ttk.Label(right, text="리포트 / 생각 — 실시간", font=("", 10, "bold")).pack(anchor="w")
        self.out = scrolledtext.ScrolledText(right, wrap="word", font=("Malgun Gothic", 10))
        self.out.pack(fill="both", expand=True)
        self.out.tag_config("reason", foreground="#8a8a8a")
        pane.add(right, weight=2)

    # ── 실행 제어 ─────────────────────────────────────────────────────────
    def _start(self):
        if self.worker and self.worker.is_alive():
            return
        self.stop_event.clear()
        self.log.delete("1.0", "end")
        self.out.delete("1.0", "end")
        self.run_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.status.config(text="실행 중...")

        def parse(key, cast, default):
            try:
                return cast(self.vars[key].get())
            except ValueError:
                return default

        kw = dict(
            window_hours=parse("window_hours", float, 4.0),
            frac=parse("frac", float, 0.35),
            chunk_size=parse("chunk_size", int, 100),
            important_k=parse("important_k", int, 15),
            chart_tickers=parse("chart_tickers", int, 6),
            dry_run=self.dry.get(),
        )
        self.worker = threading.Thread(target=self._run, kwargs=kw, daemon=True)
        self.worker.start()

    def _run(self, **kw):
        try:
            digest.run_once(on_event=self.q.put,
                            should_stop=self.stop_event.is_set, **kw)
        except digest.StopRequested:
            pass
        except Exception as e:  # 스레드 예외를 UI 로 전달
            self.q.put({"type": "error", "msg": f"{type(e).__name__}: {e}"})
        finally:
            self.q.put({"type": "_finished"})

    def _stop(self):
        self.stop_event.set()
        self.status.config(text="중단 요청 — 현재 단계 끝나면 정지")

    def _open_latest(self):
        p = HERE / "reports" / "latest.md"
        if p.exists():
            import os
            os.startfile(p)  # Windows

    # ── 이벤트 소비(메인 스레드) ──────────────────────────────────────────
    def _drain(self):
        try:
            while True:
                ev = self.q.get_nowait()
                self._handle(ev)
        except queue.Empty:
            pass
        self.root.after(80, self._drain)

    def _handle(self, ev: dict):
        t = ev.get("type")
        if t == "stage":
            self.status.config(text=ev["stage"])
            self.log.insert("end", f"\n[{ev['stage']}] {ev.get('msg', '')}\n", "stage")
            self.log.see("end")
            # 합성 시작 순간, 첫 토큰 오기 전까지 오른쪽 패널에 대기 표시
            if ev["stage"].startswith("합성") and "dry-run" not in ev.get("msg", ""):
                self._await = True
                self.out.insert("end", "⏳ 합성 첫 토큰 대기…\n", "reason")
                self.out.see("end")
        elif t == "log":
            self.log.insert("end", f"  {ev['msg']}\n")
            self.log.see("end")
        elif t == "delta":
            if getattr(self, "_await", False):  # 첫 토큰 도착 → 대기 표시 제거
                self.out.delete("1.0", "end")
                self._await = False
            tag = "reason" if ev.get("kind") == "reason" else ""
            self.out.insert("end", ev["text"], tag)
            self.out.see("end")
        elif t == "done":
            self.status.config(text=f"완료 — 저장: {ev['msg']}")
            self.log.insert("end", f"\n[완료] {ev['msg']}\n", "stage")
            self.log.see("end")
        elif t == "error":
            self.status.config(text=f"오류: {ev['msg']}")
            self.log.insert("end", f"\n[오류] {ev['msg']}\n", "err")
            self.log.see("end")
        elif t == "_finished":
            self.run_btn.config(state="normal")
            self.stop_btn.config(state="disabled")


def main():
    root = tk.Tk()
    DigestGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
