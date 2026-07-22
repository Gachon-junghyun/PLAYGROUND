@echo off
REM 다이제스트 1회 실행 (콘솔). 인자 그대로 전달.
REM   run_once.bat                 → 실제 1회 (LLM 호출)
REM   run_once.bat --dry-run       → 크레딧 0, 배관/재료만
REM   run_once.bat --frac 1.0      → 완전 무손실(전체)
chcp 65001 >nul
cd /d "%~dp0"
python -u digest.py --once %*
echo.
pause
