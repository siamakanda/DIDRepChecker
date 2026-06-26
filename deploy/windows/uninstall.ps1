# uninstall.ps1
# DID Intel — Windows uninstaller
# Run as Administrator.

param(
    [string]$InstallDir = "$env:LOCALAPPDATA\did-intel"
)

Write-Host ""
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host "  DID Intel — Windows Uninstaller" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Removing: $InstallDir" -ForegroundColor Yellow
Write-Host ""

# Change to a safe directory to avoid locking the folder
Set-Location $env:SystemRoot\System32

# Stop any running python processes from this install
$serverProcess = Get-Process -Name "python" -ErrorAction SilentlyContinue |
    Where-Object { $_.Path -like "*$InstallDir*" }
if ($serverProcess) {
    Write-Host "[1/2] Stopping running server..." -ForegroundColor Yellow
    $serverProcess | Stop-Process -Force
    Write-Host "  ✓ Server stopped"
} else {
    Write-Host "[1/2] No running server found"
}

# Remove application directory
if (Test-Path $InstallDir) {
    Write-Host "[2/2] Removing installation directory..."
    Remove-Item -Recurse -Force $InstallDir -ErrorAction SilentlyContinue
    if (Test-Path $InstallDir) {
        Write-Host "  ✗ Could not delete all files. Close any programs using the folder." -ForegroundColor Red
        exit 1
    }
    Write-Host "  ✓ Directory removed"
} else {
    Write-Host "[2/2] Install directory not found — nothing to remove"
}

Write-Host ""
Write-Host "Uninstall complete." -ForegroundColor Green
Write-Host ""