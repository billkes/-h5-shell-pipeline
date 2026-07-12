@echo off
REM cursor-ios-batch: Flutter / iOS batch production entry (Windows)
REM Usage: double-click, or run .\run.bat in CMD

cd /d "%~dp0"

set "VENV_PYTHON=%CD%\.venv\Scripts\python.exe"
set "VENV_PIP=%CD%\.venv\Scripts\pip.exe"

if not exist ".venv" (
    echo.
    echo ============================================================
    echo   First run, initializing environment...
    echo ============================================================
    echo.
    echo   [1/3] Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo   Failed to create venv. Please make sure Python3 is installed.
        pause
        exit /b 1
    )
    echo   OK venv created

    echo.
    echo   [2/3] Installing dependencies...
    "%VENV_PIP%" install -r requirements.txt -q
    if errorlevel 1 (
        echo   Failed to install dependencies
        pause
        exit /b 1
    )
    echo   OK dependencies installed
    echo.
    echo   [3/3] Environment ready (ui-ux-pro-max loaded at runtime)
    echo   OK skipped uupm local snapshot sync
    echo.
    echo   Environment initialization complete!
    echo.
    timeout /t 1 /nobreak >nul
)

set "PYTHONPATH=%CD%\scripts%PYTHONPATH%"
"%VENV_PYTHON%" -m batch %*
if errorlevel 1 pause
