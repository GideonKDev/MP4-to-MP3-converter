@echo off
chcp 65001 > nul
title Build MP4 to MP3 Converter EXE
color 0B

echo ============================================
echo   MP4 to MP3 Converter - EXE Builder
echo ============================================
echo.

REM Set variables
set "SCRIPT_DIR=%~dp0"
set "DIST_DIR=%SCRIPT_DIR%dist"
set "BUILD_DIR=%SCRIPT_DIR%build"
set "SPEC_DIR=%SCRIPT_DIR%"

REM Check for main.py
if not exist "main.py" (
    echo ❌ ERROR: main.py not found!
    echo.
    echo Please make sure your main Python file is named 'main.py'
    echo or rename your file to main.py
    echo.
    dir *.py
    echo.
    pause
    exit /b 1
)

echo ✓ Found main.py
echo.

REM Check for PyInstaller
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo ❌ PyInstaller not installed!
    echo.
    echo Run setup_environment.bat first
    echo or install manually: pip install pyinstaller
    echo.
    pause
    exit /b 1
)

echo ✓ PyInstaller is installed
echo.

REM Check for icon
if exist "icon.ico" (
    echo ✓ Using icon.ico
    set "ICON_OPTION=--icon=icon.ico"
) else (
    echo ℹ No icon.ico found - creating default icon...
    
    REM Create default icon using Python
    python -c "
try:
    from PIL import Image, ImageDraw
    img = Image.new('RGBA', (256, 256), (74, 144, 226, 255))
    draw = ImageDraw.Draw(img)
    draw.polygon([(80, 70), (80, 186), (186, 128)], fill=(255, 255, 255, 255))
    img.save('icon.ico', format='ICO')
    print('Default icon created: icon.ico')
except ImportError:
    print('PIL not installed, skipping icon creation')
    "
    
    if exist "icon.ico" (
        set "ICON_OPTION=--icon=icon.ico"
        echo ✓ Default icon created
    ) else (
        set "ICON_OPTION="
        echo ℹ No icon will be used
    )
)
echo.

REM Clean previous builds
if exist "%DIST_DIR%" (
    echo Cleaning previous build...
    rmdir /s /q "%DIST_DIR%" 2>nul
)
if exist "%BUILD_DIR%" (
    rmdir /s /q "%BUILD_DIR%" 2>nul
)
if exist "*.spec" (
    del *.spec 2>nul
)

echo ============================================
echo   Building EXE File
echo ============================================
echo.
echo This may take 2-5 minutes...
echo Please wait...
echo.

REM Build EXE with PyInstaller
python -m PyInstaller ^
    --onefile ^
    --windowed ^
    --name "MP4toMP3" ^
    --clean ^
    --noconfirm ^
    %ICON_OPTION% ^
    --add-data ".";"." ^
    --hidden-import PyQt6 ^
    --hidden-import PyQt6.QtCore ^
    --hidden-import PyQt6.QtGui ^
    --hidden-import PyQt6.QtWidgets ^
    --hidden-import moviepy ^
    --hidden-import mutagen ^
    --hidden-import PIL ^
    --hidden-import numpy ^
    --hidden-import imageio ^
    --hidden-import imageio_ffmpeg ^
    --hidden-import cv2 ^
    main.py

REM Check if EXE was created
if exist "%DIST_DIR%\MP4toMP3.exe" (
    echo.
    echo ============================================
    echo   BUILD SUCCESSFUL!
    echo ============================================
    echo.
    
    REM Get EXE size
    for %%F in ("%DIST_DIR%\MP4toMP3.exe") do set "EXE_SIZE=%%~zF"
    set /a "EXE_SIZE_MB=%EXE_SIZE%/1048576"
    
    echo EXE Location: %DIST_DIR%\MP4toMP3.exe
    echo File Size: %EXE_SIZE_MB% MB
    echo.
    
    REM Create README file
    echo Creating README file...
    (
    echo # MP4 to MP3 Converter
    echo.
    echo ## Instructions
    echo 1. Double-click MP4toMP3.exe to run
    echo 2. Make sure FFmpeg is installed on your system
    echo 3. Drag and drop MP4 files to convert
    echo.
    echo ## FFmpeg Installation
    echo If you don't have FFmpeg:
    echo 1. Download from: https://ffmpeg.org/download.html
    echo 2. Extract to C:\ffmpeg
    echo 3. Add C:\ffmpeg\bin to your PATH
    echo    - Right-click This PC ^> Properties ^> Advanced system settings
    echo    - Environment Variables ^> Edit PATH ^> Add C:\ffmpeg\bin
    echo.
    echo ## Troubleshooting
    echo - If EXE doesn't start: Install Visual C++ Redistributable
    echo - Download: https://aka.ms/vs/17/release/vc_redist.x64.exe
    ) > "%DIST_DIR%\README.txt"
    
    echo README created: %DIST_DIR%\README.txt
    echo.
    
    REM Create run script
    echo Creating run script...
    (
    echo @echo off
    echo chcp 65001 ^> nul
    echo echo MP4 to MP3 Converter
    echo echo ====================
    echo echo.
    echo echo Checking for FFmpeg...
    echo where ffmpeg ^>nul 2^>nul
    echo if errorlevel 1 (
    echo     echo ERROR: FFmpeg not found!
    echo     echo Please install FFmpeg from https://ffmpeg.org
    echo     echo.
    echo     pause
    echo     exit /b 1
    echo )
    echo echo ✓ FFmpeg is installed
    echo echo.
    echo echo Starting converter...
    echo echo.
    echo MP4toMP3.exe
    echo.
    echo if errorlevel 1 (
    echo     echo.
    echo     echo Application closed with error
    echo     pause
    echo )
    ) > "%DIST_DIR%\Run_Converter.bat"
    
    echo Run script created: %DIST_DIR%\Run_Converter.bat
    echo.
    
    REM Open dist folder
    echo Opening output folder...
    start "" "%DIST_DIR%"
    
    echo ============================================
    echo  DONE!
    echo ============================================
    echo.
    echo Your EXE is ready to use!
    echo Location: %DIST_DIR%
    echo.
    echo To distribute: Just share the MP4toMP3.exe file
    echo Users DO NOT need Python installed!
    echo.
    
) else (
    echo.
    echo ============================================
    echo   BUILD FAILED!
    echo ============================================
    echo.
    echo Possible issues:
    echo 1. Missing Python dependencies
    echo 2. Syntax errors in main.py
    echo 3. PyInstaller installation issue
    echo.
    echo Try running: setup_environment.bat
    echo Then try again.
)

echo.
pause