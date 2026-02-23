@echo off
cd /d %~dp0\..
echo [YueXia] Installing backend dependencies...
call conda activate yuexia
pip install -r src\backend\requirements.txt
echo [YueXia] Installing frontend dependencies...
cd src\frontend && npm install
echo [YueXia] Done.
pause
