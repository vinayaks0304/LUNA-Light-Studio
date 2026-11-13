# Changelog

The Linux/Windows desktop app and Android app have historically used separate version numbers. This changelog records project milestones rather than implying identical version numbers across platforms.

## Repository consolidation — 2026-11-13

- Combined the identical Linux/Windows desktop code into one `desktop/` tree.
- Added the native Kotlin Android app with the colour-wheel gesture fix.
- Added architecture, protocol, project write-up, build and troubleshooting documentation.
- Added desktop test and Android build GitHub Actions workflows.
- Removed a device-specific BLE address from public source: desktop scans by name with an optional private address override; Android scans by name.
- Excluded vendor APK/decompiled source, BLE capture logs, private settings and build outputs.

## Desktop v0.5.1

- Standalone PyInstaller builds and user-level Linux/KDE installation.
- Windows build/install script and Start menu integration.
- Colour-reactive dark theme, persistent named colours and quick-palette shortcuts.
- 58 effect selections, audio controls, experimental timers and microphone modes.
- Serialised BLE writes and reliable single-command power toggles.

## Android v0.2.1

- Native Kotlin Bluetooth implementation with queued GATT writes.
- Desktop-inspired adaptive dark UI and custom HSV colour wheel.
- Fixed colour-wheel gestures so the surrounding page does not scroll while dragging.
- Saved colours, effects, brightness, power, pixel count and channel order.
- Local music playback and phone-microphone audio analysis remain unimplemented.

## Earlier work

- Python/Tkinter prototype established initial BLE colour and brightness control.
- APK analysis recovered command formats and the 58-mode effect catalogue.
- GATT probe identified `FFF0`, `FFF3` and `FFF4`.
- Experiments established that pixel count is not a segment-selection mechanism.
