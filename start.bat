@echo off
title Start MusicBot By VeloxGG
color 0a

echo ========================================
echo       MusicBot Setup and Run Script     
echo ========================================
echo.

:: [บัคที่ 1] Check if Python is installed (รองรับทั้งคำสั่ง python และ py)
set "PYTHON_CMD=python"
python --version >nul 2>&1
IF %ERRORLEVEL% EQU 0 GOTO PYTHON_INSTALLED

py --version >nul 2>&1
IF %ERRORLEVEL% EQU 0 (
    set "PYTHON_CMD=py"
    GOTO PYTHON_INSTALLED
)

:: [บัคที่ 2] ออโต้ติดตั้งแต่ Python รุ่นเสถียร (3.11) หากไม่มีในเครื่อง
echo [SETUP] It looks like Python is not installed yet. Don't worry!
winget --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo [ERROR] Your Windows is missing the 'Winget' Package Manager!
    echo [FIX] Please CLOSE this window, and run "Repair_Winget.bat" to fix your Windows first.
    pause
    exit /b
)

echo [SETUP] Initializing automatic Python installation using winget...
winget install -e --id Python.Python.3.11 --accept-package-agreements --accept-source-agreements

:: รีเช็คอีกรอบหลังจากติดตั้ง
python --version >nul 2>&1
IF %ERRORLEVEL% EQU 0 (
    set "PYTHON_CMD=python"
    GOTO PYTHON_INSTALLED
)

py --version >nul 2>&1
IF %ERRORLEVEL% EQU 0 (
    set "PYTHON_CMD=py"
    GOTO PYTHON_INSTALLED
)

echo [ERROR] Failed to find Python even after installation.
echo Please install Python manually from https://www.python.org/downloads/
echo **IMPORTANT**: Make sure to check the box "Add Python to PATH" during installation.
pause
exit /b

:PYTHON_INSTALLED
echo [INFO] Python is installed and ready.

:: [บัคที่ 3] ตรวจสอบและออโต้ติดตั้ง FFmpeg ที่มักจะทำให้บอทเสียงไม่ออก
ffmpeg -version >nul 2>&1
IF %ERRORLEVEL% EQU 0 GOTO FFMPEG_INSTALLED

echo [SETUP] FFmpeg is missing. It is required for playing audio.
winget --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo [ERROR] Your Windows is missing the 'Winget' Package Manager!
    echo [FIX] Please CLOSE this window, and run "Repair_Winget.bat" to fix your Windows first.
    pause
    exit /b
)

echo [SETUP] Installing FFmpeg via winget...
winget install -e --id Gyan.FFmpeg --accept-package-agreements --accept-source-agreements

ffmpeg -version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo ----------------------------------------------------
    echo [ERROR] Failed to install FFmpeg! (Winget not found)
    echo [FIX] Please CLOSE this window, and run "Repair_Winget.bat" instead!
    echo ----------------------------------------------------
    pause
    exit /b
)

echo [SUCCESS] FFmpeg has been installed successfully!
echo [IMPORTANT] Your system needs to refresh its settings.
echo Please CLOSE this window and double-click start.bat again to continue!
pause
exit /b

:FFMPEG_INSTALLED
echo [INFO] FFmpeg is installed.

:: [บัคที่ 4] ระบบ Auto-Update (อิงจาก Latest Release ใน GitHub)
if exist update.zip del /f /q update.zip >nul 2>&1
powershell -Command "$release = Invoke-RestMethod -Uri 'https://api.github.com/repos/devwangu/DiscordMusician/releases/latest' -ErrorAction SilentlyContinue; if ($null -eq $release) { Write-Host '[UPDATE] Could not check for release updates.'; exit 0 }; $latest = $release.tag_name; $configPath = 'config.json'; $current = 'none'; if (Test-Path $configPath) { $config = Get-Content $configPath -Raw | ConvertFrom-Json; if ($config.version) { $current = $config.version } }; Write-Host ('[UPDATE] Current Version: ' + $current + ' - Latest Release: ' + $latest); if ($latest -ne $current -and $latest -ne $null) { Write-Host '[UPDATE] Downloading latest release update...'; $zipUrl = 'https://github.com/devwangu/DiscordMusician/archive/refs/tags/' + $latest + '.zip'; Invoke-WebRequest -Uri $zipUrl -OutFile 'update.zip'; if (-not (Test-Path $configPath)) { $config = @{} } else { $config = Get-Content $configPath -Raw | ConvertFrom-Json }; $config | Add-Member -Type NoteProperty -Name 'version' -Value $latest -Force; $config | ConvertTo-Json | Set-Content $configPath } else { Write-Host '[UPDATE] You are already running the latest version! Skipping update.' }"
IF EXIST update.zip (
    echo [UPDATE] Extracting new release files...
    powershell -Command "Expand-Archive -Path 'update.zip' -DestinationPath 'update_temp' -Force" >nul 2>&1
    
    echo [UPDATE] Installing release updates...
    :: [บัคที่ 5] ระบบกันไฟล์เขียนทับตัวเอง (Self-Overwrite) จนพัง
    echo start.bat > exclude.txt
    echo test_*.bat >> exclude.txt
    
    :: รองรับการดึงไฟล์จาก ZIP แตกออกมาแบบครอบจักรวาล (ทั้ง Branch และ Tag)
    for /d %%D in (update_temp\DiscordMusician-*) do (
        xcopy /Y /E /H /C /I /EXCLUDE:exclude.txt "%%D\*" .\ >nul 2>&1
    )
    if exist exclude.txt del /f /q exclude.txt
    
    echo [UPDATE] Cleaning up temporary files...
    rmdir /S /Q update_temp
    del /F /Q update.zip
    echo [SUCCESS] UPDATE to latest release complete!
    set "JUST_UPDATED=1"
) ELSE (
    set "JUST_UPDATED=0"
)

echo.
:: [บัคที่ 6] ระบบ VENV (สภาพแวดล้อมจำลองแบบกล่องทราย กั้นไม่ให้ Lib ไปตีกับงานโปรเจกต์อื่นในคอมผู้ใช้)
IF EXIST "venv\Scripts\activate.bat" GOTO VENV_EXISTS

echo [SETUP] Creating your virtual environment (venv) for the first time...
%PYTHON_CMD% -m venv venv
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
IF "%JUST_UPDATED%"=="1" GOTO DO_UPDATE
GOTO CHECK_LIBS

:DO_UPDATE
.\venv\Scripts\python.exe -m pip install --upgrade pip >nul 2>&1
:: [บัคที่ 7] ซ่อน Log โหดๆ ของ PIP ไม่ให้ออกมารกหูรกตาพร้อมทำกงล้อ Spinner หมุนสวยๆ ให้ดูไม่งง
powershell -Command "$c = '|','/','-','\'; $i = 0; $p = Start-Process '.\venv\Scripts\python.exe' -ArgumentList '-m pip install -q -U -r requirement_lib.txt' -NoNewWindow -PassThru; while (-not $p.HasExited) { Write-Host -NoNewline \"`r[INFO] New update detected. Updating libraries... $($c[$i])  (this might take a minute)\"; $i++; if ($i -eq 4) { $i = 0 }; Start-Sleep -Milliseconds 100 }; Write-Host \"`r[INFO] New update detected. Updating libraries... Done!                                  \""
GOTO RUN_BOT

:CHECK_LIBS
:: [บัคที่ 8] ตรวจสอบว่า Lib หลักของโปรแกรมถูกลบหายไปไหม ถ้าหายจะออโต้โหลดกลับให้
.\venv\Scripts\python.exe -c "import discord, yt_dlp, customtkinter, nacl, davey" >nul 2>&1
IF ERRORLEVEL 1 (
    echo [INFO] Missing libraries detected. Installing...
    .\venv\Scripts\python.exe -m pip install --upgrade pip >nul 2>&1
    .\venv\Scripts\python.exe -m pip install -r requirement_lib.txt
) ELSE (
    echo [INFO] All libraries are ready!
)

:RUN_BOT

:: Start the bot
echo.
echo ========================================
echo           Starting the Bot...           
echo ========================================

:: Give users 1.5 seconds to read the messages above before closing the window
powershell -Command "Start-Sleep -Seconds 1.5"

:: [บัคที่ 9] รัน Background Service ด้วย pythonw เพื่อกันหน้าจอดำค้างติ่งอยู่บน Desktop ทำให้แอบรันได้เนียนๆ
start "" ".\venv\Scripts\pythonw.exe" bot.py
exit
