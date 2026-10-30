@echo off
cd /d "%~dp0"
if not exist "backend\.venv\Scripts\python.exe" (
  echo Backend environment missing. Run: py -m uv sync --project backend --frozen --python 3.12
  pause
  exit /b 1
)
"backend\.venv\Scripts\python.exe" "scripts\start-local-demo.py"
if errorlevel 1 pause
