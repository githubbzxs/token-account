@echo off
setlocal
cd /d "%~dp0"
if /i "%~1"=="--run" goto run_once

if exist "%~dpn0.vbs" (
  wscript //nologo "%~dpn0.vbs" "%~f0" --run
  exit /b 0
)

start "" /min cmd /c ""%~f0" --run"
exit /b 0

:run_once
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

start "" cmd /k "echo Python not found: neither python nor py is available. && echo Install Python 3.8+ and add it to PATH, then retry. && pause"
exit /b 1

