@echo off
chcp 65001 > nul
title Setup Python Environment for MP4 to MP3 Converter
color 0A

echo ============================================
echo   Setting up Python Environment
echo ============================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% equ 0 (
    echo ✓ Python is installed
    python --version
) else (
    echo Python not found!
    echo.
    echo Installing Python 3.11...
    
    REM Download Python installer
    echo Downloading Python installer...
    powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe' -OutFile 'python_installer.exe'"
    
    if exist python_installer.exe (
        echo Installing Python...
        start /wait python_installer.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
        del python_installer.exe
        echo Python installed successfully
    ) else (
        echo Failed to download Python
        echo Please install manually from: https://python.org
        pause
        exit /b 1
    )
)

echo.
echo ============================================
echo   Installing Required Packages
echo ============================================
echo.

REM Update pip
python -m pip install --upgrade pip --quiet

REM Install PyInstaller and other requirements
echo Installing PyInstaller...
python -m pip install pyinstaller --quiet

echo Installing PyQt6...
python -m pip install PyQt6 --quiet

echo Installing moviepy...
python -m pip install moviepy --quiet

echo Installing mutagen...
python -m pip install mutagen --quiet

echo Installing pillow for icon creation...
python -m pip install pillow --quiet

echo.
echo  All packages installed successfully!
echo.
echo ============================================
echo   Environment Setup Complete!
echo ============================================
echo.
echo Next steps:
echo 1. Make sure your main Python file is named 'main.py'
echo 2. Run 'build_exe.bat' to create the EXE
echo 3. The EXE will be in the 'dist' folder
echo.
pause