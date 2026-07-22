@echo off
REM 4시간 주기 스케줄러 — 이 창을 열어두면 계속 돈다. Ctrl-C 로 종료.
REM 인자 그대로 전달:  run_scheduler.bat --dry-run   /   run_scheduler.bat --interval-hours 1 --max-cycles 2
REM 파일 로그로 돌리려면(무인 실행):  run_scheduler.bat > run.log 2>&1
chcp 65001 >nul
cd /d "%~dp0"
echo [스케줄러 시작] 4시간마다 리포트 생성. 종료하려면 이 창에서 Ctrl-C.
python -u scheduler.py %*
echo.
echo [스케줄러 종료]
pause
