@echo off
REM h5-shell-pipeline: H5 Shell batch production entry (Windows CMD)
REM Usage: double-click, or run .\run.bat in CMD

cd /d "%~dp0"

set "VENV_PYTHON=%CD%\.venv\Scripts\python.exe"
set "VENV_PIP=%CD%\.venv\Scripts\pip.exe"

if not exist ".venv" (
    echo.
    echo ============================================================
    echo   ????????????...
    echo ============================================================
    echo.
    echo   [1/3] ??????...
    python -m venv .venv
    if errorlevel 1 (
        echo   ??????????????? Python3
        pause
        exit /b 1
    )
    echo   OK ????????

    echo.
    echo   [2/3] ????...
    "%VENV_PIP%" install -r requirements.txt -q
    if errorlevel 1 (
        echo   ??????
        pause
        exit /b 1
    )
    echo   OK ??????
    echo.
    echo   [3/3] ?????H5 Shell ??????
    echo   OK ???? / uupm ??????
    echo.
    echo   ????????
    echo.
    timeout /t 1 /nobreak >nul
)

set "PYTHONPATH=%CD%\scripts;%PYTHONPATH%"
"%VENV_PYTHON%" -m batch %*
if errorlevel 1 pause
