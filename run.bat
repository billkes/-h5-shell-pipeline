@echo off
chcp 65001 >nul
REM h5-shell-pipeline：H5 壳包批量生产交互式入口（Windows CMD 版）
REM 用法：双击运行，或在 CMD 中执行 .\run.bat [参数]

cd /d "%~dp0"

set "VENV_PYTHON=%CD%\.venv\Scripts\python.exe"
set "VENV_PIP=%CD%\.venv\Scripts\pip.exe"

if not exist ".venv" (
    echo.
    echo ════════════════════════════════════════════════════════════
    echo   首次运行，正在初始化环境...
    echo ════════════════════════════════════════════════════════════
    echo.
    echo   [1/3] 创建虚拟环境...
    python -m venv .venv
    if errorlevel 1 (
        echo   ❌ 创建虚拟环境失败，请确保已安装 Python3
        pause
        exit /b 1
    )
    echo   ✅ 虚拟环境创建成功

    echo.
    echo   [2/3] 安装依赖...
    "%VENV_PIP%" install -r requirements.txt -q
    if errorlevel 1 (
        echo   ❌ 安装依赖失败
        pause
        exit /b 1
    )
    echo   ✅ 依赖安装成功
    echo.
    echo   [3/3] 环境就绪（H5 Shell 专用流水线，独立于 cursor-ios-batch）...
    echo   ✅ 跳过飞书 / uupm 本地快照同步
    echo.
    echo   环境初始化完成！
    echo.
    timeout /t 1 /nobreak >nul
)

if defined PYTHONPATH (
    set "PYTHONPATH=%CD%\scripts;%PYTHONPATH%"
) else (
    set "PYTHONPATH=%CD%\scripts"
)

"%VENV_PYTHON%" -m batch %*
if errorlevel 1 pause
