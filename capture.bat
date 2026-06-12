@echo off
cd /d "%~dp0"

if "%1"=="" (
    echo Usage: capture.bat ^<template_name^>
    echo Example: capture.bat roll.png
    pause
    exit /b 1
)

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found
    pause
    exit /b 1
)

pip install -r requirements.txt -q
python main.py capture %*
pause
