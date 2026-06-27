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

REM Read host/port from config or fall back to defaults
for /f "usebackq tokens=1,2 delims=:" %%a in (`python -c "from did_intel.config import get_config; c=get_config(); print(f\"{c.get('api_host','0.0.0.0')}:{c.get('api_port',8000)}\")"`) do (
    set API_HOST=%%a
    set API_PORT=%%b
)
if "%API_HOST%"=="" set API_HOST=0.0.0.0
if "%API_PORT%"=="" set API_PORT=8000

echo.
echo =======================================
echo   DID Intel API Server
echo =======================================
echo.
echo Starting FastAPI server on http://%API_HOST%:%API_PORT%
echo API docs available at http://%API_HOST%:%API_PORT%/docs
echo Press Ctrl+C to stop the server.
echo.

REM Use didintel-server (reads config for host/port)
didintel-server

pause