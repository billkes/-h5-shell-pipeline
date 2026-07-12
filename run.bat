@echo off
REM h5-shell-pipeline: H5 Shell batch production entry (Windows)
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
    echo   Environment initialization complete!
    echo.
    timeout /t 1 /nobreak >nul
)

if defined PYTHONPATH (
    set "PYTHONPATH=%CD%\scripts;%PYTHONPATH%"
) else (
    set "PYTHONPATH=%CD%\scripts"
)

if "%~1"=="" (
    echo.
    echo h5-shell-pipeline task CLI
    echo.
    echo Common commands:
    echo   .\run.bat task-init --batch-id ^<id^> --rows ^<n^>
    echo   .\run.bat task-add --rows ^<n^>
    echo   .\run.bat task-validate
    echo   .\run.bat task-list
    echo   .\run.bat task-show ^<app-name^>
    echo   .\run.bat task-ready
    echo   .\run.bat build-all --h5-host ^<host^> --team-id ^<id^>
    echo   .\run.bat build ^<app-name^>
    echo.
    "%VENV_PYTHON%" -m batch --help
    exit /b 0
)

"%VENV_PYTHON%" -m batch %*
if errorlevel 1 pause
