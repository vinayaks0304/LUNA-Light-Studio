# Build and install LUNA

This repository contains **source code**, not prebuilt installers or a signed Android APK. Desktop installers build native executables on their target operating system. The Android debug APK is built with the Android SDK.

## Linux (CachyOS / Arch / KDE)

Requirements: Linux x86_64, Python 3 with `venv`, BlueZ, and PortAudio for optional desktop audio reaction.

```bash
sudo pacman -S --needed python python-pip bluez portaudio
sudo systemctl enable --now bluetooth
cd desktop
./install-luna.sh
```

The installer creates a temporary Python environment, installs dependencies, builds a PyInstaller bundle and installs it under:

```text
~/.local/opt/luna/
```

It also creates `~/.local/bin/luna` and a KDE application launcher. **Everyday use does not require activating a Python environment.** The initial build needs internet access. To remove the app while keeping preferences, run `./uninstall-luna.sh`.

To run from source for development:

```bash
cd desktop
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

## Windows 10/11

Requirements: Windows 10/11 x64, Bluetooth LE support, Python 3.11+ for the one-time build, and internet access to download Python dependencies.

1. Extract or clone the repository on Windows.
2. Open `desktop/`.
3. Double-click `install-windows.bat` (or run it from PowerShell to see build logs).
4. After installation, open **LUNA Light Studio** from the Start menu.

The script runs unit tests, creates a PyInstaller `LUNA.exe`, and installs it under:

```text
%LOCALAPPDATA%\Programs\LUNA\
```

The source/build directory can be removed **after installation succeeds**. Saved settings live in the Windows user profile, not alongside the executable. Build the Windows executable on Windows rather than attempting a cross-compile from Linux.

## Android (build on Linux)

Requirements:

- JDK 17 (`jdk17-openjdk` on CachyOS).
- Android SDK Platform 35, SDK Build-Tools, Platform-Tools, and accepted SDK licences.
- Gradle installed locally for the one-time wrapper generation. The wrapper itself uses **Gradle 8.7**.
- Android device with BLE and USB debugging enabled for `adb install`.

On CachyOS:

```bash
sudo pacman -S --needed jdk17-openjdk gradle android-tools
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk
export ANDROID_HOME="$HOME/Android/Sdk"
export PATH="$JAVA_HOME/bin:$ANDROID_HOME/platform-tools:$PATH"

cd android
./setup-wrapper.sh
./gradlew assembleDebug
adb devices
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

The generated APK is:

```text
android/app/build/outputs/apk/debug/app-debug.apk
```

`setup-wrapper.sh` generates the official `gradlew` launcher and wrapper JAR from a locally installed Gradle. These generated files are ignored by Git. If your project already has a working wrapper, skip that step. The setup script uses `--no-validate-url` because a previous environment could not validate the Gradle distribution URL before downloading it; the actual Gradle download still happens when the wrapper runs.

**Android Studio alternative:** Open the `android/` directory as a project, configure the JDK 17 Gradle runtime and Android SDK Platform 35, and build the debug APK. No emulator is required when testing on a real phone.

**Updating an existing installation:** `adb install -r` retains app data when the package ID and signing certificate match. Debug keys may differ between computers; don't uninstall an existing app if you need its saved colours until you've backed them up.

## Bluetooth device selection

By default, LUNA scans for a peripheral advertising **`GATT--DEMO`**. This makes the public repository independent of one person's Bluetooth address.

On desktop, an optional private address override is available:

```bash
# Linux example; do not commit your actual device address
LUNA_BLE_ADDRESS='AA:BB:CC:DD:EE:FF' python main.py
```

On Windows PowerShell, set `$env:LUNA_BLE_ADDRESS` before launching the executable. If you rely on a private address for a desktop-launcher install, configure it locally; do not put it in public repository files. Android currently scans by advertised name only.

## Tests

```bash
cd desktop
python -m unittest discover -s tests -v
```

Unit tests use mocked Bluetooth classes and do not require a powered LED strip. They do not replace manual BLE, UI, audio, or schedule tests on each platform.
