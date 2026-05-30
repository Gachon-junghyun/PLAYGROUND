@echo off
REM PLAY29 네이버 산업분석 PDF 다운로더 - 더블클릭 실행용
REM 의존성 설치 후 1페이지 전체 PDF를 .\naver_research_reports 에 저장한다.
cd /d "%~dp0"
echo === 의존성 확인/설치 ===
python -m pip install requests beautifulsoup4 -q
echo.
echo === 목록 미리보기 (다운로드 전 구조 확인) ===
python naver_research_dl.py --list-only
echo.
echo === PDF 다운로드 시작 ===
python naver_research_dl.py --out ".\naver_research_reports"
echo.
echo === 끝. naver_research_reports 폴더를 확인하세요. ===
pause
