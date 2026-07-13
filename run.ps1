# h5-shell-pipeline：H5 壳包批量生产交互式入口（Windows PowerShell 版）
# 用法：.\run.ps1 [参数]

Set-Location -Path $PSScriptRoot

$VenvPython = "$PWD\.venv\Scripts\python.exe"
$VenvPip = "$PWD\.venv\Scripts\pip.exe"

$env:PYTHONPATH = "$PWD\scripts" + $(if ($env:PYTHONPATH) { ";$env:PYTHONPATH" } else { "" })

if (-not (Test-Path ".venv")) {
    Write-Host ""
    Write-Host "════════════════════════════════════════════════════════════"
    Write-Host "  首次运行，正在初始化环境..."
    Write-Host "════════════════════════════════════════════════════════════"
    Write-Host ""

    Write-Host "  [1/3] 创建虚拟环境..."
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ❌ 创建虚拟环境失败，请确保已安装 Python3"
        Read-Host "按回车退出"
        exit 1
    }
    Write-Host "  ✅ 虚拟环境创建成功"

    Write-Host ""
    Write-Host "  [2/3] 安装依赖..."
    & $VenvPip install -r requirements.txt -q
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ❌ 安装依赖失败"
        Read-Host "按回车退出"
        exit 1
    }
    Write-Host "  ✅ 依赖安装成功"

    Write-Host ""
    Write-Host "  [3/3] 环境就绪（H5 Shell 专用流水线，独立于 cursor-ios-batch）..."
    Write-Host "  ✅ 跳过飞书 / uupm 本地快照同步"
    Write-Host ""
    Write-Host "  环境初始化完成！"
    Write-Host ""
    Start-Sleep -Seconds 1
}

& $VenvPython -m batch @args
