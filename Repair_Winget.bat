@echo off
title Manual Dependencies Installer
color 0b

echo ========================================
echo   Manual Dependency Installer (No Winget)
echo ========================================
echo.
echo [INFO] This script will manually download and install Python 3.11 and FFmpeg.
echo [INFO] Use this ONLY if normal start.bat failed to install them via winget.
echo.

:: -------------------------
:: 1. PYTHON INSTALLATION
:: -------------------------
python --version >nul 2>&1
IF %ERRORLEVEL% EQU 0 GOTO PYTHON_OK
py --version >nul 2>&1
IF %ERRORLEVEL% EQU 0 GOTO PYTHON_OK

echo [SETUP] Python is missing. Downloading Python installer...
powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Write-Host 'Downloading Python 3.11...'; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.8/python-3.11.8-amd64.exe' -OutFile 'python_installer.exe'"
if exist python_installer.exe (
    echo [SETUP] Running Python installer silently (this may take a minute)...
    start /wait python_installer.exe /quiet InstallAllUsers=0 PrependPath=1 Include_test=0
    del python_installer.exe
    echo [SUCCESS] Python installation complete!
) ELSE (
    echo [ERROR] Failed to download Python script. Try manually at python.org.
)
GOTO CHECK_FFMPEG

:PYTHON_OK
echo [SUCCESS] Python is already installed!

:: -------------------------
:: 2. FFMPEG INSTALLATION
:: -------------------------
:CHECK_FFMPEG
echo.
ffmpeg -version >nul 2>&1
IF %ERRORLEVEL% EQU 0 GOTO FFMPEG_OK

echo [SETUP] FFmpeg is missing. Downloading FFmpeg from GitHub...
powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Write-Host 'Downloading FFmpeg ZIP...'; Invoke-WebRequest -Uri 'https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip' -OutFile 'ffmpeg.zip'"
if exist ffmpeg.zip (
    echo [SETUP] Extracting FFmpeg...
    powershell -Command "Expand-Archive -Path 'ffmpeg.zip' -DestinationPath 'ffmpeg_temp' -Force"
    for /d %%D in (ffmpeg_temp\ffmpeg-*) do (
        xcopy /Y /F "%%D\bin\ffmpeg.exe" .\ >nul 2>&1
        xcopy /Y /F "%%D\bin\ffprobe.exe" .\ >nul 2>&1
    )
    rmdir /S /Q ffmpeg_temp
    del /F /Q ffmpeg.zip
    echo [SUCCESS] FFmpeg extraction complete!
) ELSE (
    echo [ERROR] Failed to download FFmpeg.
)
GOTO DONE

:FFMPEG_OK
echo [SUCCESS] FFmpeg is already installed!

:DONE
echo.
echo ========================================
echo   Installation check complete!
echo   You can now close this window and double-click "start.bat" as usual.
echo ========================================
pause
exit
