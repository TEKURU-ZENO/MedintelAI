@echo off
setlocal
cd /d "%~dp0"
where node >nul 2>nul || (echo Node.js is required. Install Node.js 20 LTS or newer. & pause & exit /b 1)
if not exist node_modules (call npm.cmd install || (pause & exit /b 1))
call npm.cmd run desktop:win
if errorlevel 1 (echo Build failed. Review the error above. & pause & exit /b 1)
echo Installer output is in the release folder.
pause
