@echo off
cd /d "%~dp0"
echo ================================================
echo   Build Script
echo ================================================

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found
    pause
    exit /b 1
)

echo [1/4] Installing PyInstaller...
python -m pip install pyinstaller -q
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install PyInstaller
    pause
    exit /b 1
)

echo [2/4] Cleaning old build...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build

echo [3/4] Building package...
python -m PyInstaller ^
    --onedir ^
    --console ^
    --name=GachaBot ^
    --add-data "templates;templates" ^
    --add-data "config.py;." ^
    --hidden-import=cv2 ^
    --hidden-import=numpy ^
    --hidden-import=mss ^
    --hidden-import=pyautogui ^
    --hidden-import=PIL ^
    --collect-all pynput ^
    --collect-all mss ^
    main.py

if %errorlevel% neq 0 (
    echo [ERROR] Build failed
    pause
    exit /b 1
)

echo [4/4] Renaming and copying...
if exist "dist\ZhanHuo" rmdir /s /q "dist\ZhanHuo"
rename "dist\GachaBot" "ZhanHuo"
rename "dist\ZhanHuo\GachaBot.exe" "ZhanHuo.exe"

copy config.py "dist\ZhanHuo\" /Y >nul
xcopy templates "dist\ZhanHuo\templates\" /Y /I /Q >nul
if exist positions.json copy positions.json "dist\ZhanHuo\" /Y >nul

echo.
echo ================================================
echo   Build complete!
echo   Output: dist\ZhanHuo\
echo   EXE: ZhanHuo.exe
echo ================================================
echo   Usage:
echo     ZhanHuo.exe run
echo     ZhanHuo.exe preview
pause
