# Troubleshooting

## LUNA cannot find the LED controller

1. Power the strip and enable Bluetooth.
2. Close Mr Star and other LUNA instances; only one client should control the device at a time.
3. Check whether the controller advertises the name `GATT--DEMO`.
4. On Linux, check `bluetoothctl show` and that the Bluetooth service is running.
5. On Android, grant Nearby devices/Bluetooth permissions when requested.

The public repository discovers by advertised name rather than a hard-coded personal MAC address. If desktop name scanning fails, set the `LUNA_BLE_ADDRESS` environment variable locally. Do **not** commit your own address.

## Power OFF works but power ON is delayed

Early versions suffered from overlapping BLE writes and extra commands during power-on. Current desktop code serialises writes using an `asyncio.Lock`; Android uses a GATT write queue. Check that you're running the latest source and that another app is not connected. Avoid adding arbitrary sleeps or repeatedly hammering the power button before inspecting the connection state.

## Colour changes but not all LEDs respond

The **active pixel count** determines how many LEDs the controller drives. If you configure 75 when your strip has 150, the other 75 may remain off. Restore the correct count in Settings. This setting does not enable independently coloured sections.

## Android colour wheel scrolls the page

The current `ColourWheelView.kt` owns gestures that begin inside the wheel by calling `requestDisallowInterceptTouchEvent(true)`, then releases the lock on finger-up or cancellation. If scrolling still occurs, ensure your checkout includes the latest `ColourWheelView.kt` and rebuild the APK with `./gradlew assembleDebug`.

## Android Gradle wrapper URL verification failed

`android/setup-wrapper.sh` uses `--no-validate-url` when generating the wrapper. This avoids a preliminary URL check that failed on one system; the actual Gradle 8.7 download is still required. Confirm network access and try `./gradlew --version` before building.

## Android compilation error: Drawable where Int expected

An early Android version referenced a `background` property ambiguously. The current source uses the corrected reference. If you see `Type mismatch: inferred type is Drawable! but Int was expected`, make sure you're compiling the current repository rather than an older extracted ZIP.

## Android SDK XML version warning

Older Android Gradle tooling may warn about a newer SDK XML schema. A warning alone is not necessarily a build failure. Look for the **first actual compiler error** below it. Use JDK 17, Android SDK Platform 35 and the project's Gradle/Android Gradle Plugin versions.

## Windows installer opens a Python `>>>` prompt

An early PowerShell installer invoked the Python launcher incorrectly. The current `desktop/build-and-install-windows.ps1` resolves the real Python executable before running `-m venv`. Use the current installer and run it from an extracted writable folder.

## Linux desktop launcher is missing

Run `~/.local/bin/luna` to verify the executable is installed. On KDE, refresh the application cache with `kbuildsycoca6 --noincremental` or log out and back in. The Linux installer installs a desktop entry under `~/.local/share/applications/`.

## PC audio reaction does not work

The desktop audio-reactive feature needs an accessible PortAudio input. On Linux, system audio loopback may require PipeWire/PulseAudio monitor configuration. On Windows, an appropriate recording or loopback device may not be available. Test with a physical microphone first. The local music player does **not** automatically feed its playback into the reaction algorithm.

## Saved colours missing after an update

Desktop preferences are stored by Qt `QSettings` outside the executable. On Linux, check `~/.config/LUNA Light Studio/LUNA.conf`; on Windows, use the current user's Qt settings backend. Running the app as another user or with `sudo` may create a different preferences store. On Android, an update preserves app data only if the application ID and signing key match. Do not uninstall/clear app data before backing up a palette.

## Schedules appear to save but do not trigger

Timer packets were recovered from the original Android app, but behaviour has not been fully verified on the physical controller. Test a short ON/OFF schedule while supervised. Check the device clock, weekday mask and any available FFF4 notification readback. Do not rely on this feature for safety-critical or unattended operation.
