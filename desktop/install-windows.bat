@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0build-and-install-windows.ps1"
if errorlevel 1 (
  echo.
  echo LUNA installation failed. Read the error above.
  pause
  exit /b 1
)
echo.
echo Installation complete. Press any key to close.
pause >nul
