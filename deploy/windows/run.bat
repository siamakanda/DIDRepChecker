@echo off
REM Run from the project root (parent of deploy/windows)
cd /d "%~dp0..\.."

REM Check if virtual environment exists
if not exist "venv" (
    echo Virtual environment not found. Please run deploy\windows\install.ps1 first.
    pause
    exit /b 1
)

REM Activate virtual environment
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo Failed to activate virtual environment.
    pause
    exit /b 1
)

echo.
echo =======================================
echo   DID Intel API Server
echo =======================================
echo.
echo Starting FastAPI server on http://localhost:8000
echo API docs available at http://localhost:8000/docs
echo Press Ctrl+C to stop the server.
echo.

REM Run Uvicorn in production mode (no --reload)
uvicorn did_intel.api:app --host 0.0.0.0 --port 8000

pause