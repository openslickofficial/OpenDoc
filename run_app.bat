@echo off
title Snapdragon Document Assistant
echo ======================================================================
echo   Launching Snapdragon Document Assistant...
echo ======================================================================

REM Check if virtual environment exists and activate
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
)

REM Enforce 100% offline mode
set HF_HUB_OFFLINE=1
set TRANSFORMERS_OFFLINE=1

REM Run the application
python scripts\run_app.py

if errorlevel 1 (
    echo.
    echo [ERROR] Application exited with an error.
    pause
)
