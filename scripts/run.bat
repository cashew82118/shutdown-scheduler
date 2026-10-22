@echo off
rem Dev launcher: starts the app without a console window.
setlocal
cd /d "%~dp0.."

if not exist ".venv\Scripts\pythonw.exe" (
    echo [ERROR] Virtual environment not found: .venv
    echo Run the setup step first.
    pause
    exit /b 1
)

start "" ".venv\Scripts\pythonw.exe" "src\main.py"
exit /b 0
