# LUNA Light Studio: Reverse-Engineering a Bluetooth LED Controller and Building a Cross-Platform Application

## Abstract

LUNA Light Studio is a cross-platform application for controlling a Bluetooth LED strip from Linux, Windows and Android. The project began with a practical limitation: the strip was controlled through a proprietary Android application, while no equivalent desktop application was available for the user's workflow. Rather than replacing the hardware, the project reconstructed the controller's Bluetooth Low Energy (BLE) command interface and implemented independent clients for three operating systems.

The resulting system combines BLE protocol analysis, asynchronous communication, native desktop and mobile interfaces, persistent configuration, and application packaging. It supports global colour selection, brightness, power, predefined animations, saved colour palettes, and a colour-adaptive interface. More advanced functions, such as controller-side schedules and audio reaction, are included with explicit verification caveats. Arbitrary per-LED colour selection remains an identified firmware/protocol limitation rather than a falsely advertised feature.

## Problem statement

The LED strip was driven by a small Bluetooth controller and configured through an Android app known as Mr Star. The user's goals were to control the same hardware from a Linux PC, retain access on Windows, and ultimately create a polished replacement Android experience. A further goal was independent control of coloured sections of the strip.

The central engineering challenge was that the Bluetooth command format was not documented for general-purpose developers. Establishing reliable control required discovering the device's GATT layout, recovering command encodings, and accounting for asynchronous writes and state changes.

## Reverse-engineering approach

The controller advertised itself as `GATT--DEMO`. BLE discovery showed a vendor-specific GATT service (`FFF0`), a writable characteristic (`FFF3`) and a notification characteristic (`FFF4`). These UUIDs established the communication path but did not describe the payload semantics.

The original Android APK was examined to understand how application actions map to BLE packets. The recovered protocol uses frames that generally begin with `BC` and terminate with `55`. Distinct opcodes control power, HSV colour, brightness, pixel count, RGB channel order and built-in effects. For example, the ON command is `BC 01 01 01 55`, and the OFF command is `BC 01 01 00 55`.

Colour selection is not transmitted as a three-byte RGB tuple. LUNA converts a user-selected HEX colour into hue and saturation, encodes those values into the expected frame, and sends brightness separately. This distinction matters for accurately reproducing the original app's behaviour.

The investigation also identified 58 effect IDs in the original app's visible categories. LUNA exposes these through searchable UI controls. Additional names found in app resources were not automatically assumed to be supported by the hardware.

## Desktop implementation

The first prototype used Python, Bleak and Tkinter to establish basic LED control. Once the protocol was understood, the interface was rebuilt with PySide6 to support a more cohesive application architecture.

The desktop implementation separates packet construction from Bluetooth transport and UI state. `protocol.py` contains pure encoders, `ble.py` manages connection and writes, `window.py` coordinates controls, and separate modules implement effects, palette persistence, theme calculations and audio functionality. This division makes the packet logic testable without a physical LED strip.

A major reliability problem appeared during early power testing: the LEDs switched off promptly but sometimes took a long time to switch on. The issue was addressed by serialising BLE writes and removing unnecessary brightness or colour packets from the power-on action. The final power toggle transmits a single command, while related multi-packet operations use an ordered sequence. This fix was verified by repeated use on the actual controller.

## User experience and persistent state

LUNA's UI uses a dark layout with accents derived from the currently selected LED colour. Instead of applying the chosen HEX colour indiscriminately, the theme engine adjusts contrast for readable controls, including extreme colours such as black or white. The LED colour value itself is not altered by these interface adjustments.

Users can name, save, rename, delete and reuse colours. The desktop version stores preferences through Qt's `QSettings`; the Android version uses `SharedPreferences`. Saved palettes use a compatible JSON representation, although automatic synchronisation across devices is not implemented. Crucially, LUNA does not push all saved settings to the controller merely because a connection is established.

## Cross-platform engineering

Linux and Windows share the same PySide6/Bleak application code. PyInstaller packages the application into a platform-native executable, while platform-specific scripts handle installation and launcher integration. On Linux, the installer registers a KDE application entry; on Windows, it creates a Start menu shortcut. Both builds use the same protocol encoders and regression tests.

Android uses a native Kotlin implementation because desktop Qt widgets and Python's Bleak backend are not directly interchangeable with Android's lifecycle and BLE APIs. Its Bluetooth transport uses a serialised GATT-write queue, preserving the key reliability lesson from the desktop version. The Android interface adds a custom HSV colour wheel and a glowing preview. A touch-handling bug was resolved by preventing the parent scroll view from intercepting wheel gestures until the finger is released or the gesture is cancelled.

## Testing and validation

The desktop test suite checks exact packet bytes, effect IDs, write ordering, saved-colour serialisation and theme contrast. These tests run without Bluetooth hardware by using a mocked transport. Real-device testing was still essential: the user confirmed working core LED control on Linux, Windows and Android, and verified the power and Android colour-wheel gesture fixes.

The project distinguishes between features that are implemented in source code and those that have been physically verified. Controller-specific effect behaviour, scheduling and some audio-related commands require further device testing. A successful BLE write does not prove that a firmware feature executed.

## Limitations and future work

The largest unresolved feature is arbitrary segment or per-pixel colour control. The built-in rainbow effects prove the controller can produce multiple simultaneous colours, but the inspected application exposes no command for assigning colours to arbitrary LED indices. Experiments with the active-pixel-count setting showed that inactive LEDs turn off, rather than retaining independently chosen colours. A GATT probe found no additional write characteristic.

Possible future work includes identifying the physical LED signalling protocol, evaluating a compatible replacement controller, implementing cross-device palette export/import, completing Android music playback and audio analysis, and adding more comprehensive hardware-in-the-loop tests. None of these is presented as completed work.

## Outcome

LUNA demonstrates how an undocumented consumer device can be integrated into a multi-platform software system through protocol analysis and careful engineering. The most valuable work was not merely reproducing UI controls: it involved turning uncertain hardware behaviour into documented commands, diagnosing asynchronous communication failures, designing maintainable cross-platform layers, and iterating against real hardware feedback.

**Technologies:** Python, PySide6, Bleak, asyncio, Kotlin, Android BluetoothGatt, Android SDK, Gradle, Qt Multimedia, PortAudio, PyInstaller, Git and GitHub Actions.
