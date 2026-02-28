@echo off
chcp 65001 >nul
title YueXia - Services
cd /d "%~dp0"

call conda activate yuexia
if errorlevel 1 (
    echo [YueXia] 错误：无法激活 conda 环境 yuexia
    pause
    exit /b 1
)

python launcher.py
pause
