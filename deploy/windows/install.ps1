# install.ps1
# DIDRepChecker - Windows installer
# Run from the project root directory.
#
#   powershell -ExecutionPolicy Bypass -File deploy\windows\install.ps1

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path "$ScriptDir\..\.."

Write-Host ""
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host "  DIDRepChecker - Windows Installer" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host "  Project : $ProjectRoot" -ForegroundColor Yellow
Write-Host ""

$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) {
    Write-Host "ERROR: Python 3.9+ required. Install from https://python.org" -ForegroundColor Red
    exit 1
}
$ver = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
$parts = $ver.Split('.')
$major = [int]$parts[0]
$minor = [int]$parts[1]
if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 9)) {
    Write-Host "ERROR: Python 3.9+ required. Found: $ver" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Python $ver" -ForegroundColor Green

Push-Location $ProjectRoot

Write-Host "Creating virtual environment..." -ForegroundColor Yellow
if (Test-Path venv) {
    Remove-Item -Recurse -Force venv
}
& python -m venv venv

Write-Host "Installing build tools..." -ForegroundColor Yellow
& "venv\Scripts\python.exe" -m pip install --upgrade pip setuptools wheel -q

Write-Host "Installing package and dependencies..." -ForegroundColor Yellow
& "venv\Scripts\pip.exe" install -r requirements.txt -q
& "venv\Scripts\pip.exe" install . -q

Pop-Location

Write-Host ""
Write-Host "=======================================" -ForegroundColor Green
Write-Host "  DIDRepChecker installed successfully!" -ForegroundColor Green
Write-Host "=======================================" -ForegroundColor Green
Write-Host "  Location : $ProjectRoot"
Write-Host ""
Write-Host "  To start the server:"
Write-Host "    $ProjectRoot\deploy\windows\run.bat"
Write-Host ""
