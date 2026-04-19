@echo off
cd /d "%~dp0.."

REM Check if virtual environment exists
if not exist "venv" (
    echo Virtual environment not found. Please run installer_windows.bat first.
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
echo Starting FastAPI server on http://localhost:8000
echo API docs available at http://localhost:8000/docs
echo Press Ctrl+C to stop the server.
echo.

REM Run Uvicorn (reload enabled for development)
uvicorn server.api_server:app --host 0.0.0.0 --port 8000 --reload

pause