@echo off
setlocal enabledelayedexpansion

REM Move to project root (parent of deploy/windows)
cd /d "%~dp0..\.." 2>nul || (
    echo ERROR: Cannot find project root.
    pause
    exit /b 1
)

REM Check virtual environment
if not exist "venv\Scripts\python.exe" (
    echo Virtual environment not found. Run: deploy\windows\install.ps1
    pause
    exit /b 1
)

REM Activate
call venv\Scripts\activate.bat >nul 2>&1
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment.
    pause
    exit /b 1
)

echo.
echo  DIDRepChecker API Server
echo  http://localhost:8000
echo  Docs: http://localhost:8000/docs
echo  Press Ctrl+C to stop.
echo.

python -m uvicorn did_intel.api:app --host 0.0.0.0 --port 8000

if errorlevel 1 (
    echo.
    echo Server stopped with error.
    pause
)
