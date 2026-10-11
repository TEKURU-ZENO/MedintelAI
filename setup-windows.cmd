@echo off
setlocal
cd /d "%~dp0"
where node >nul 2>nul || (echo Node.js 20+ is required. Install it first. & pause & exit /b 1)
where py >nul 2>nul || (echo Python 3.10+ is required. Install it first. & pause & exit /b 1)
if not exist backend\.venv (
  py -3.11 -m venv backend\.venv
  if errorlevel 1 (echo Python 3.11 is recommended for the ML engine. Install Python 3.11 and rerun setup. & pause & exit /b 1)
)
call backend\.venv\Scripts\python.exe -m pip install --upgrade pip || (pause & exit /b 1)
echo Installing the original MedIntel OCR engine dependencies. This may take time because the ML runtime is large.
call backend\.venv\Scripts\python.exe -m pip install -r backend\requirements-original.txt || (echo Original engine dependency installation failed. Review the Python version and error above. & pause & exit /b 1)
call backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt || (pause & exit /b 1)
if not exist node_modules (
  call npm.cmd install
  if errorlevel 1 (pause & exit /b 1)
)
echo Setup completed. Run run-medintel.cmd to launch the API and desktop UI.
pause
