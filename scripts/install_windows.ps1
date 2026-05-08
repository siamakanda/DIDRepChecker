# install_windows.ps1
# One‑command installer for DID Reputation Checker on Windows
# Installs into %LOCALAPPDATA%\DIDRepChecker (per‑user, writable)
# Run this script as Administrator (only needed to install Git/Python).

param(
    [string]$RepoUrl = "https://github.com/siamakanda/DIDRepChecker.git",
    [string]$Branch = "main"
)

# Fixed installation directory – never use current directory
$InstallDir = "$env:LOCALAPPDATA\DIDRepChecker"

Write-Host "=======================================" -ForegroundColor Cyan
Write-Host "DID Reputation Checker Installer for Windows" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Installation directory: $InstallDir" -ForegroundColor Yellow
Write-Host ""

# Check if running as Administrator (still needed to install Git/Python)
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "WARNING: Administrator rights are required to install Git and Python." -ForegroundColor Yellow
    Write-Host "If Git and Python are already installed, you can continue without admin rights." -ForegroundColor Yellow
    $continue = Read-Host "Continue anyway? (y/n)"
    if ($continue -ne 'y') { exit 1 }
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

# Install Python if not present
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Python not found. Installing Python 3.12..." -ForegroundColor Yellow
    $pythonInstaller = "$env:TEMP\python-installer.exe"
    $pythonUrl = "https://www.python.org/ftp/python/3.12.3/python-3.12.3-amd64.exe"
    Invoke-WebRequest -Uri $pythonUrl -OutFile $pythonInstaller
    Start-Process -FilePath $pythonInstaller -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1" -Wait
    Remove-Item $pythonInstaller
    # Refresh environment
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
}

# Handle existing installation
if (Test-Path $InstallDir) {
    if (Test-Path "$InstallDir\.git") {
        Write-Host "Repository already exists. Pulling latest changes..." -ForegroundColor Yellow
        Set-Location $InstallDir
        git pull origin $Branch
    } else {
        Write-Host "Installation directory already exists (non‑git). Skipping clone." -ForegroundColor Yellow
        Write-Host "If you want a fresh installation, delete the folder first." -ForegroundColor Yellow
        Set-Location $InstallDir
    }
} else {
    Write-Host "Cloning repository into $InstallDir..." -ForegroundColor Yellow
    git clone --branch $Branch $RepoUrl $InstallDir
    Set-Location $InstallDir
}

# Create virtual environment if missing
$venvDir = "$InstallDir\venv"
if (-not (Test-Path $venvDir)) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv $venvDir
}

# Activate and install dependencies
Write-Host "Installing Python dependencies..." -ForegroundColor Yellow
& "$venvDir\Scripts\Activate.ps1"
python -m pip install --upgrade pip
if (Test-Path "$InstallDir\requirements.txt") {
    pip install -r "$InstallDir\requirements.txt"
} else {
    Write-Host "requirements.txt not found. Installing core packages..." -ForegroundColor Yellow
    pip install fastapi uvicorn aiohttp lxml aiosqlite
}
pip install gunicorn uvicorn  # optional, but useful

Write-Host ""
Write-Host "Installation complete!" -ForegroundColor Green
Write-Host "API files are located in: $InstallDir"
Write-Host ""

$runScript = Join-Path $InstallDir "run_windows.bat"
if (-not (Test-Path $runScript)) {
    Write-Host "WARNING: run_windows.bat not found in the expected location." -ForegroundColor Yellow
    Write-Host "You can start the server manually using one of these commands:" -ForegroundColor Cyan
    Write-Host "  1. cd $InstallDir && python server/api_server.py" -ForegroundColor White
    Write-Host "  2. cd $InstallDir && uvicorn server.api_server:app --host 0.0.0.0 --port 8000 --reload" -ForegroundColor White
    Write-Host ""
    $manual = Read-Host "Do you want to start the server using the first command now? (Y/N)"
    if ($manual -eq 'Y' -or $manual -eq 'y') {
        Write-Host "Starting server..." -ForegroundColor Yellow
        Start-Process -FilePath "python" -ArgumentList "server/api_server.py" -WorkingDirectory $InstallDir -WindowStyle Normal
        Write-Host "Server started in a new window." -ForegroundColor Green
    }
    exit 0
}

$startNow = Read-Host "Do you want to start the server now? (Y/N)"
if ($startNow -eq 'Y' -or $startNow -eq 'y') {
    Write-Host "Starting server in a new window..." -ForegroundColor Yellow
    Start-Process -FilePath $runScript -WindowStyle Normal -WorkingDirectory $InstallDir
    Write-Host "Server window opened. You can close it to stop the server." -ForegroundColor Green
} else {
    Write-Host "To start the server manually, run: $InstallDir\run_windows.bat" -ForegroundColor Cyan
}
Write-Host ""