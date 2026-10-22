@echo off
rem P2 demo: clock dial + time wheels, no shutdown logic involved.
setlocal
cd /d "%~dp0.."

if not exist ".venv\Scripts\pythonw.exe" (
    echo [ERROR] Virtual environment not found: .venv
    pause
    exit /b 1
)

start "" ".venv\Scripts\pythonw.exe" "src\ui\clock_demo.py"
exit /b 0
