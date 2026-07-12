# h5-shell-pipeline：H5 Shell 批量生产入口（Windows PowerShell 版）
# 用法：.\run.ps1 [python -m batch 参数]

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
        Write-Host "  创建虚拟环境失败，请确保已安装 Python3"
        Read-Host "按回车退出"
        exit 1
    }
    Write-Host "  ✅ 虚拟环境创建成功"

    Write-Host ""
    Write-Host "  [2/3] 安装依赖..."
    & $VenvPip install -r requirements.txt -q
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  安装依赖失败"
        Read-Host "按回车退出"
        exit 1
    }
    Write-Host "  ✅ 依赖安装成功"

    Write-Host ""
    Write-Host "  环境初始化完成！"
    Write-Host ""
    Start-Sleep -Seconds 1
}

if ($args.Count -eq 0) {
    Write-Host ""
    Write-Host "h5-shell-pipeline task CLI"
    Write-Host ""
    Write-Host "常用命令："
    Write-Host "  .\run.ps1 task-init --batch-id <id> --rows <n>"
    Write-Host "  .\run.ps1 task-add --rows <n>"
    Write-Host "  .\run.ps1 task-validate"
    Write-Host "  .\run.ps1 task-list"
    Write-Host "  .\run.ps1 task-show <应用主名称>"
    Write-Host "  .\run.ps1 task-ready"
    Write-Host "  .\run.ps1 build-all --h5-host <host> --team-id <id>"
    Write-Host "  .\run.ps1 build <应用主名称>"
    Write-Host ""
    & $VenvPython -m batch --help
    exit 0
}

& $VenvPython -m batch @args
