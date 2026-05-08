# install_windows.ps1
# One‑command installer for DID Reputation Checker on Windows
# Installs into %LOCALAPPDATA%\DIDRepChecker

param(
    [string]$RepoUrl = "https://github.com/siamakanda/DIDRepChecker.git",
    [string]$Branch = "main"
)

$InstallDir = "$env:LOCALAPPDATA\DIDRepChecker"

Write-Host "=======================================" -ForegroundColor Cyan
Write-Host "DID Reputation Checker Installer for Windows" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Installation directory: $InstallDir" -ForegroundColor Yellow
Write-Host ""

# --- Helper: Install Git if missing ---
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "Git not found. Installing Git for Windows..." -ForegroundColor Yellow
    $gitInstaller = "$env:TEMP\GitInstaller.exe"
    $gitUrl = "https://github.com/git-for-windows/git/releases/download/v2.45.2.windows.1/Git-2.45.2-64-bit.exe"
    Invoke-WebRequest -Uri $gitUrl -OutFile $gitInstaller
    Start-Process -FilePath $gitInstaller -ArgumentList "/VERYSILENT /NORESTART" -Wait
    Remove-Item $gitInstaller
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
}

# --- Helper: Install Python if missing ---
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Python not found. Installing Python 3.12..." -ForegroundColor Yellow
    $pythonInstaller = "$env:TEMP\python-installer.exe"
    $pythonUrl = "https://www.python.org/ftp/python/3.12.3/python-3.12.3-amd64.exe"
    Invoke-WebRequest -Uri $pythonUrl -OutFile $pythonInstaller
    Start-Process -FilePath $pythonInstaller -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1" -Wait
    Remove-Item $pythonInstaller
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
}

# --- Ensure installation directory exists and contains the repo ---
if (-not (Test-Path $InstallDir)) {
    Write-Host "Cloning repository..." -ForegroundColor Yellow
    git clone --branch $Branch $RepoUrl $InstallDir
} else {
    if (Test-Path "$InstallDir\.git") {
        Write-Host "Repository already exists. Pulling latest changes..." -ForegroundColor Yellow
        Push-Location $InstallDir
        git pull origin $Branch
        Pop-Location
    } else {
        Write-Host "Directory exists but is not a git repository. Using existing files (no update)." -ForegroundColor Yellow
    }
}

# Change to the installation directory
Set-Location $InstallDir

# --- Virtual environment (remove if corrupted) ---
$venvDir = "$InstallDir\venv"
if (Test-Path $venvDir) {
    $activateScript = "$venvDir\Scripts\Activate.ps1"
    if (-not (Test-Path $activateScript)) {
        Write-Host "Virtual environment is incomplete. Removing it..." -ForegroundColor Yellow
        Remove-Item -Recurse -Force $venvDir
    }
}
if (-not (Test-Path $venvDir)) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv $venvDir
    if (-not (Test-Path "$venvDir\Scripts\Activate.ps1")) {
        Write-Host "ERROR: Failed to create virtual environment." -ForegroundColor Red
        exit 1
    }
}

# --- Activate and install dependencies ---
Write-Host "Installing Python dependencies..." -ForegroundColor Yellow
& "$venvDir\Scripts\Activate.ps1"
python -m pip install --upgrade pip
if (Test-Path "$InstallDir\requirements.txt") {
    pip install -r "$InstallDir\requirements.txt"
} else {
    Write-Host "requirements.txt not found. Installing core packages..." -ForegroundColor Yellow
    pip install fastapi uvicorn aiohttp lxml aiosqlite
}
pip install gunicorn uvicorn  # optional but useful

Write-Host ""
Write-Host "Installation complete!" -ForegroundColor Green
Write-Host "API files are located in: $InstallDir"
Write-Host ""

# --- Prompt to start the server ---
$runScript = Join-Path $InstallDir "run_windows.bat"
if (-not (Test-Path $runScript)) {
    Write-Host "WARNING: run_windows.bat not found." -ForegroundColor Yellow
    Write-Host "You can start the server manually: cd $InstallDir && python server/api_server.py" -ForegroundColor Cyan
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