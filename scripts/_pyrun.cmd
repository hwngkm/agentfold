@echo off
chcp 65001 >nul
set "PYTHONUTF8=1"
REM Python launcher for hooks on Windows cmd.exe: active venv, repo .venv, then py -3 / python.
REM No Python found: exit 0 silently - hooks must never block the AI tool or git.

if defined VIRTUAL_ENV if exist "%VIRTUAL_ENV%\Scripts\python.exe" (
  "%VIRTUAL_ENV%\Scripts\python.exe" %*
  exit /b %ERRORLEVEL%
)

if exist "%~dp0..\.venv\Scripts\python.exe" (
  "%~dp0..\.venv\Scripts\python.exe" %*
  exit /b %ERRORLEVEL%
)

where py >nul 2>nul
if not errorlevel 1 (
  py -3 %*
  exit /b %ERRORLEVEL%
)

where python >nul 2>nul
if not errorlevel 1 (
  python %*
  exit /b %ERRORLEVEL%
)

exit /b 0
