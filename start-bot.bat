@echo off
REM Start Aurelm bot with production database
REM Usage: start-bot.bat [port]

setlocal enabledelayedexpansion

set DB=pipeline\aurelm_v22_2_2.db
set PORT=8473

if not "%1"=="" set PORT=%1

echo Starting Aurelm bot with database: %DB%
echo Port: %PORT%
echo.

py -3.12 -m bot --db %DB% --port %PORT%

if errorlevel 1 (
    echo.
    echo Bot failed to start. Check the database path and make sure port is available.
    pause
)
