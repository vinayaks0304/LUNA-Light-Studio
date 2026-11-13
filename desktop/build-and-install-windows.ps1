# LUNA Windows port: build a native Windows .exe, then install for this user.
# Run from PowerShell on Windows 10/11, or double-click install-windows.bat.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$source = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $source
# Resolve the actual interpreter executable before creating the virtual environment.
# This avoids a launcher/splatting combination that can open the Python >>> prompt
# instead of executing `python -m venv` on some Windows installations.
$pythonPath = $null
$pyLauncher = Get-Command py.exe -ErrorAction SilentlyContinue
if ($null -ne $pyLauncher) {
  try {
    $resolved = & ($pyLauncher.Source) -3 -c 'import sys; print(sys.executable)'
    if ($LASTEXITCODE -eq 0 -and $resolved) {
      $candidate = [string](@($resolved)[-1])
      if (Test-Path -LiteralPath $candidate -PathType Leaf) { $pythonPath = $candidate }
    }
  } catch {
    Write-Host 'Python launcher could not resolve an interpreter; trying python.exe directly.'
  }
}
if (-not $pythonPath) {
  $pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
  if ($null -eq $pythonCommand) {
    throw 'Python 3.11+ not found. Install Python from python.org and retry.'
  }
  $pythonPath = $pythonCommand.Source
}
Write-Host "Using Python: $pythonPath"
& $pythonPath -c 'import sys; assert sys.version_info >= (3,11), "Python 3.11+ required"; print(sys.version.split()[0])'
if ($LASTEXITCODE -ne 0) { throw 'Python 3.11+ is required.' }

$venv = Join-Path $source '.build\venv'
$pythonExe = Join-Path $venv 'Scripts\python.exe'
Write-Host '[1/5] Creating a temporary build environment...'
& $pythonPath -m venv $venv
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $pythonExe)) {
  throw 'Failed to create build environment. Try running the installer from a writable extracted folder.'
}

Write-Host '[2/5] Installing LUNA and packaging dependencies...'
& $pythonExe -m pip install --disable-pip-version-check -r (Join-Path $source 'requirements.txt') 'pyinstaller>=6.11,<7'
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }

Write-Host '[3/5] Running protocol and preference regression tests...'
& $pythonExe -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw 'Tests failed; existing installation has not been changed.' }

Write-Host '[4/5] Building standalone Windows application...'
$icon = Join-Path $source 'assets\luna.ico'
$png = Join-Path $source 'assets\luna-512.png'
& $pythonExe -m PyInstaller --noconfirm --clean --onedir --windowed --noupx `
  --name LUNA --icon $icon `
  --distpath (Join-Path $source 'dist') `
  --workpath (Join-Path $source '.build\work') `
  --specpath (Join-Path $source '.build\spec') `
  --add-data "${png};assets" `
  --hidden-import PySide6.QtMultimedia `
  --collect-submodules bleak.backends.winrt `
  --collect-all sounddevice `
  (Join-Path $source 'main.py')
if ($LASTEXITCODE -ne 0) { throw 'Windows build failed.' }

$built = Join-Path $source 'dist\LUNA'
$exe = Join-Path $built 'LUNA.exe'
if (-not (Test-Path $exe)) { throw 'The expected executable was not produced.' }

Write-Host '[5/5] Installing LUNA for the current Windows user...'
if (Get-Process -Name LUNA -ErrorAction SilentlyContinue) {
  throw 'Close LUNA before installing this update, then run the installer again.'
}
$target = Join-Path $env:LOCALAPPDATA 'Programs\LUNA'
if (Test-Path $target) { Remove-Item -LiteralPath $target -Recurse -Force }
New-Item -ItemType Directory -Force -Path (Split-Path $target) | Out-Null
Copy-Item -LiteralPath $built -Destination $target -Recurse
$installedExe = Join-Path $target 'LUNA.exe'

$startDir = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'
$shortcutPath = Join-Path $startDir 'LUNA Light Studio.lnk'
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $installedExe
$shortcut.WorkingDirectory = $target
$shortcut.IconLocation = "$installedExe,0"
$shortcut.Description = 'LUNA Light Studio — Bluetooth LED control'
$shortcut.Save()

Write-Host ''
Write-Host 'LUNA installed successfully.' -ForegroundColor Green
Write-Host "Open Start and search for 'LUNA Light Studio'."
Write-Host "Executable: $installedExe"
Write-Host 'Your Windows settings and saved colours are not deleted during updates.'
