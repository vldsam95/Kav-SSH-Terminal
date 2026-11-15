@echo off
setlocal
cd /d "%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\run.ps1"

if errorlevel 1 (
    echo.
    echo Kav SSH Terminal failed to start.
    echo If this is the first run on this computer, install Python 3.12 or newer:
    echo https://www.python.org/downloads/
    echo.
    pause
)
