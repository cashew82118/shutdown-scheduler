@echo off
rem Build a single-file Windows executable.
rem Note: use %CD% for absolute paths - --specpath moves the working base directory,
rem so relative paths like assets\app.ico would resolve to build\assets\app.ico.
setlocal
cd /d "%~dp0.."

if not exist ".venv\Scripts\pyinstaller.exe" (
    echo [ERROR] PyInstaller not installed.
    pause
    exit /b 1
)

".venv\Scripts\pyinstaller.exe" --noconfirm --clean --onefile --windowed ^
    --name "定时关机" ^
    --icon "%CD%\assets\app.ico" ^
    --add-data "%CD%\assets;assets" ^
    --version-file "%CD%\assets\version_info.txt" ^
    --paths "%CD%\src" ^
    --distpath "dist" ^
    --workpath "build" ^
    --specpath "build" ^
    "src\main.py"

if errorlevel 1 (
    echo [ERROR] Build failed.
    pause
    exit /b 1
)

echo.
echo Build finished: dist\定时关机.exe
pause
