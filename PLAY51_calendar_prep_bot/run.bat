@echo off
REM PLAY51 개인 비서 봇 실행 (더블클릭 또는 이 창에서 실행)
REM 끄려면 이 창에서 Ctrl+C, 창을 닫아도 봇이 꺼집니다.
cd /d "%~dp0"
echo [PLAY51] 봇 시작... (Ctrl+C 로 종료)
python -u bot.py
echo.
echo [PLAY51] 봇이 종료되었습니다.
pause
