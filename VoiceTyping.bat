@echo off
:: Voice Typing - Quick Start Launcher
:: Double-click this file to start the voice typing application

title Voice Typing
cd /d "%~dp0"

:: Check if Python is available
where python >nul 2>&1
if errorlevel 1 (
    echo Python not found! Please install Python 3.10+ and add to PATH.
    pause
    exit /b 1
)

:: Check for API key
if not defined GEMINI_API_KEY (
    echo.
    echo ================================================
    echo  GEMINI_API_KEY environment variable not set!
    echo ================================================
    echo.
    echo Please set your API key:
    echo   1. Open Windows Settings ^> System ^> About ^> Advanced system settings
    echo   2. Click "Environment Variables"
    echo   3. Add new User variable: GEMINI_API_KEY = your_api_key
    echo.
    echo Or run: setx GEMINI_API_KEY "your_api_key_here"
    echo.
    pause
    exit /b 1
)

echo Starting Voice Typing...
echo Press Win+H to toggle voice dictation.
echo.
python main.py

if errorlevel 1 (
    echo.
    echo Application exited with error. Check the logs above.
    pause
)
