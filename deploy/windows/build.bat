@echo off
echo Building DIDRepChecker...
echo.

REM Move to project root
cd /d "%~dp0..\.."

REM Check tools
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller -q
)

pip show pystray >nul 2>&1
if errorlevel 1 (
    echo Installing pystray + pillow...
    pip install pystray pillow -q
)

REM Clean previous build
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul

echo Running PyInstaller...
pyinstaller deploy\windows\pyinstaller.spec --noconfirm --clean

if exist "dist\DIDRepChecker.exe" (
    echo.
    echo =====================================
    echo   Build successful!
    echo =====================================
    echo   dist\DIDRepChecker.exe (tray app)
    echo   dist\didrepchecker-server.exe (server)
    echo.
) else (
    echo.
    echo Build FAILED - check errors above.
)

pause
