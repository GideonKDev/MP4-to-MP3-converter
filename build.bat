@echo off
chcp 65001 > nul
title MP4 to MP3 Converter - EXE Builder
color 0A

echo ========================================
echo   MP4 to MP3 Converter - EXE Builder
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  Python not found!
    echo Please install Python 3.8+ from python.org
    pause
    exit /b 1
)

REM Create virtual environment
echo Creating virtual environment...
python -m venv venv
call venv\Scripts\activate.bat

REM Install requirements
echo Installing requirements...
pip install --upgrade pip
pip install -r requirements.txt

REM Ask for build method
echo.
echo Select build method:
echo 1. PyInstaller (recommended)
echo 2. Nuitka (faster, smaller)
echo 3. Both
echo.

set /p choice="Enter choice (1-3): "

if "%choice%"=="1" (
    echo Building with PyInstaller...
    python build_exe.py
) else if "%choice%"=="2" (
    echo Building with Nuitka...
    python build_nuitka.py
) else if "%choice%"=="3" (
    echo Building with both methods...
    python build_exe.py
    echo.
    echo ========================================
    echo.
    python build_nuitka.py
) else (
    echo Invalid choice
)

REM Open dist folder
if exist "dist\" (
    echo.
    echo Opening dist folder...
    start "" "dist\"
)

pause