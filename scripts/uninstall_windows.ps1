# uninstall_windows.ps1
# Removes the DID Reputation Checker installation from Windows.
# Run as Administrator.

param(
    [string]$InstallDir = "$env:LOCALAPPDATA\DIDRepChecker"
)

Write-Host "Uninstalling DID Reputation Checker from $InstallDir" -ForegroundColor Cyan

# Change to a safe directory (System32) to avoid locking the installation folder
cd $env:SystemRoot\System32

# Stop any running server process (if it's still running)
$serverProcess = Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "*$InstallDir*" }
if ($serverProcess) {
    Write-Host "Stopping running server process..." -ForegroundColor Yellow
    $serverProcess | Stop-Process -Force
}

# Remove scheduled task if it exists (though we never created one in the installer)
$taskName = "DIDRepCheckerAPI"
$task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($task) {
    Write-Host "Removing scheduled task..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

# Remove application directory
if (Test-Path $InstallDir) {
    Write-Host "Removing installation directory..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force $InstallDir -ErrorAction SilentlyContinue
    if (Test-Path $InstallDir) {
        Write-Host "ERROR: Could not delete all files. Please close any programs using the folder and try again." -ForegroundColor Red
        exit 1
    } else {
        Write-Host "Installation directory removed." -ForegroundColor Green
    }
} else {
    Write-Host "Installation directory not found." -ForegroundColor Yellow
}

Write-Host "Uninstall complete." -ForegroundColor Green