@echo off
:: Voice Typing - Install to Windows Startup
:: Run this script as Administrator to add Voice Typing to Windows startup

echo ================================================
echo  Voice Typing - Startup Installation
echo ================================================
echo.

:: Get the directory of this script
set "APP_DIR=%~dp0"
set "VBS_PATH=%APP_DIR%VoiceTyping_Hidden.vbs"
set "TASK_NAME=VoiceTyping"

:: Check if VBS file exists
if not exist "%VBS_PATH%" (
    echo ERROR: VoiceTyping_Hidden.vbs not found!
    echo Please run this script from the VoiceTyping folder.
    pause
    exit /b 1
)

echo Choose installation method:
echo.
echo   1. Startup Folder (Recommended - Simple, runs at login)
echo   2. Task Scheduler (Advanced - runs at system startup)
echo   3. Remove from startup
echo   4. Cancel
echo.
set /p CHOICE="Enter choice (1-4): "

if "%CHOICE%"=="1" goto :STARTUP_FOLDER
if "%CHOICE%"=="2" goto :TASK_SCHEDULER
if "%CHOICE%"=="3" goto :REMOVE
if "%CHOICE%"=="4" goto :END
echo Invalid choice!
pause
exit /b 1

:STARTUP_FOLDER
echo.
echo Installing to Startup folder...

:: Get Startup folder path
set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"

:: Create shortcut using PowerShell
powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%STARTUP_FOLDER%\VoiceTyping.lnk'); $s.TargetPath = '%VBS_PATH%'; $s.WorkingDirectory = '%APP_DIR%'; $s.Description = 'Voice Typing - System-wide voice dictation'; $s.Save()"

if errorlevel 1 (
    echo ERROR: Failed to create shortcut!
    pause
    exit /b 1
)

echo.
echo SUCCESS! Voice Typing will start automatically when you log in.
echo.
echo Shortcut created at:
echo   %STARTUP_FOLDER%\VoiceTyping.lnk
echo.
echo To remove: Run this script again and choose option 3.
pause
goto :END

:TASK_SCHEDULER
echo.
echo Installing via Task Scheduler...
echo (This may require Administrator privileges)
echo.

:: Create the scheduled task
schtasks /create /tn "%TASK_NAME%" /tr "wscript.exe \"%VBS_PATH%\"" /sc onlogon /rl highest /f

if errorlevel 1 (
    echo.
    echo ERROR: Failed to create scheduled task!
    echo Try running this script as Administrator.
    pause
    exit /b 1
)

echo.
echo SUCCESS! Voice Typing will start automatically at login.
echo.
echo To remove: Run this script again and choose option 3.
echo Or use Task Scheduler and delete the "VoiceTyping" task.
pause
goto :END

:REMOVE
echo.
echo Removing Voice Typing from startup...

:: Remove from Startup folder
set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
if exist "%STARTUP_FOLDER%\VoiceTyping.lnk" (
    del "%STARTUP_FOLDER%\VoiceTyping.lnk"
    echo Removed from Startup folder.
)

:: Remove from Task Scheduler
schtasks /query /tn "%TASK_NAME%" >nul 2>&1
if not errorlevel 1 (
    schtasks /delete /tn "%TASK_NAME%" /f
    echo Removed from Task Scheduler.
)

echo.
echo Voice Typing removed from startup.
pause
goto :END

:END
echo.
echo Done!
