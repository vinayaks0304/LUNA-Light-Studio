# Development history

LUNA grew from a small desktop BLE experiment into a three-platform application. This is a chronological account of the engineering milestones rather than a claim that every experimental feature has been validated.

## 1. Establishing control from a PC

The starting point was a USB-powered LED strip controlled by the Mr Star Android app. The device advertised itself as `GATT--DEMO`. BLE inspection identified vendor service `FFF0` and command-write characteristic `FFF3`.

An early Python script used **Bleak** for BLE transport and **Tkinter** for basic colour and brightness controls. The first working global-colour command established that a Linux desktop could control the same strip as the phone app.

## 2. Recovering the controller protocol

The Android APK was examined to map UI actions to transmitted bytes. This produced packet encoders for power, HSV colour, brightness, pixel count, channel order, effect selection, speed, direction, microphone controls, and scheduling.

The original application source was used **for protocol analysis only**. It is not included in this repository. The protocol descriptions and new LUNA implementations are documented separately.

## 3. Building a real desktop application

The Tkinter prototype was replaced with a **PySide6** interface featuring a dashboard, navigation, colour controls, presets, brightness and device settings. The project was renamed **LUNA Light Studio**.

A significant early bug affected power toggling: OFF often worked instantly, while ON was inconsistent or delayed. Investigation pointed to overlapping BLE writes and unnecessary follow-up commands. The fix serialised writes and reduced each power toggle to a single packet. The user subsequently confirmed reliable ON/OFF operation.

## 4. Investigating selective LED colours

A key goal was to colour the first half of the strip blue and the second half pink. The strip's flowing-water effects clearly showed multiple colours at once. However, setting the active pixel count to 75 of 150 turned the other half off rather than retaining a different colour.

The source-code audit and GATT service probe found no identifiable arbitrary per-pixel or range-write operation. LUNA therefore **does not claim segment control**. A replacement controller might be a future option once the strip's electrical protocol and voltage are established.

## 5. Extending the feature set

The desktop application gained 58 selectable effects, microphone modes, local music playback, experimental PC audio reaction and controller-side schedule controls. Saved named colours were added using `QSettings` and JSON serialisation.

Next came a **colour-reactive dark theme**: the UI derives accents from the selected light colour while adjusting contrast to keep controls legible. Theme previews do not send extra BLE packets.

## 6. Standalone Linux and Windows releases

The desktop code was packaged with **PyInstaller**. The Linux installer registers an application-menu entry on KDE and a `luna` command. The Windows installer builds a native `.exe` and creates a Start menu shortcut. An early Windows build-script issue that opened an interactive Python prompt was corrected by resolving the Python executable explicitly.

The user confirmed that the Windows build launched and controlled the LEDs successfully.

## 7. Native Android port

Android was implemented separately in **Kotlin**, using Android's BLE APIs. It preserves the controller protocol while using native UI and local preferences.

The Android visual redesign introduced a touch-sensitive HSV colour wheel, a glowing colour preview, adaptive dark styling and mobile navigation. A gesture conflict between the wheel and its surrounding scroll view was fixed by disallowing parent interception during wheel drags. The user subsequently confirmed the Android app was working.

## 8. Repository consolidation

The Linux and Windows source trees were identical at the application level, so they were consolidated into one `desktop/` implementation with both installers. The Kotlin port lives in `android/`. The repository adds documentation, a conservative feature matrix, automated desktop tests and CI workflows.

The public source intentionally avoids embedding the developer's private controller address and excludes APK decompilations, raw HCI logs, and personal settings.

## Lessons learned

- **A BLE write is not a hardware acknowledgement.** Transport and device behaviour must be distinguished.
- **Command ordering matters.** Serialisation fixed a bug that looked like a firmware problem.
- **A controller-generated rainbow is not proof of a pixel-addressing API.** Capabilities need experimental verification.
- **Native touch interaction needs explicit gesture ownership.** Custom controls can conflict with parent scrolling containers.
- **Persistent data belongs outside application bundles.** This allows safe updates without losing saved palettes.
- **Platform sharing has limits.** Desktop code can be reused across Linux and Windows, while Android benefits from a native BLE/UI layer.
