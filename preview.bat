@echo off
cd /d "%~dp0"

echo ================================================
echo   Gacha Bot - Preview Mode (no clicking)
echo ================================================

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found
    pause
    exit /b 1
)

pip install -r requirements.txt -q
python main.py preview
pause
