@echo off
REM Start Aurelm — bot + Flutter app
REM Usage: start-all.bat [db_path]

set DB=pipeline\aurelm_v22_2_2.db
set PORT=8473
set EXE=gui\build\windows\x64\runner\Release\aurelm_gui.exe

if not "%1"=="" set DB=%1

if not exist "%DB%" (
    echo ERROR: Database not found: %DB%
    pause
    exit /b 1
)

if not exist "%EXE%" (
    echo ERROR: App not built. Run: cd gui ^&^& flutter build windows
    pause
    exit /b 1
)

echo Starting bot with %DB%...
start "Aurelm Bot" py -3.12 -m bot --db %DB% --port %PORT%

echo Waiting for bot to start...
timeout /t 4 /nobreak >nul

echo Starting Flutter app...
start "" "%EXE%"

echo Done.
