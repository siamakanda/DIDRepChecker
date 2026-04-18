@echo off
cd ..

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
echo Starting FastAPI server on http://localhost:8000
echo API docs available at http://localhost:8000/docs
echo Press Ctrl+C to stop the server.
echo.

REM Run Uvicorn (reload enabled for development)
uvicorn server.api_server:app --host 0.0.0.0 --port 8000 --reload

pause