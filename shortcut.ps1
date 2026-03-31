# Simple Desktop Shortcut Creator
# Save as: CreateShortcut.ps1
# Right-click → "Run with PowerShell"

$AppName = "MP4 to MP3 Converter"
$AppPath = ".\dist\MP4toMP3.exe"
$IconPath = ".\icon.ico"

# Check if app exists
if (-not (Test-Path $AppPath)) {
    Write-Host "ERROR: Application not found at $AppPath" -ForegroundColor Red
    Write-Host "Looking for application..."
    
    # Try to find it
    if (Test-Path ".\MP4toMP3.exe") { $AppPath = ".\MP4toMP3.exe" }
    elseif (Test-Path ".\main.py") { $AppPath = "python.exe `".\main.py`"" }
    else {
        Write-Host "Please specify the correct application path." -ForegroundColor Yellow
        pause
        exit 1
    }
}

# Create shortcut
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = "$DesktopPath\$AppName.lnk"

try {
    $WshShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut($ShortcutPath)
    $Shortcut.TargetPath = $AppPath
    $Shortcut.WorkingDirectory = (Get-Location).Path
    
    # Add icon if exists
    if (Test-Path $IconPath) {
        $Shortcut.IconLocation = "$IconPath,0"
    }
    
    $Shortcut.Save()
    
    Write-Host " SUCCESS!" -ForegroundColor Green
    Write-Host "Shortcut created at: $ShortcutPath" -ForegroundColor White
    
    # Show shortcut
    explorer.exe "/select,$ShortcutPath"
}
catch {
    Write-Host " ERROR: $_" -ForegroundColor Red
}

pause