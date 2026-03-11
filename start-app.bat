@echo off
REM Start Aurelm Flutter app
REM Assumes bot is already running on port 8473

echo Starting Aurelm Flutter app...
echo Make sure bot is running first (see start-bot.bat)
echo.

cd gui
flutter run -d windows

if errorlevel 1 (
    echo.
    echo Flutter failed to start. Check that Flutter is installed and Windows platform is available.
    pause
)
