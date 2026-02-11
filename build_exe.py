#!/usr/bin/env python3
"""
Build Windows EXE for MP4 to MP3 Converter
Save as: build_exe.py
"""

import os
import sys
import shutil
import subprocess
import tempfile
from pathlib import Path
import json
import argparse

class EXEBuilder:
    def __init__(self):
        self.project_dir = Path(__file__).parent
        self.build_dir = self.project_dir / "build"
        self.dist_dir = self.project_dir / "dist"
        self.spec_file = self.project_dir / "converter.spec"
        
    def check_dependencies(self):
        """Check if PyInstaller is installed"""
        try:
            import PyInstaller
            return True, "PyInstaller is installed"
        except ImportError:
            return False, "PyInstaller not installed. Run: pip install pyinstaller"
    
    def create_icon(self):
        """Create a default icon if none exists"""
        icon_path = self.project_dir / "icon.ico"
        
        if not icon_path.exists():
            print("Creating default icon...")
            print("Warning: No icon.ico found. Create one for better appearance.")
            return None
        return icon_path
    
    def create_version_info(self):
        """Create version info file for EXE"""
        version_info = {
            "version": "1.0.0",
            "product_name": "MP4 to MP3 Converter Pro",
            "company_name": "Audio Tools",
            "file_description": "Professional MP4 to MP3 Conversion Tool",
            "legal_copyright": "© 2024 MP4 to MP3 Converter. All rights reserved.",
            "original_filename": "MP4toMP3.exe",
            "internal_name": "MP4toMP3"
        }
        
        version_file = self.project_dir / "version_info.txt"
        with open(version_file, 'w') as f:
            json.dump(version_info, f, indent=2)
        
        return version_file
    
    def create_spec_file(self, main_script, icon_path=None):
        """Create PyInstaller spec file"""
        spec_content = f'''# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Block RT mode for Windows 10/11
block_cipher = None

# List of hidden imports (modules that PyInstaller might miss)
hiddenimports = [
    'PyQt6', 'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets',
    'moviepy', 'mutagen', 'numpy', 'PIL', 'PIL._imaging',
    'cv2', 'imageio', 'imageio_ffmpeg',
    'queue', 'threading', 'json', 'pathlib', 'subprocess',
    'sys', 'os', 'time', 'datetime', 'logging', 'tempfile',
    'shutil', 'hashlib', 'traceback', 'collections',
    'concurrent.futures', 'multiprocessing', 'multiprocessing.pool'
]

# Additional data files (icons, configs, etc.)
datas = []

# Add icon if exists
icon_path = {repr(str(icon_path)) if icon_path else None}

a = Analysis(
    ['{main_script}'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Console or Windowed application
console = False  # Set to True for console window, False for windowed app

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='MP4toMP3',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # Compress executable with UPX
    upx_exclude=[],
    runtime_tmpdir=None,
    console=console,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path,
)

# Optional: Create single EXE file
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='MP4toMP3'
)
'''
        
        with open(self.spec_file, 'w') as f:
            f.write(spec_content)
        
        print(f"Created spec file: {self.spec_file}")
        return self.spec_file
    
    def find_main_script(self):
        """Find the main Python script"""
        possible_files = [
            "main.py",
            "converter.py", 
            "mp4tomp3.py",
            "app.py",
            "gui.py"
        ]
        
        for file in possible_files:
            if (self.project_dir / file).exists():
                return self.project_dir / file
        
        # Ask user if not found
        while True:
            user_input = input("Enter the path to your main Python script: ").strip()
            if os.path.exists(user_input):
                return Path(user_input)
            print(f"File not found: {user_input}")
    
    def build_exe(self, main_script, onefile=True, debug=False):
        """Build the EXE using PyInstaller"""
        
        # Clean previous builds
        if self.build_dir.exists():
            shutil.rmtree(self.build_dir)
        if self.dist_dir.exists():
            shutil.rmtree(self.dist_dir)
        
        # Create icon
        icon_path = self.create_icon()
        
        # Build command
        cmd = [
            'pyinstaller',
            '--name', 'MP4toMP3',
            '--clean',
            '--noconfirm',
        ]
        
        if onefile:
            cmd.append('--onefile')
        
        if not debug:
            cmd.append('--noconsole')  # No console window for GUI apps
        
        if icon_path:
            cmd.extend(['--icon', str(icon_path)])
        
        # Add Windows-specific options
        cmd.extend([
            '--windowed',  # Windows GUI application
            '--uac-admin',  # Request admin privileges if needed
            '--add-data', '.;.',  # Include all files in directory
        ])
        
        # Hidden imports
        hidden_imports = [
            'PyQt6', 'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets',
            'moviepy', 'mutagen', 'numpy', 'PIL',
            'cv2', 'imageio', 'imageio_ffmpeg'
        ]
        
        for imp in hidden_imports:
            cmd.extend(['--hidden-import', imp])
        
        # Add the main script
        cmd.append(str(main_script))
        
        print(f"Building EXE with command:")
        print(' '.join(cmd))
        print("\nThis may take a few minutes...")
        
        # Run PyInstaller
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print("\nBuild successful!")
                
                exe_path = self.dist_dir / "MP4toMP3.exe"
                if exe_path.exists():
                    print(f"\nEXE created at: {exe_path}")
                    print(f"Size: {exe_path.stat().st_size / (1024*1024):.2f} MB")
                    
                    # Create README file
                    self.create_readme(exe_path)
                    
                    return True, str(exe_path)
                else:
                    return False, "EXE was not created (check build folder)"
            else:
                print(f"\n Build failed!")
                print(f"Error: {result.stderr}")
                return False, result.stderr
                
        except Exception as e:
            return False, str(e)
    
    def create_readme(self, exe_path):
        """Create a README file for the EXE"""
       # readme_content = f'''# MP4 to MP3 Converter - Windows Executable

## Application Details
- **File:** {exe_path.name}
- **Version:** 1.0.0
- **Platform:** Windows 10/11 (64-bit)
- **Size:** {exe_path.stat().st_size / (1024*1024):.2f} MB

## Requirements
- Windows 10 or 11 (64-bit recommended)
- FFmpeg must be installed on your system
- For optimal performance: 4GB RAM minimum

## Installation
1. Copy the EXE file to any folder
2. Ensure FFmpeg is installed and in PATH
3. Double-click to run

## FFmpeg Installation
If you don't have FFmpeg:

### Method 1: Using Chocolatey (Recommended)
```cmd
choco install ffmpeg