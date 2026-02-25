@echo off
cd /d "%~dp0\.."
echo [YueXia] Checking conda environment...
conda env list | findstr /C:"yuexia" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] conda environment 'yuexia' not found. Please create it first:
    echo   conda create -n yuexia python=3.10
    pause
    exit /b 1
)
echo [YueXia] Installing backend dependencies...
call conda activate yuexia
pip install -r src\backend\requirements.txt
echo [YueXia] Installing frontend dependencies...
cd src\frontend && npm install
echo [YueXia] Done.
pause
