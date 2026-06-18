# install_windows.ps1
# One‑command installer for DID Reputation Checker on Windows
# Installs into %LOCALAPPDATA%\DIDRepChecker

param(
    [string]$RepoUrl = "https://github.com/siamakanda/DIDRepChecker.git",   # fixed URL
    [string]$Branch = "main"
)

$InstallDir = "$env:LOCALAPPDATA\DIDRepChecker"

Write-Host "=======================================" -ForegroundColor Cyan
Write-Host "DID Reputation Checker Installer for Windows" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Installation directory: $InstallDir" -ForegroundColor Yellow
Write-Host ""

# --- Check Python version (requires 3.9+) ---
try {
    $pyVersion = python --version 2>&1
    if ($pyVersion -match "Python 3\.(\d+)") {
        $minor = [int]$Matches[1]
        if ($minor -lt 9) {
            Write-Host "Python 3.9 or higher is required. Found: $pyVersion" -ForegroundColor Red
            exit 1
        }
    } else {
        Write-Host "Could not determine Python version. Ensure Python 3.9+ is installed." -ForegroundColor Yellow
    }
} catch {
    Write-Host "Python not found. Please install Python 3.9+ from https://python.org" -ForegroundColor Red
    exit 1
}

# --- Helper: Install Git if missing ---
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

# --- Handle existing installation directory ---
if (Test-Path $InstallDir) {
    if (Test-Path "$InstallDir\.git") {
        Write-Host "Repository already exists. Pulling latest changes..." -ForegroundColor Yellow
        Push-Location $InstallDir
        git pull origin $Branch
        Pop-Location
    } else {
        Write-Host "Directory exists but is not a git repository." -ForegroundColor Yellow
        $choice = Read-Host "Do you want to remove it and clone fresh? (y/n)"
        if ($choice -eq 'y') {
            Write-Host "Removing existing directory..." -ForegroundColor Yellow
            Remove-Item -Recurse -Force $InstallDir -ErrorAction SilentlyContinue
        } else {
            Write-Host "Using existing files (no update)." -ForegroundColor Yellow
        }
    }
}

# --- Clone repository if needed ---
if (-not (Test-Path $InstallDir)) {
    Write-Host "Cloning repository..." -ForegroundColor Yellow
    git clone --branch $Branch $RepoUrl $InstallDir
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to clone repository. Please check the URL and network." -ForegroundColor Red
        exit 1
    }
}

# Change to the installation directory
Set-Location $InstallDir

# --- Virtual environment: remove if corrupted, else create ---
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
    pip install fastapi uvicorn aiohttp lxml aiosqlite pyperclip
}

# --- Create default config.json if missing ---
$configFile = "$InstallDir\config.json"
if (-not (Test-Path $configFile)) {
    Write-Host "Creating default config.json..." -ForegroundColor Yellow
    @"
{
    "cache_ttl_days": 3
}
"@ | Out-File -Encoding utf8 -FilePath $configFile
}

Write-Host ""
Write-Host "Installation complete!" -ForegroundColor Green
Write-Host "API files are located in: $InstallDir"
Write-Host "Configuration file: $configFile"
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