@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if %errorlevel%==0 (
  python src\codex_token_report.py --out report --open
  exit /b %errorlevel%
)

where py >nul 2>nul
if %errorlevel%==0 (
  py -3 src\codex_token_report.py --out report --open
  exit /b %errorlevel%
)

echo Python not found. Install Python 3.8+ and ensure it is in PATH.
pause
exit /b 1

