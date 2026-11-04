@echo off
cd /d "%~dp0"
if not exist "backend\.venv\Scripts\python.exe" (
  echo Install backend dependencies first: py -m uv sync --project backend --frozen --python 3.12
  pause
  exit /b 1
)
"backend\.venv\Scripts\python.exe" "scripts\start-website.py" %*
if errorlevel 1 pause
