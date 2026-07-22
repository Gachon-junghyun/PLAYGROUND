@echo off
REM 뉴스 다이제스트 GUI 실행 — 더블클릭용. 진행 로그 + 리포트 실시간 스트리밍 창.
chcp 65001 >nul
cd /d "%~dp0"
python gui.py
if errorlevel 1 (
  echo.
  echo [오류] 실행 실패 — 위 메시지를 확인하세요. openai/yfinance 설치 여부, nvapi 키 등.
  pause
)
