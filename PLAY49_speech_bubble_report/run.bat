@echo off
rem PLAY49 말풍선 리포트 — 더블클릭하면 데스크탑 창이 뜬다 (콘솔 없음, 서버 없음)
cd /d "%~dp0"
start "" pythonw app.py
