# Contributing to LUNA

Thanks for your interest in LUNA Light Studio. This is a hardware-specific interoperability project, so reproducible observations and careful protocol documentation are especially valuable.

## Before opening a pull request

- Open an issue describing the controller model, firmware behaviour and proposed change.
- Keep the desktop and Android protocol implementations in sync when modifying a packet format.
- Add or update desktop unit tests for protocol, BLE ordering, palette or theme changes.
- Distinguish commands observed in the original app from commands physically tested on the strip.
- Never submit vendor APKs, decompiled proprietary source, raw private Bluetooth captures, personal device addresses or credentials.
- Keep platform-specific GUI changes isolated from protocol code where practical.

## Test locally

```bash
cd desktop
python -m unittest discover -s tests -v
```

For Android, build with JDK 17, SDK Platform 35 and Gradle 8.7. See [docs/BUILDING.md](docs/BUILDING.md).

## Hardware bug reports

Include your OS, LUNA version/commit, Android version if applicable, whether the device advertises `GATT--DEMO`, exact steps to reproduce, expected versus actual result, and any **sanitised** logs. Do not post unique BLE addresses, private settings, full HCI dumps or authentication data.

## Project scope

Per-pixel or segment control is a research goal, not a supported feature. Please don't submit guessed BLE commands or potentially destructive firmware-flashing steps as if they were verified. Controller-side timers and audio features also require careful real-device testing.

## Licence

A project licence is pending the owner's decision. External contributions should wait until licensing and contribution terms are clear.
