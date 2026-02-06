@echo off
setlocal
cd /d "%~dp0"
set "REFRESH_SECONDS=15"

where python >nul 2>nul
if %errorlevel%==0 (
  python src\codex_token_report.py --out report --open
  if not %errorlevel%==0 exit /b %errorlevel%
  goto loop_python
)

where py >nul 2>nul
if %errorlevel%==0 (
  py -3 src\codex_token_report.py --out report --open
  if not %errorlevel%==0 exit /b %errorlevel%
  goto loop_py
)

echo Python not found. Install Python 3.8+ and ensure it is in PATH.
pause
exit /b 1

:loop_python
timeout /t %REFRESH_SECONDS% /nobreak >nul
python src\codex_token_report.py --out report >nul
if not %errorlevel%==0 (
  echo Report refresh failed. Retrying in %REFRESH_SECONDS%s...
)
goto loop_python

:loop_py
timeout /t %REFRESH_SECONDS% /nobreak >nul
py -3 src\codex_token_report.py --out report >nul
if not %errorlevel%==0 (
  echo Report refresh failed. Retrying in %REFRESH_SECONDS%s...
)
goto loop_py

