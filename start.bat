@echo off
title Start MusicBot By VeloxGG
color 0a

echo ========================================
echo       MusicBot Setup and Run Script     
echo ========================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
IF %ERRORLEVEL% EQU 0 GOTO PYTHON_INSTALLED

echo [SETUP] It looks like Python is not installed yet. Don't worry!
echo [SETUP] Initializing automatic Python installation using winget...
winget install -e --id Python.Python.3.11 --accept-package-agreements --accept-source-agreements

:: Refreshing Environment Variables in Batch is tricky, so we check using the Windows Python Launcher ('py') instead, 
:: or simply tell the user to restart the file.
py --version >nul 2>&1
IF %ERRORLEVEL% EQU 0 GOTO PYTHON_NEWLY_INSTALLED

echo [ERROR] Failed to find Python even after installation.
echo Please install Python manually from https://www.python.org/downloads/
echo **IMPORTANT**: Make sure to check the box "Add Python to PATH" during installation.
pause
exit /b

:PYTHON_NEWLY_INSTALLED
echo [SUCCESS] Python has been installed successfully!
echo [IMPORTANT] Your system needs to refresh its settings.
echo Please CLOSE this window and double-click start.bat again to continue!
pause
exit /b

:PYTHON_INSTALLED
echo [INFO] Python is installed.

:: Check if FFmpeg is installed
ffmpeg -version >nul 2>&1
IF %ERRORLEVEL% EQU 0 GOTO FFMPEG_INSTALLED

echo [SETUP] FFmpeg is missing. It is required for playing audio.
echo [SETUP] Installing FFmpeg via winget...
winget install -e --id Gyan.FFmpeg --accept-package-agreements --accept-source-agreements

echo [SUCCESS] FFmpeg has been installed successfully!
echo [IMPORTANT] Your system needs to refresh its settings.
echo Please CLOSE this window and double-click start.bat again to continue!
pause
exit /b

:FFMPEG_INSTALLED
echo [INFO] FFmpeg is installed.

:: Auto-Update System (Latest Release)
echo [UPDATE] Checking for the latest stable release from GitHub...
if exist update.zip del /f /q update.zip >nul 2>&1
powershell -Command "$release = Invoke-RestMethod -Uri 'https://api.github.com/repos/devwangu/DiscordMusician/releases/latest' -ErrorAction SilentlyContinue; if ($null -eq $release) { exit 0 }; $latest = $release.tag_name; $configPath = 'config.json'; $current = 'none'; if (Test-Path $configPath) { $config = Get-Content $configPath -Raw | ConvertFrom-Json; if ($config.version) { $current = $config.version } }; if ($latest -ne $current -and $latest -ne $null) { Invoke-WebRequest -Uri $release.zipball_url -OutFile 'update.zip'; if (-not (Test-Path $configPath)) { $config = @{} } else { $config = Get-Content $configPath -Raw | ConvertFrom-Json }; $config | Add-Member -Type NoteProperty -Name 'version' -Value $latest -Force; $config | ConvertTo-Json | Set-Content $configPath }" >nul 2>&1
IF EXIST update.zip (
    echo [UPDATE] Extracting new files...
    powershell -Command "Expand-Archive -Path 'update.zip' -DestinationPath 'update_temp' -Force" >nul 2>&1
    
    echo [UPDATE] Installing updates...
    :: GitHub APIs extract into a folder named RepoName-VersionHash (e.g. devwangu-DiscordMusician-xxxxx)
    :: We use a wildcard to enter that single dynamically named folder
    for /d %%D in (update_temp\devwangu-DiscordMusician-*) do (
        xcopy /Y /E /H /C /I "%%D\*" .\ >nul 2>&1
    )
    
    echo [UPDATE] Cleaning up temporary files...
    rmdir /S /Q update_temp
    del /F /Q update.zip
    echo [SUCCESS] Update complete!
    set "JUST_UPDATED=1"
) ELSE (
    echo [UPDATE] Failed to download update or no release found. Skipping...
    set "JUST_UPDATED=0"
)

echo.
:: Create virtual environment if it doesn't exist
IF EXIST "venv\Scripts\activate.bat" GOTO VENV_EXISTS

echo [SETUP] Creating your virtual environment (venv) for the first time...
python -m venv venv
IF %ERRORLEVEL% EQU 0 GOTO VENV_CREATED

echo [ERROR] Failed to create virtual environment. Please check your system settings.
pause
exit /b

:VENV_CREATED
echo [SUCCESS] Virtual environment created.

:VENV_EXISTS
:: Activate the virtual environment
echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat

:: Install requirements
IF "%JUST_UPDATED%"=="1" (
    echo [INFO] New update detected. Updating libraries...(this might take a minute)...
    python -m pip install --upgrade pip >nul 2>&1
    pip install -U -r requirement_lib.txt
) ELSE (
    python -c "import discord, yt_dlp, customtkinter, nacl, davey" >nul 2>&1
    IF ERRORLEVEL 1 (
        echo [INFO] Missing libraries detected. Installing...
        python -m pip install --upgrade pip >nul 2>&1
        pip install -r requirement_lib.txt
    ) ELSE (
        echo [INFO] All libraries are ready!
    )
)

:: Start the bot
echo.
echo ========================================
echo           Starting the Bot...           
echo ========================================

:: Use start and pythonw to run the bot without a console window, then close the terminal.
start "" pythonw bot.py
exit
