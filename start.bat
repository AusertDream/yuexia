@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title YueXia - Services
cd /d "%~dp0"

if not exist "data\screenshots" mkdir "data\screenshots"
if not exist "data\tts_output" mkdir "data\tts_output"
if not exist "data\diary" mkdir "data\diary"
if not exist "data\chromadb" mkdir "data\chromadb"
if not exist "logs" mkdir "logs"

for /f %%i in ('powershell -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "TS=%%i"
mkdir "logs\%TS%"
for /f "skip=5 delims=" %%d in ('dir /b /ad /o-n logs') do rd /s /q "logs\%%d"

for /f "tokens=2 delims=: " %%a in ('findstr "tts_port" config\config.yaml') do set TTS_PORT=%%a
for /f "tokens=2 delims=: " %%a in ('findstr "backend_port" config\config.yaml') do set BACKEND_PORT=%%a
for /f "tokens=2 delims=: " %%a in ('findstr "frontend_port" config\config.yaml') do set FRONTEND_PORT=%%a

set "ROOT=%cd%\"
set "SOVITS_DIR=%cd%\GPT-SoVITS-v2-240821"

set "TTS_PID="
set "BACKEND_PID="
set "FRONTEND_PID="

echo [YueXia] Starting TTS service (port %TTS_PORT%)...
start "" /B cmd /c "cd /d %SOVITS_DIR% && runtime\python.exe api_v2.py -a 127.0.0.1 -p %TTS_PORT% -c GPT_SoVITS/configs/tts_infer.yaml >%ROOT%logs\%TS%\tts.log 2>&1"
timeout /t 5 /nobreak >nul

echo [YueXia] Starting Backend service (port %BACKEND_PORT%)...
set "YUEXIA_ROOT=%ROOT%"
set "PYTHONIOENCODING=utf-8"
start "" /B cmd /c "cd /d %ROOT% && conda run -n yuexia python -m src.backend.app >%ROOT%logs\%TS%\backend.log 2>&1"

echo [YueXia] Starting Frontend service (port %FRONTEND_PORT%)...
set "VITE_BACKEND_PORT=%BACKEND_PORT%"
set "VITE_FRONTEND_PORT=%FRONTEND_PORT%"
start "" /B cmd /c "cd /d %ROOT%src\frontend && npm run dev >%ROOT%logs\%TS%\frontend.log 2>&1"

echo.
echo [YueXia] Waiting for frontend...

set RETRY=0
:wait_frontend
if !RETRY! GEQ 30 (
    echo [YueXia] ERROR: Frontend failed to start within 60s.
    goto shutdown
)
set /a RETRY+=1
timeout /t 2 /nobreak >nul
powershell -Command "try{(Invoke-WebRequest http://localhost:%FRONTEND_PORT% -UseBasicParsing -TimeoutSec 2).StatusCode}catch{exit 1}" >nul 2>&1
if errorlevel 1 goto wait_frontend

echo [YueXia] Frontend ready! Opening browser...
start "" http://localhost:%FRONTEND_PORT%
for /f %%a in ('powershell -NoProfile -Command "(Get-CimInstance Win32_Process | Where-Object {$_.CommandLine -like '*vite*'} | Select-Object -First 1).ProcessId"') do set "FRONTEND_PID=%%a"

for /f %%a in ('powershell -NoProfile -Command "(Get-CimInstance Win32_Process | Where-Object {$_.CommandLine -like '*src.backend.app*'} | Select-Object -First 1).ProcessId"') do set "BACKEND_PID=%%a"

for /f %%a in ('powershell -NoProfile -Command "(Get-CimInstance Win32_Process | Where-Object {$_.CommandLine -like '*api_v2.py*'} | Select-Object -First 1).ProcessId"') do set "TTS_PID=%%a"

:menu
echo.
echo ============================================
echo   [YueXia] All services running!
echo ============================================
echo   1. Open browser
echo   2. Exit (close all services)
echo ============================================
set /p "CHOICE=  Enter choice: "
if "!CHOICE!"=="1" (
    start "" http://localhost:%FRONTEND_PORT%
    goto menu
)
if "!CHOICE!"=="2" goto shutdown
echo   [!!] Invalid choice.
goto menu

:shutdown
echo.
echo [YueXia] Stopping services...

set KILLED=0

call :kill_service "TTS" "api_v2.py" "%TTS_PORT%" "!TTS_PID!"
call :kill_service "Backend" "src.backend.app" "%BACKEND_PORT%" "!BACKEND_PID!"
call :kill_service "Frontend" "vite" "%FRONTEND_PORT%" "!FRONTEND_PID!"

echo.
echo [YueXia] All services stopped. Goodbye!
exit /b

:kill_service
set "SVC_NAME=%~1"
set "SVC_KEYWORD=%~2"
set "SVC_PORT=%~3"
set "SVC_CACHED_PID=%~4"

if "!SVC_KEYWORD!"=="" (
    echo   [--] !SVC_NAME!: keyword empty, skipped
    goto :eof
)
if "!SVC_PORT!"=="" (
    echo   [--] !SVC_NAME!: port empty, skipped
    goto :eof
)

netstat -ano | findstr ":!SVC_PORT! " >nul 2>&1
if errorlevel 1 (
    echo   [--] !SVC_NAME! port !SVC_PORT! not in use, service not running
    goto :eof
)

set "NAME_PIDS="
for /f %%a in ('powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object {$_.CommandLine -like '*!SVC_KEYWORD!*'} | ForEach-Object {$_.ProcessId}"') do (
    set "NAME_PIDS=!NAME_PIDS! %%a"
)

set "PORT_PIDS="
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%SVC_PORT% "') do (
    set "_P=%%a"
    if not "!_P!"=="0" (
        set "PORT_PIDS=!PORT_PIDS! !_P!"
    )
)

set "KILL_COUNT=0"
set "KILLED_PIDS="
for %%n in (!NAME_PIDS!) do (
    for %%p in (!PORT_PIDS!) do (
        if "%%n"=="%%p" (
            echo !KILLED_PIDS! | findstr /C:" %%n " >nul 2>&1 || (
                set /a KILL_COUNT+=1
                if !KILL_COUNT! GTR 4 (
                    echo   [!!] !SVC_NAME!: too many PIDs, aborting
                    goto :eof
                )
                taskkill /F /T /PID %%n >nul 2>&1
                echo   [OK] !SVC_NAME! stopped ^(PID %%n^)
                set "KILLED_PIDS=!KILLED_PIDS! %%n "
            )
        )
    )
)

if "!KILL_COUNT!"=="0" (
    if not "!SVC_CACHED_PID!"=="" (
        taskkill /F /T /PID !SVC_CACHED_PID! >nul 2>&1 && (
            echo   [OK] !SVC_NAME! stopped via cached PID !SVC_CACHED_PID!
        ) || (
            echo   [--] !SVC_NAME!: no intersection found, cached PID !SVC_CACHED_PID! also invalid
        )
    ) else (
        echo   [--] !SVC_NAME!: no intersection found, no cached PID available
    )
)
goto :eof
