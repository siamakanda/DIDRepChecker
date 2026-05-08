# uninstall_windows.ps1
# Removes the DID Reputation Checker installation from Windows.
# Run as Administrator.

param(
    [string]$InstallDir = "$env:LOCALAPPDATA\DIDRepChecker"
)

Write-Host "Uninstalling DID Reputation Checker from $InstallDir" -ForegroundColor Cyan

# Remove scheduled task if exists
$taskName = "DIDRepCheckerAPI"
$task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($task) {
    Write-Host "Stopping and removing scheduled task..." -ForegroundColor Yellow
    Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

# Remove application directory
if (Test-Path $InstallDir) {
    Write-Host "Removing installation directory..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force $InstallDir
}

Write-Host "Uninstall complete." -ForegroundColor Green