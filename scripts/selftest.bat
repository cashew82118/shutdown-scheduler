@echo off
rem P1 selftest: arm 600s -> record -> cancel -> verify. Safe, runs in seconds.
setlocal
cd /d "%~dp0.."

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found: .venv
    pause
    exit /b 1
)

".venv\Scripts\python.exe" "scripts\selftest_shutdown.py"
echo.
pause
