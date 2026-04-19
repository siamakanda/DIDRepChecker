@echo off
title DID Reputation API Server
echo =======================================
echo DID Reputation API Server (FastAPI)
echo =======================================
echo.

REM Change directory to project root so venv is created globally
cd /d "%~dp0.."

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed or not in PATH.
    echo Please install Python 3.9+ from https://python.org
    pause
    exit /b 1
)

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo Failed to create virtual environment.
        pause
        exit /b 1
    )
)

REM Activate virtual environment
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo Failed to activate virtual environment.
    pause
    exit /b 1
)

REM Install dependencies
echo Installing/upgrading dependencies...
if exist "requirements.txt" (
    pip install -r requirements.txt
) else (
    echo requirements.txt not found. Installing core packages only.
    pip install fastapi uvicorn aiohttp lxml aiosqlite
)

echo.
echo Installation complete. You can now run run_windows.bat to start the server.
pause