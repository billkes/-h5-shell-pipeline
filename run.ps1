#!/usr/bin/env powershell
# h5-shell-pipeline: H5 Shell batch production entry (Windows PowerShell)
# Usage: .\run.ps1 for interactive menu, or .\run.ps1 <command> [args]

Set-Location -Path $PSScriptRoot

$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
$venvPip = Join-Path $PSScriptRoot ".venv\Scripts\pip.exe"

if (-not (Test-Path ".venv")) {
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "  First run, initializing environment..." -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host ""

    Write-Host "  [1/3] Creating virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  Failed to create venv. Please make sure Python3 is installed." -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
    Write-Host "  OK venv created" -ForegroundColor Green

    Write-Host ""
    Write-Host "  [2/3] Installing dependencies..." -ForegroundColor Yellow
    & $venvPip install -r requirements.txt -q
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  Failed to install dependencies" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
    Write-Host "  OK dependencies installed" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Environment initialization complete!" -ForegroundColor Green
    Write-Host ""
    Start-Sleep -Seconds 1
}

$env:PYTHONPATH = "$PSScriptRoot\scripts;$env:PYTHONPATH"

# No args → interactive menu (handled by Python)
# With args → direct command execution
& $venvPython -m batch @args
if ($args.Count -eq 0) {
    Read-Host "Press Enter to exit"
}
