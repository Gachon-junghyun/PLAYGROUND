# PLAY46_song_snippet_quiz/game.py
"""음악 1초 듣고 맞추기 (Heardle 스타일) — tkinter + pygame.

규칙:
  - 곡 순서는 매판 무작위 셔플.
  - SPACE 는 *같은 구간*을 다시 들려준다 (시작점·길이 그대로). 처음엔 1초.
  - 듣는 시간은 고정이지만 [− 시간]/[+ 시간] 버튼(또는 ↑/↓ 키)으로 직접 바꾼다.
    1 → 1.5 → 2.5 → 4 → 6 → 9초. 길게 들을수록 쉽지만 점수는 낮아진다.
  - [🔀 랜덤 섞기] 버튼(또는 R 키)을 누르면 같은 곡의 *다른 부분*이 나온다.
  - 4지선다 보기를 클릭하면 정답 판정. 적게 들을수록 고득점.
    맞히면 초록, 틀리면 빨강 + 정답 표시 후 다음 곡으로.

실행: python game.py   (먼저 download.py 로 곡을 받아둬야 함)
"""
from __future__ import annotations

import json
import os
import random
import sys
import tkinter as tk
from pathlib import Path

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame

HERE = Path(__file__).resolve().parent
PLAYLIST = HERE / "playlist.json"
CLIPS = HERE / "clips"

# 듣는 시간(초) 단계. [− 시간]/[+ 시간] 으로 이 안에서 이동.
LISTEN_STEPS = [1.0, 1.5, 2.5, 4.0, 6.0, 9.0]
MAX_LISTEN = max(LISTEN_STEPS)
N_CHOICES = 4


def load_playlist() -> list[dict]:
    if not PLAYLIST.exists():
        sys.exit("playlist.json 이 없다. 먼저 `python download.py` 실행.")
    rows = json.loads(PLAYLIST.read_text(encoding="utf-8"))
    rows = [r for r in rows if (CLIPS / r["file"]).exists() and r.get("duration", 0) > 0]
    if len(rows) < 2:
        sys.exit("재생 가능한 곡이 2곡 미만이다. download.py 로 곡을 더 받아라.")
    return rows


class Quiz:
    def __init__(self, root: tk.Tk, songs: list[dict]):
        self.root = root
        self.songs = songs
        self.order: list[int] = []
        self.pos = -1
        self.cur: dict = {}
        self.step = 0            # LISTEN_STEPS 인덱스 (듣는 시간)
        self.offset = 0.0        # 현재 곡에서 들려줄 시작 지점(초) — 곡당 고정
        self.answered = False
        self.score = 0
        self.streak = 0
        self.played = 0          # 진행한 곡 수
        self._stop_job = None

        pygame.mixer.init()
        self._build_ui()
        self.root.bind("<space>", lambda e: self.play_snippet())
        self.root.bind("<Up>", lambda e: self.change_duration(+1))
        self.root.bind("<Down>", lambda e: self.change_duration(-1))
        self.root.bind("r", lambda e: self.reshuffle())
        self.root.bind("R", lambda e: self.reshuffle())
        self.root.bind("<Return>", lambda e: self.answered and self.next_song())
        self.next_song()

    # ─── UI ───────────────────────────────────────────
    def _build_ui(self) -> None:
        self.root.title("🎵 1초 노래 맞추기")
        self.root.configure(bg="#101018")
        self.root.geometry("600x680")

        self.lbl_score = tk.Label(self.root, text="", font=("Segoe UI", 12),
                                  fg="#9aa0b5", bg="#101018")
        self.lbl_score.pack(pady=(14, 2))

        self.lbl_status = tk.Label(self.root, text="", font=("Segoe UI", 16, "bold"),
                                   fg="#ffffff", bg="#101018")
        self.lbl_status.pack(pady=(6, 2))

        self.lbl_listen = tk.Label(self.root, text="", font=("Segoe UI", 40, "bold"),
                                   fg="#5ad1ff", bg="#101018")
        self.lbl_listen.pack(pady=(4, 2))

        # 듣는 시간 조절 + 랜덤 섞기
        ctrl = tk.Frame(self.root, bg="#101018")
        ctrl.pack(pady=(2, 4))
        tk.Button(ctrl, text="− 시간", font=("Segoe UI", 11, "bold"),
                  bg="#3a3a52", fg="white", activebackground="#4a4a66", relief="flat",
                  padx=12, pady=6, command=lambda: self.change_duration(-1)).pack(side="left", padx=4)
        tk.Button(ctrl, text="+ 시간", font=("Segoe UI", 11, "bold"),
                  bg="#3a3a52", fg="white", activebackground="#4a4a66", relief="flat",
                  padx=12, pady=6, command=lambda: self.change_duration(+1)).pack(side="left", padx=4)
        tk.Button(ctrl, text="🔀 랜덤 섞기", font=("Segoe UI", 11, "bold"),
                  bg="#7a4ddd", fg="white", activebackground="#6a3dcc", relief="flat",
                  padx=12, pady=6, command=self.reshuffle).pack(side="left", padx=12)

        self.btn_play = tk.Button(self.root, text="▶  SPACE 로 듣기", font=("Segoe UI", 14, "bold"),
                                  bg="#2b6cff", fg="white", activebackground="#1e54cc",
                                  relief="flat", padx=18, pady=10, command=self.play_snippet)
        self.btn_play.pack(pady=8)

        self.choice_frame = tk.Frame(self.root, bg="#101018")
        self.choice_frame.pack(pady=10, fill="x", padx=40)
        self.choice_btns: list[tk.Button] = []
        for i in range(N_CHOICES):
            b = tk.Button(self.choice_frame, text="", font=("Segoe UI", 12),
                          bg="#1c1c2b", fg="#e6e6f0", activebackground="#2a2a40",
                          relief="flat", pady=10, wraplength=440, justify="center",
                          command=lambda idx=i: self.guess(idx))
            b.pack(fill="x", pady=4)
            self.choice_btns.append(b)

        self.btn_next = tk.Button(self.root, text="다음 곡 →", font=("Segoe UI", 12, "bold"),
                                  bg="#3a3a52", fg="white", activebackground="#4a4a66",
                                  relief="flat", padx=14, pady=8, command=self.next_song)

    # ─── 라운드 진행 ──────────────────────────────────
    def next_song(self) -> None:
        self.btn_next.pack_forget()
        if not self.order:
            self.order = list(range(len(self.songs)))
            random.shuffle(self.order)
        self.pos += 1
        if self.pos >= len(self.order):  # 한 바퀴 다 돌면 다시 셔플
            self.order = list(range(len(self.songs)))
            random.shuffle(self.order)
            self.pos = 0
        self.cur = self.songs[self.order[self.pos]]
        self.step = 0
        self.answered = False
        self.played += 1
        self.offset = self._random_offset()  # 곡당 한 번 정해 고정

        # 보기: 정답 + 무작위 오답 3개
        others = [s for s in self.songs if s["file"] != self.cur["file"]]
        decoys = random.sample(others, min(N_CHOICES - 1, len(others)))
        self.options = decoys + [self.cur]
        random.shuffle(self.options)

        for b, opt in zip(self.choice_btns, self.options):
            b.config(text=self._label(opt), state="normal",
                     bg="#1c1c2b", fg="#e6e6f0")
        self.lbl_status.config(text="이 곡은?", fg="#ffffff")
        self.play_snippet()

    def _random_offset(self) -> float:
        """곡 안에서 최대 길이(MAX_LISTEN)를 재생해도 안 넘치는 랜덤 시작점."""
        dur = float(self.cur.get("duration", 0))
        hi = max(0.0, dur - MAX_LISTEN)
        return random.uniform(0, hi) if hi > 0 else 0.0

    @staticmethod
    def _label(s: dict) -> str:
        return f"{s['title']}" + (f"  —  {s['artist']}" if s.get("artist") else "")

    def _refresh_meta(self) -> None:
        self.lbl_score.config(
            text=f"점수 {self.score}    연속 {self.streak}    {self.played}곡째")
        sec = LISTEN_STEPS[self.step]
        self.lbl_listen.config(text=f"{sec:g}초")

    # ─── 듣는 시간 조절 / 구간 섞기 ───────────────────
    def change_duration(self, delta: int) -> None:
        if self.answered:
            return
        new = min(len(LISTEN_STEPS) - 1, max(0, self.step + delta))
        if new == self.step:
            return
        self.step = new
        self.play_snippet()

    def reshuffle(self) -> None:
        """같은 곡, 다른 부분."""
        if self.answered:
            return
        self.offset = self._random_offset()
        self.play_snippet()

    # ─── 재생 (항상 현재 offset + 현재 길이) ──────────
    def play_snippet(self) -> None:
        if self.answered:
            return
        listen = LISTEN_STEPS[self.step]
        try:
            pygame.mixer.music.load(str(CLIPS / self.cur["file"]))
            pygame.mixer.music.play(start=self.offset)
        except Exception as e:
            self.lbl_status.config(text=f"재생 오류: {e}", fg="#ff6b6b")
            return

        if self._stop_job:
            self.root.after_cancel(self._stop_job)
        self._stop_job = self.root.after(int(listen * 1000), self._stop)
        self._refresh_meta()

    def _stop(self) -> None:
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass

    # ─── 판정 ─────────────────────────────────────────
    def guess(self, idx: int) -> None:
        if self.answered:
            return
        self.answered = True
        self._stop()
        chosen = self.options[idx]
        correct = chosen["file"] == self.cur["file"]

        for b, opt in zip(self.choice_btns, self.options):
            b.config(state="disabled")
            if opt["file"] == self.cur["file"]:
                b.config(bg="#1f8f4e", fg="white")      # 정답은 항상 초록
            elif opt is chosen:
                b.config(bg="#b23b3b", fg="white")      # 내가 고른 오답은 빨강

        if correct:
            pts = max(20, 100 - self.step * 15)         # 적게 들었을수록 고득점
            self.score += pts
            self.streak += 1
            self.lbl_status.config(text=f"정답! +{pts}점", fg="#5fe08a")
        else:
            self.streak = 0
            self.lbl_status.config(
                text=f"땡! 정답: {self._label(self.cur)}", fg="#ff6b6b")
        self._refresh_meta()
        self.btn_next.pack(side="bottom", pady=12)  # 항상 창 맨 아래에 고정


def main() -> None:
    songs = load_playlist()
    root = tk.Tk()
    Quiz(root, songs)
    root.mainloop()


if __name__ == "__main__":
    main()
