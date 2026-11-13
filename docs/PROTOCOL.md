# Bluetooth LE protocol reference

This is an **interoperability-oriented description** of the observed command formats for a BLE LED controller advertised as `GATT--DEMO`. It is based on examination of the original Android application's behaviour/source and subsequent tests with the LUNA implementations. It is not a vendor specification and does not imply compatibility with every controller or firmware revision.

## GATT layout

| Component | UUID | Role |
|---|---|---|
| Service | `0000fff0-0000-1000-8000-00805f9b34fb` | Vendor-specific service |
| Characteristic | `0000fff3-0000-1000-8000-00805f9b34fb` | Write / write without response |
| Characteristic | `0000fff4-0000-1000-8000-00805f9b34fb` | Notifications |

The inspected controller exposed only these two characteristics. An MTU-dependent maximum write length is **not** evidence of support for arbitrary pixel buffers.

## Packet structure

Most commands start with `BC`, carry an opcode and payload, and end with `55`. The exact meaning of the intervening length/subcommand fields varies by command. Avoid treating every packet as a generic fixed-length record.

All examples below are **hexadecimal bytes**; placeholders such as `[hi]` and `[lo]` describe fields, not literal bytes.

| Action | Packet bytes | Notes |
|---|---|---|
| Power OFF | `BC 01 01 00 55` | One command per toggle |
| Power ON | `BC 01 01 01 55` | No extra colour/brightness write required |
| Global colour | `BC 04 06 [H_hi] [H_lo] [S_hi] [S_lo] 00 00 55` | Hue and saturation, not per-pixel RGB |
| Brightness | `BC 05 06 [B_hi] [B_lo] 00 00 00 00 55` | `B` in 0–1000 |
| Active pixel count | `BC 03 02 [N_hi] [N_lo] 55` | LUNA UI clamps `N` to 8–300 |
| Channel order | `BC 02 01 [order] 55` | Six positions, 1–6 |
| Effect | `BC 06 02 [id/255] [id%255] 55` | Unusual divisor **255**, as found in app logic |
| Effect speed | `BC 08 01 [speed] 55` | LUNA UI range 1–100 |
| Effect direction | `BC 07 01 [00 or 01] 55` | UI direction toggle |
| Host microphone colour | `BC 09 06 [H_hi] [H_lo] [S_hi] [S_lo] 00 00 55` | Used for host-generated audio response |
| Microphone source | `BC 0F 01 [00 or 01] 55` | Source selection |
| Microphone mode | `BC 11 01 [01..04] 55` | Classic, Soft, Dynamic, Disco |
| Microphone sensitivity | `BC 12 01 [value] 55` | UI range 0–100 |
| Read timer | `BC 0C 01 01 55` | Notification response may vary |
| Write timer | `BC 0D 06 01 [on/off] [enabled] [weekday mask] [hour] [minute] 55` | Experimental on hardware |

The device-clock command has a non-standard layout: `BC 0B 07 [year_hi] [year_lo] [month] [day] [hour] [minute] [second] 55 [weekday]`.

### Colour encoding

LUNA converts `#RRGGBB` to HSV before transmission. Hue is an integer in approximately `0–359`, and saturation is scaled to `0–1000`. Brightness is transmitted separately. The final two zero bytes in the global-colour packet were constant in the examined application; their firmware semantics remain unknown.

Example: full-saturation red:

```text
BC 04 06 00 00 03 E8 00 00 55
```

Example: brightness 800/1000:

```text
BC 05 06 03 20 00 00 00 00 55
```

### Effect catalogue

LUNA exposes the 58 effect IDs in the original app's visible mode categories:

| Category | IDs | Count |
|---|---|---:|
| Basic | `1–4, 7, 10, 26–27, 29–32` | 12 |
| Opening & closing | `35–44` | 10 |
| Transition | `45–54` | 10 |
| Running water | `55–62` | 8 |
| Tailing | `76–83` | 8 |
| Running | `84–93` | 10 |
| **Total** | | **58** |

The Android resources contained additional names, but those are not automatically treated as verified controller modes.

## Why custom LED segments are not implemented

The built-in flowing-water animation displays several colours simultaneously, proving the **controller can generate a multi-colour data stream**. It does **not** prove that the BLE API accepts a colour for a particular LED index or range.

A controlled test with 150 active LEDs, then 75 active LEDs, showed that reducing the pixel-count setting turned off the inactive half; changing the global colour affected only the active LEDs. It did not preserve a different colour in the inactive half. This makes the pixel-count setting unsuitable as a segment editor.

No arbitrary per-pixel or range-addressing operation was identified in the examined Android app, and the GATT probe found no second write path. **Undocumented commands remain possible**, but LUNA does not guess at them or send random opcodes.

## Reliability considerations

1. Use a single active BLE connection to the controller.
2. Serialise GATT writes; don't send multiple power/brightness packets simultaneously.
3. Keep power toggles to a single ON or OFF frame.
4. Don't reapply stored settings automatically on connect.
5. Treat write success as transport completion, not confirmed LED state.
6. Validate schedule commands on hardware before unattended use.

For implementation, see `desktop/mrstar/protocol.py`, `desktop/mrstar/ble.py`, `android/app/src/main/java/dev/luna/lightstudio/Protocol.kt`, and `LedBluetooth.kt`.
