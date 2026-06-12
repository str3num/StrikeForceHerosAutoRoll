@echo off
cd /d "%~dp0"

echo ================================================
echo   Gacha Bot - Windows Launcher
echo ================================================

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Install: https://www.python.org/downloads/
    pause
    exit /b 1
)
python --version

:: Install dependencies
echo.
echo [1/2] Installing dependencies...
python -m pip install --upgrade pip -q
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)

:: Quick verify
echo.
python -c "import cv2; print('cv2 OK')" 2>nul
if %errorlevel% neq 0 (
    echo [WARN] cv2 import failed, retrying install...
    python -m pip install opencv-python --force-reinstall
)

:: Launch
echo.
echo [2/2] Starting bot...
echo Controls: F6=Start  F7=Stop  F8=Exit
echo.
python main.py run
pause
