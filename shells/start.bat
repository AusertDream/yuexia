@echo off
chcp 65001 >nul
cd /d "%~dp0.."

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

start "" /B cmd /c "cd /d %SOVITS_DIR% && runtime\python.exe api_v2.py -a 127.0.0.1 -p %TTS_PORT% -c GPT_SoVITS/configs/tts_infer.yaml >%ROOT%logs\%TS%\tts.log 2>&1"
timeout /t 5 /nobreak >nul

start "" /B cmd /c "cd /d %ROOT% && call conda activate yuexia && python -m src.backend.app >%ROOT%logs\%TS%\backend.log 2>&1"
start "" /B cmd /c "cd /d %ROOT%src\frontend && npm run dev >%ROOT%logs\%TS%\frontend.log 2>&1"

:wait_backend
timeout /t 2 /nobreak >nul
powershell -Command "try{(Invoke-WebRequest http://localhost:%BACKEND_PORT%/api/system/status -UseBasicParsing -TimeoutSec 2).StatusCode}catch{exit 1}" >nul 2>&1
if errorlevel 1 goto wait_backend

:wait_frontend
timeout /t 2 /nobreak >nul
powershell -Command "try{(Invoke-WebRequest http://localhost:%FRONTEND_PORT% -UseBasicParsing -TimeoutSec 2).StatusCode}catch{exit 1}" >nul 2>&1
if errorlevel 1 goto wait_frontend

(echo TTS_PORT=%TTS_PORT%
echo BACKEND_PORT=%BACKEND_PORT%
echo FRONTEND_PORT=%FRONTEND_PORT%) > config\pids.conf
for /f "skip=1" %%a in ('wmic process where "commandline like '%%api_v2.py%%'" get processid 2^>nul ^| findstr /r "[0-9]"') do for /f %%b in ("%%a") do echo TTS_PID=%%b>> config\pids.conf
for /f "skip=1" %%a in ('wmic process where "commandline like '%%src.backend.app%%'" get processid 2^>nul ^| findstr /r "[0-9]"') do for /f %%b in ("%%a") do echo BACKEND_PID=%%b>> config\pids.conf
for /f "skip=1" %%a in ('wmic process where "commandline like '%%vite%%'" get processid 2^>nul ^| findstr /r "[0-9]"') do for /f %%b in ("%%a") do echo FRONTEND_PID=%%b>> config\pids.conf

start "" http://localhost:%FRONTEND_PORT%
