@echo off
setlocal
cd /d "%~dp0"
if not exist node_modules (echo Frontend dependencies are missing. Run setup-windows.cmd first. & pause & exit /b 1)
rem The desktop app starts the OCR API itself (backend\.venv if present, otherwise the installed Python)
rem and stops it when the window closes.
call npm.cmd run desktop
if errorlevel 1 pause
