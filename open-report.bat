@echo off
setlocal
cd /d "%~dp0"
if /i "%~1"=="--serve" goto serve_hidden

if exist "%~dpn0.vbs" (
  wscript //nologo "%~dpn0.vbs" "%~f0" --serve
) else (
  start "Codex Token Usage Service" /min cmd /c ""%~f0" --serve"
)

timeout /t 2 /nobreak >nul
start "" http://127.0.0.1:8000
exit /b 0

:serve_hidden
where python >nul 2>nul
if %errorlevel%==0 (
  python src\codex_token_report.py serve --host 127.0.0.1 --port 8000 --db-file data\token-account.db
  exit /b %errorlevel%
)

where py >nul 2>nul
if %errorlevel%==0 (
  py -3 src\codex_token_report.py serve --host 127.0.0.1 --port 8000 --db-file data\token-account.db
  exit /b %errorlevel%
)

start "" cmd /k "echo 未找到 Python：既没有 python 也没有 py。 && echo 请先安装 Python 3.11+ 并加入 PATH，然后重试。 && pause"
exit /b 1
