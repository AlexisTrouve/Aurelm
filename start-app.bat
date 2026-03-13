@echo off
REM Start Aurelm Flutter app (prebuilt release)
REM Assumes bot is already running on port 8473

set EXE=gui\build\windows\x64\runner\Release\aurelm_gui.exe

if not exist "%EXE%" (
    echo ERROR: App not built yet. Run: cd gui && flutter build windows
    pause
    exit /b 1
)

echo Starting Aurelm...
start "" "%EXE%"
