#!/usr/bin/env bash
# One-time builder/installer for CachyOS and other x86_64 Linux desktops.
# After installation, the app uses a bundled runtime, NOT a Python venv.
set -Eeuo pipefail

SOURCE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

if [[ "$(uname -s)" != "Linux" ]]; then
  echo 'LUNA desktop installer supports Linux only.' >&2
  exit 1
fi
if [[ "$(uname -m)" != "x86_64" ]]; then
  echo 'This build script currently targets x86_64 Linux.' >&2
  exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo 'Python is needed once to build the standalone app.' >&2
  echo 'On CachyOS: sudo pacman -S --needed python python-pip bluez portaudio' >&2
  exit 1
fi
if ! python3 -m venv --help >/dev/null 2>&1; then
  echo 'Python venv support is missing. Install Python with venv support first.' >&2
  exit 1
fi
if ! command -v bluetoothctl >/dev/null 2>&1; then
  echo 'Note: bluetoothctl not found. Install bluez to use the LED controller.' >&2
fi
if command -v ldconfig >/dev/null 2>&1 && ! ldconfig -p 2>/dev/null | grep -q 'libportaudio.so'; then
  echo 'Note: libportaudio not found. Install portaudio for PC audio reaction.' >&2
fi

BUILD_DIR="$(mktemp -d "${TMPDIR:-/tmp}/luna-desktop-build.XXXXXXXX")"
cleanup() { rm -rf -- "$BUILD_DIR"; }
trap cleanup EXIT

echo '[1/4] Preparing a temporary build environment...'
python3 -m venv "$BUILD_DIR/venv"

echo '[2/4] Downloading build dependencies (internet required the first time)...'
"$BUILD_DIR/venv/bin/python" -m pip install --disable-pip-version-check --no-input \
  -r "$SOURCE_DIR/requirements.txt" 'pyinstaller>=6.11'

echo '[3/4] Building a bundled Linux executable...'
(
  cd "$SOURCE_DIR"
  "$BUILD_DIR/venv/bin/pyinstaller" \
    --noconfirm --clean --onedir --windowed --noupx \
    --name LUNA \
    --distpath "$BUILD_DIR/dist" \
    --workpath "$BUILD_DIR/work" \
    --specpath "$BUILD_DIR/spec" \
    --add-data "$SOURCE_DIR/assets/luna-512.png:assets" \
    --hidden-import PySide6.QtMultimedia \
    --collect-submodules bleak.backends.bluezdbus \
    --collect-submodules dbus_fast \
    main.py
)

echo '[4/4] Installing LUNA and registering its KDE launcher...'
"$SOURCE_DIR/scripts/install-bundle.sh" "$BUILD_DIR/dist/LUNA"
echo
echo 'LUNA installed successfully.'
echo 'Launch from the KDE application menu, or type: luna'
echo 'Your existing LUNA preferences and saved colours have not been changed.'
