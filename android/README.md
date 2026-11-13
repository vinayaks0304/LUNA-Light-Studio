# LUNA Android

Native Kotlin Android app using `BluetoothGatt` and a custom `ColourWheelView`. It implements LUNA's colour-reactive dark UI, saved palettes, core BLE controls and 58 selectable built-in effects.

## Build on Linux

Prerequisites: JDK 17, Android SDK Platform 35, Android SDK Build-Tools, Android Platform-Tools (`adb`), and a locally installed Gradle for initial wrapper generation.

```bash
cd android
./setup-wrapper.sh
./gradlew assembleDebug
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

The setup script generates `gradlew` and the official wrapper JAR locally; those generated files are not stored in this repository. If you use Android Studio, open this `android/` directory and allow Gradle sync.

### Android-specific design

- The wheel sends a colour command **on finger release**, not continuously while dragging.
- The wheel prevents the surrounding scroll view from intercepting active wheel gestures.
- BLE writes are serialised through a GATT queue to avoid overlapping power commands.
- Colours and UI preferences are stored locally with `SharedPreferences` (the `luna` store).
- The app discovers peripherals advertising `GATT--DEMO`, rather than embedding a device-specific address.

The Music page does not yet implement Android local music playback or phone-microphone audio analysis. Controller microphone modes and controller-side schedules are separate features.

See [the build guide](../docs/BUILDING.md), [feature matrix](../docs/FEATURE_MATRIX.md) and [protocol reference](../docs/PROTOCOL.md).
