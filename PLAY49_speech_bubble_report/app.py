# -*- coding: utf-8 -*-
"""
PLAY49 말풍선 리포트 — 데스크탑 창(window) 버전.

서버·인터넷·설치 전부 불필요. 파이썬 표준 내장 Tkinter만 쓴다.
더블클릭(또는 `python app.py`)하면 네이티브 창이 뜨고, 상단 탭으로 종목을 바꾸면
채팅처럼 [차트] + [이름 → 주장 → 근거 → 결론] 메시지가 쫘라락 스크롤된다.

데이터: 같은 폴더의 data.json (build_data.py / build_stocks.py 가 생성).
스키마: { "stocks": [ {ticker,name,unit,price,change,asof,note,series,reports}, ... ], "meta": {...} }
"""
import json, os, sys
import tkinter as tk

HERE = os.path.dirname(os.path.abspath(__file__))

NAVY = "#0b2e57"
NAVY2 = "#13427d"
PAGE = "#dbe3ec"
CARD = "#ffffff"
LINE = "#e2e8f0"
SLATE = "#64748b"
SLATE_L = "#94a3b8"
ROSE = "#e11d48"
BLUE = "#2563eb"
RED_BADGE = "#ef4444"
BLUE_BADGE = "#3b82f6"
FAM = "Malgun Gothic"


def load():
    p = os.path.join(HERE, "data.json")
    if not os.path.exists(p):
        raise SystemExit("data.json 이 없습니다. 먼저  python build_data.py  또는  build_stocks.py  를 실행하세요.")
    with open(p, encoding="utf-8") as f:
        data = json.load(f)
    if "stocks" not in data:  # 단일 subject 스키마 → stocks 래핑(하위호환)
        s = dict(data["subject"]); s["series"] = data["series"]; s["reports"] = data["reports"]
        data = {"stocks": [s], "meta": data.get("meta", {})}
    return data


def fmt_price(v, unit):
    if unit == "원":
        return "{:,}원".format(int(round(v)))
    if unit in ("달러", "USD", "$"):
        return "${:,.2f}".format(v)
    return "%s %s" % (v, unit)


def fmt_y(v, unit):
    if unit == "원":
        return "%.0fk" % (v / 1000.0)
    if unit in ("달러", "USD", "$"):
        return "$%.0f" % v
    return "%.0f" % v


class App:
    def __init__(self, root, data):
        self.root = root
        self.stocks = data["stocks"]
        self.meta = data.get("meta", {})
        self.idx = 0
        root.title("말풍선 리포트 — 애널리스트가 내 차트 옆에서 말해준다")
        root.geometry("480x840")
        root.configure(bg=PAGE)
        root.minsize(420, 600)

        self._titlebar()
        self.body = tk.Frame(root, bg=PAGE)
        self.body.pack(fill="both", expand=True)
        self.render()

    # ── 상단: 앱 제목 + 종목 탭 ──
    def _titlebar(self):
        bar = tk.Frame(self.root, bg=NAVY)
        bar.pack(fill="x")
        tk.Label(bar, text="❝ 말풍선 리포트", bg=NAVY, fg="white",
                 font=(FAM, 12, "bold")).pack(anchor="w", padx=14, pady=(8, 0))
        tk.Label(bar, text="애널리스트가 차트 옆에서 말해준다 · AI 에이전트가 정리",
                 bg=NAVY, fg="#cbd5e1", font=(FAM, 8)).pack(anchor="w", padx=14)
        tabs = tk.Frame(bar, bg=NAVY)
        tabs.pack(anchor="w", padx=12, pady=8)
        self.tab_btns = []
        for i, s in enumerate(self.stocks):
            b = tk.Label(tabs, text="  %s  " % s["name"], font=(FAM, 10, "bold"),
                         padx=4, pady=3, cursor="hand2")
            b.pack(side="left", padx=(0, 6))
            b.bind("<Button-1>", lambda e, i=i: self.select(i))
            self.tab_btns.append(b)
        self._paint_tabs()

    def _paint_tabs(self):
        for i, b in enumerate(self.tab_btns):
            if i == self.idx:
                b.configure(bg="white", fg=NAVY)
            else:
                b.configure(bg=NAVY2, fg="#cbd5e1")

    def select(self, i):
        if i == self.idx:
            return
        self.idx = i
        self._paint_tabs()
        self.render()

    # ── 선택 종목 렌더 (가격헤더 + 차트 + 피드) ──
    def render(self):
        for w in self.body.winfo_children():
            w.destroy()
        self.bubble_widgets = {}
        s = self.stocks[self.idx]
        self._subheader(s)
        self._chart(s)
        self._feed(s)

    def _subheader(self, s):
        h = tk.Frame(self.body, bg=CARD)
        h.pack(fill="x")
        left = tk.Frame(h, bg=CARD); left.pack(side="left", padx=14, pady=8)
        tk.Label(left, text=s["name"], bg=CARD, fg=NAVY,
                 font=(FAM, 13, "bold")).pack(anchor="w")
        tk.Label(left, text="%s · %s" % (s.get("ticker", ""), s.get("note", "")),
                 bg=CARD, fg=SLATE_L, font=(FAM, 8), wraplength=250,
                 justify="left").pack(anchor="w")
        right = tk.Frame(h, bg=CARD); right.pack(side="right", padx=14)
        up = s.get("change", 0) >= 0
        tk.Label(right, text=fmt_price(s["price"], s.get("unit", "")), bg=CARD, fg=NAVY,
                 font=(FAM, 14, "bold")).pack(anchor="e")
        tk.Label(right, text="%s %+.2f%%" % ("▲" if up else "▼", s.get("change", 0)),
                 bg=CARD, fg=ROSE if up else BLUE, font=(FAM, 9, "bold")).pack(anchor="e")

    def _chart(self, s):
        wrap = tk.Frame(self.body, bg=PAGE)
        wrap.pack(fill="x", padx=10, pady=(8, 4))
        tk.Label(wrap, text="번호 핀 = 리포트 발행일 (클릭하면 해당 글로 이동) · %s" % s.get("unit", ""),
                 bg=PAGE, fg=SLATE_L, font=(FAM, 8)).pack(anchor="w", padx=4, pady=(0, 2))
        W, H = 458, 188
        unit = s.get("unit", "")
        c = tk.Canvas(wrap, width=W, height=H, bg=CARD, highlightthickness=1,
                      highlightbackground=LINE)
        c.pack()
        series = s["series"]
        vals = [p["value"] for p in series]
        span = (max(vals) - min(vals)) or 1
        lo, hi = min(vals) - span * 0.15, max(vals) + span * 0.15
        padL, padR, padT, padB = 42, 14, 38, 22
        pw, ph = W - padL - padR, H - padT - padB
        n = len(series)
        X = lambda i: padL + (0 if n <= 1 else pw * i / (n - 1))
        Y = lambda v: padT + ph * (1 - (v - lo) / (hi - lo))
        for t in (0, 0.5, 1):
            yy = padT + ph * t
            c.create_line(padL, yy, W - padR, yy, fill=LINE)
            c.create_text(padL - 6, yy, text=fmt_y(hi - (hi - lo) * t, unit),
                          anchor="e", fill=SLATE_L, font=(FAM, 7))
        step = max(1, n // 6)
        for i, p in enumerate(series):
            if i % step == 0 or i == n - 1:
                c.create_text(X(i), H - 8, text=p["date"][5:], fill=SLATE_L, font=(FAM, 7))
        pts = []
        for i, p in enumerate(series):
            pts += [X(i), Y(p["value"])]
        if len(pts) >= 4:
            c.create_line(*pts, fill=NAVY2, width=2)

        idx = {p["date"]: i for i, p in enumerate(series)}
        for num, r in enumerate(s["reports"], 1):  # 핀 번호 = 피드 메시지 번호
            d = r.get("pinDate", r["date"])         # 발행일을 거래일에 스냅
            if d not in idx:
                continue
            i = idx[d]
            px, py = X(i), Y(series[i]["value"])
            by = max(py - 32, 12)
            tag = "mk_%s" % num
            c.create_line(px, by + 8, px, py, fill=SLATE_L, dash=(2, 2))
            c.create_oval(px - 4, py - 4, px + 4, py + 4, fill="white", outline=NAVY2, width=2)
            c.create_rectangle(px - 9, by - 11, px + 9, by + 8, fill=NAVY, outline="", tags=tag)
            c.create_polygon(px - 4, by + 8, px + 4, by + 8, px, by + 13, fill=NAVY, tags=tag)
            c.create_text(px, by - 1, text=str(num), fill="white", font=(FAM, 9, "bold"), tags=tag)
            col = RED_BADGE if r.get("newsImpact", 0) >= 0 else BLUE_BADGE
            c.create_rectangle(px + 12, by - 11, px + 33, by + 3, fill=col, outline="")
            c.create_text(px + 22, by - 4, text="%+d" % r.get("newsImpact", 0), fill="white",
                          font=(FAM, 7, "bold"))
            c.tag_bind(tag, "<Button-1>", lambda e, rid=r["id"]: self._scroll_to(rid))

    def _feed(self, s):
        outer = tk.Frame(self.body, bg=PAGE)
        outer.pack(fill="both", expand=True, padx=10, pady=(2, 10))
        self.canvas = tk.Canvas(outer, bg=PAGE, highlightthickness=0)
        sb = tk.Scrollbar(outer, orient="vertical", command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg=PAGE)
        self.win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=sb.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.inner.bind("<Configure>",
                        lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>",
                         lambda e: self.canvas.itemconfig(self.win, width=e.width))
        self.canvas.bind_all("<MouseWheel>",
                             lambda e: self.canvas.yview_scroll(int(-e.delta / 120), "units"))
        tk.Label(self.inner, text="— 발행순 애널리스트 메시지 %d건 —" % len(s["reports"]),
                 bg=PAGE, fg=SLATE_L, font=(FAM, 8)).pack(pady=(2, 2))
        for k, r in enumerate(s["reports"], 1):
            self._bubble(self.inner, r, k, s.get("unit", "원"))
        self._agent_note(self.inner)

    def _chip(self, parent, text, fg, bg):
        return tk.Label(parent, text=text, fg=fg, bg=bg, font=(FAM, 8, "bold"),
                        padx=5, pady=1)

    def _bubble(self, parent, r, num, unit="원"):
        row = tk.Frame(parent, bg=PAGE)
        row.pack(fill="x", padx=2, pady=5)
        tk.Label(row, text="증", bg=NAVY, fg="white", font=(FAM, 11, "bold"),
                 width=2, height=1).pack(side="left", anchor="n", padx=(2, 6))
        card = tk.Frame(row, bg=CARD, highlightthickness=1, highlightbackground=LINE)
        card.pack(side="left", fill="x", expand=True)
        self.bubble_widgets[r["id"]] = row
        pad = tk.Frame(card, bg=CARD); pad.pack(fill="x", padx=10, pady=8)

        head = tk.Frame(pad, bg=CARD); head.pack(fill="x")
        tk.Label(head, text=r["firm"], bg=CARD, fg=NAVY, font=(FAM, 10, "bold")).pack(side="left")
        tk.Label(head, text="  " + r["date"].replace("-", ".") + " · " + r.get("source", ""),
                 bg=CARD, fg=SLATE_L, font=(FAM, 8)).pack(side="left")
        tone = ROSE if r.get("tone") == "up" else (BLUE if r.get("tone") == "down" else SLATE)
        arrow = "▲" if r.get("tone") == "up" else ("▼" if r.get("tone") == "down" else "■")
        self._chip(head, "%s %s" % (r["opinion"], arrow), tone, "#f1f5f9").pack(side="left", padx=4)
        pos = r.get("newsImpact", 0) >= 0
        self._chip(head, "%s%d" % ("+" if pos else "", r.get("newsImpact", 0)),
                   "white", RED_BADGE if pos else BLUE_BADGE).pack(side="left")

        tline = tk.Frame(pad, bg=CARD); tline.pack(fill="x", pady=(2, 6))
        tk.Label(tline, text=r.get("title", ""), bg=CARD, fg=SLATE_L, font=(FAM, 8),
                 anchor="w", justify="left", wraplength=250).pack(side="left")
        if r.get("targetPrice"):
            self._chip(tline, "목표가 " + fmt_price(r["targetPrice"], unit),
                       NAVY, "#e2e8f0").pack(side="right")

        self._section(pad, "주장", "white", NAVY, r.get("claim", ""), bold=True)
        ev = tk.Frame(pad, bg=CARD); ev.pack(fill="x", pady=(2, 0))
        self._chip(ev, "근거", "#1d4ed8", "#dbeafe").pack(side="left", anchor="n")
        evbody = tk.Frame(ev, bg=CARD); evbody.pack(side="left", fill="x", expand=True, padx=(6, 0))
        for e in r.get("evidence", []):
            line = tk.Frame(evbody, bg=CARD); line.pack(fill="x", anchor="w")
            tk.Label(line, text=e.get("label", ""), bg=CARD, fg=SLATE_L,
                     font=(FAM, 8, "bold"), width=4, anchor="w").pack(side="left", anchor="n")
            tk.Label(line, text=e.get("text", ""), bg=CARD, fg="#475569", font=(FAM, 9),
                     justify="left", wraplength=265, anchor="w").pack(side="left", fill="x")
        self._section(pad, "결론", "#9f1239", "#ffe4e6", "▸ " + r.get("conclusion", ""),
                      fg_text=NAVY, bold=True, top=4)

        who = "AI 에이전트가 정리" if r.get("curated", True) else "자동추출 초안"
        tk.Label(pad, text="%s · 출처 %s" % (who, r.get("source", "")),
                 bg=CARD, fg="#cbd5e1", font=(FAM, 7)).pack(anchor="e", pady=(4, 0))

    def _section(self, parent, tag, tag_fg, tag_bg, text, fg_text="#1f2937",
                 bold=False, top=2):
        f = tk.Frame(parent, bg=CARD); f.pack(fill="x", pady=(top, 0))
        self._chip(f, tag, tag_fg, tag_bg).pack(side="left", anchor="n")
        tk.Label(f, text=text, bg=CARD, fg=fg_text,
                 font=(FAM, 10, "bold" if bold else "normal"),
                 justify="left", wraplength=295, anchor="w").pack(side="left", fill="x", padx=(6, 0))

    def _agent_note(self, parent):
        box = tk.Frame(parent, bg=NAVY); box.pack(fill="x", padx=2, pady=(6, 4))
        inner = tk.Frame(box, bg=NAVY); inner.pack(fill="x", padx=12, pady=8)
        tk.Label(inner, text="◆ AI 에이전트", bg=NAVY, fg="white",
                 font=(FAM, 9, "bold")).pack(anchor="w")
        tk.Label(inner, text="리포트는 AI 에이전트(클로드 코드 루틴)가 수집·증류해 주장/근거/결론으로 "
                 "정리한다. 실시간 LLM API 호출 없이 창 안에서 굴러간다.\n로드맵: 손절가 도달 시 관련 리포트 자동 푸시.",
                 bg=NAVY, fg="#cbd5e1", font=(FAM, 8), justify="left",
                 wraplength=380).pack(anchor="w")
        if self.meta:
            tk.Label(inner, text="%s 생성 · 출처 %s" % (self.meta.get("generated_at", ""),
                     self.meta.get("source", "")), bg=NAVY, fg="#64748b",
                     font=(FAM, 7)).pack(anchor="w", pady=(2, 0))

    def _scroll_to(self, rid):
        w = self.bubble_widgets.get(rid)
        if not w:
            return
        self.root.update_idletasks()
        total = max(1, self.inner.winfo_height())
        self.canvas.yview_moveto(max(0.0, w.winfo_y() / total))


def main():
    data = load()
    root = tk.Tk()
    app = App(root, data)
    if "--selftest" in sys.argv:
        root.update_idletasks(); root.update()
        if len(app.stocks) > 1:
            app.select(1); root.update()
        root.destroy()
        print("[selftest ok] stocks=%d" % len(app.stocks))
        return
    root.mainloop()


if __name__ == "__main__":
    main()
