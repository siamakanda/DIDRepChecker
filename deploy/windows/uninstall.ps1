# uninstall.ps1
# DIDRepChecker - Windows uninstaller
# Run from the project root directory.

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path "$ScriptDir\..\.."

Write-Host ""
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host "  DIDRepChecker - Uninstaller" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host "  Project : $ProjectRoot" -ForegroundColor Yellow
Write-Host ""

Push-Location $ProjectRoot

Get-Process -Name python -ErrorAction SilentlyContinue |
    Where-Object { $_.Path -like "*$ProjectRoot*" } |
    Stop-Process -Force

if (Test-Path venv) {
    Write-Host "Removing virtual environment..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force venv
}

Remove-Item -Recurse -Force did_intel.egg-info -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force build -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force dist -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force .pytest_cache -ErrorAction SilentlyContinue

Pop-Location

Write-Host ""
Write-Host "Uninstall complete. Source files untouched." -ForegroundColor Green
Write-Host ""
