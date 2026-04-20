# install_windows.ps1
# One‑command installer for DID Reputation API on Windows
# Run this script as Administrator.

param(
    [string]$RepoUrl = "https://github.com/siamakanda/DIDRepChecker.git",
    [string]$Branch = "main",
    [string]$InstallDir = "$env:ProgramFiles\DIDReputationAPI"
)

Write-Host "=======================================" -ForegroundColor Cyan
Write-Host "DID Reputation API Installer for Windows" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "This installer must be run as Administrator. Please restart PowerShell as Administrator." -ForegroundColor Red
    exit 1
}

# Install Git if not present
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "Git not found. Installing Git for Windows..." -ForegroundColor Yellow
    $gitInstaller = "$env:TEMP\GitInstaller.exe"
    $gitUrl = "https://github.com/git-for-windows/git/releases/download/v2.45.2.windows.1/Git-2.45.2-64-bit.exe"
    Invoke-WebRequest -Uri $gitUrl -OutFile $gitInstaller
    Start-Process -FilePath $gitInstaller -ArgumentList "/VERYSILENT /NORESTART" -Wait
    Remove-Item $gitInstaller
    # Refresh environment variables
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
}

# Clone or update repository
if (Test-Path $InstallDir) {
    Write-Host "Repository already exists. Pulling latest changes..." -ForegroundColor Yellow
    Set-Location $InstallDir
    git pull origin $Branch
} else {
    Write-Host "Cloning repository to $InstallDir..." -ForegroundColor Yellow
    git clone --branch $Branch $RepoUrl $InstallDir
    Set-Location $InstallDir
}

# Run the existing batch installer (it will set up venv and dependencies)
Write-Host "Running installer_windows.bat..." -ForegroundColor Yellow
Start-Process -Wait -FilePath "$InstallDir\scripts\installer_windows.bat" -Verb RunAs

Write-Host ""
Write-Host "Installation complete!" -ForegroundColor Green
Write-Host "API files are located in: $InstallDir"
Write-Host "To start the server manually, run: $InstallDir\run_windows.bat"
Write-Host ""
Write-Host "Note: The server does NOT start automatically on boot. To add it as a scheduled task, run the following in an elevated PowerShell:"
Write-Host "  `$action = New-ScheduledTaskAction -Execute '$InstallDir\venv\Scripts\python.exe' -Argument '-m uvicorn server.api_server:app --host 0.0.0.0 --port 8000'"
Write-Host "  Register-ScheduledTask -TaskName 'DIDReputationAPI' -Action `$action -Trigger (New-ScheduledTaskTrigger -AtStartup) -User 'SYSTEM' -RunLevel Highest"