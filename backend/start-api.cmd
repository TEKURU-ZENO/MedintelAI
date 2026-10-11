@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (echo Run setup-windows.cmd from the project root first. & pause & exit /b 1)
call .venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause
