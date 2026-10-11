@echo off
setlocal
cd /d "%~dp0"
if not exist backend\.venv\Scripts\python.exe (echo Run setup-windows.cmd first. & pause & exit /b 1)
if not exist node_modules (echo Frontend dependencies are missing. Run setup-windows.cmd first. & pause & exit /b 1)
start "MedIntel OCR API" /D "%~dp0backend" cmd /k ".venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
call npm.cmd run desktop
if errorlevel 1 pause
