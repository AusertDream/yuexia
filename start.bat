@echo off
chcp 65001 >nul
title YueXia AI

if not exist "data\screenshots" mkdir "data\screenshots"
if not exist "data\tts_output" mkdir "data\tts_output"
if not exist "data\diary" mkdir "data\diary"
if not exist "data\chromadb" mkdir "data\chromadb"

set "SOVITS_DIR=%~dp0GPT-SoVITS-v2-240821"
set "PATH=%SOVITS_DIR%;%PATH%"
echo Starting GPT-SoVITS TTS...
start "TTS" /D "%SOVITS_DIR%" runtime\python.exe api_v2.py -a 127.0.0.1 -p 9880 -c GPT_SoVITS/configs/tts_infer.yaml

timeout /t 5 /nobreak >nul

call D:\Anaconda\Scripts\activate.bat yuexia
python main.py
taskkill /fi "WINDOWTITLE eq TTS" /f >nul 2>&1
