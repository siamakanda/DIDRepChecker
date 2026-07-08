@echo off
echo Building DIDRepChecker...
echo.

cd /d "%~dp0..\.."

REM Install build dependencies
pip install pyinstaller pystray pillow -q

REM Clean previous build
rmdir /s /q dist 2>nul
rmdir /s /q build 2>nul

REM Build
pyinstaller deploy\windows\pyinstaller.spec --noconfirm --clean

if exist "dist\DIDRepChecker.exe" (
    echo.
    echo Build successful!
    echo Output: dist\DIDRepChecker.exe (tray app)
    echo         dist\didrepchecker-server.exe (server)
) else (
    echo.
    echo Build FAILED - check errors above.
)

pause
