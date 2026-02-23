@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title YueXia - Stop Services
cd /d "%~dp0"

echo [YueXia] Stopping services...
echo.

set KILLED=0

if not exist "config\pids.conf" (
    echo   [!!] PID file not found, skipping PID kill...
    goto :process_check
)

for /f "tokens=1,2 delims==" %%a in (config\pids.conf) do set %%a=%%b

if defined TTS_PID (
    taskkill /F /T /PID !TTS_PID! >nul 2>&1 && (echo   [OK] TTS stopped ^(PID !TTS_PID!^)& set /a KILLED+=1) || echo   [--] TTS PID !TTS_PID! not found
)
if defined BACKEND_PID (
    taskkill /F /T /PID !BACKEND_PID! >nul 2>&1 && (echo   [OK] Backend stopped ^(PID !BACKEND_PID!^)& set /a KILLED+=1) || echo   [--] Backend PID !BACKEND_PID! not found
)
if defined FRONTEND_PID (
    taskkill /F /T /PID !FRONTEND_PID! >nul 2>&1 && (echo   [OK] Frontend stopped ^(PID !FRONTEND_PID!^)& set /a KILLED+=1) || echo   [--] Frontend PID !FRONTEND_PID! not found
)

if !KILLED! GEQ 3 goto :cleanup

:process_check
echo.
echo [YueXia] Checking processes for remaining services...

set MATCH_COUNT=0
set "PIDS_TO_KILL="

for %%k in (api_v2.py src.backend.app vite) do (
    for /f "skip=1" %%p in ('wmic process where "commandline like '%%%%k%%'" get processid 2^>nul ^| findstr /r "[0-9]"') do for /f %%q in ("%%p") do (
        set /a MATCH_COUNT+=1
        set "PIDS_TO_KILL=!PIDS_TO_KILL! %%q"
    )
)

if !MATCH_COUNT! GTR 4 (
    echo   [!!] ERROR: Found !MATCH_COUNT! matching processes ^(exceeds safety limit of 4^). Aborting.
    goto :done
)

for %%p in (!PIDS_TO_KILL!) do (
    taskkill /F /T /PID %%p >nul 2>&1
    echo   [OK] Process PID %%p killed
)

:cleanup
if exist "config\pids.conf" del "config\pids.conf" >nul 2>&1
echo.
echo [YueXia] Done.

:done
pause
