# Feature status and verification

This document separates **implemented software controls** from **observed hardware behaviour**. It is intentionally more conservative than a marketing feature list.

| Feature | Linux | Windows | Android | Verification / caveat |
|---|---|---|---|---|
| Connect to `GATT--DEMO` | Implemented | Implemented | Implemented | Core LED control reported working on all three platforms |
| Power ON/OFF | Implemented | Implemented | Implemented | Power sequencing fixed; single command per toggle |
| Global colour and HEX | Implemented | Implemented | Implemented | Applies to active pixels only |
| Brightness | Implemented | Implemented | Implemented | Encoded separately from hue/saturation |
| Colour wheel / picker | Qt colour picker | Qt colour picker | Custom HSV wheel | Android gesture interception fixed |
| Saved named colours | QSettings | QSettings | SharedPreferences | Local only, no cross-device sync |
| Colour-adaptive dark theme | Implemented | Implemented | Implemented | Does not change hardware brightness |
| 58 effect selections | Implemented | Implemented | Implemented | Catalogue from app analysis; individual effects not all physically validated |
| Effect speed / direction | Implemented | Implemented | Implemented | Controller-specific behaviour |
| Active pixel count | Implemented | Implemented | Implemented | Controls number of active pixels, **not zones** |
| Channel order | Implemented | Implemented | Implemented | Six channel permutations |
| Controller microphone modes | Implemented | Implemented | Implemented | Firmware-dependent |
| PC audio reaction | Experimental | Experimental | Not implemented | Needs compatible microphone/loopback source |
| Local audio player | Implemented | Implemented | Not implemented | Qt Multimedia; playback alone does not imply LED reaction |
| Controller-side schedules | Experimental | Experimental | Experimental | Requires real-hardware verification |
| Arbitrary pixel/segment colours | Not implemented | Not implemented | Not implemented | No identified supported BLE command |

## Testing levels

- **Automated desktop tests:** Protocol encoding, mocked BLE ordering, palette serialisation, adaptive-theme contrast.
- **Manual hardware testing:** User has confirmed working core LED control on Linux, Windows and Android.
- **Not established:** Every animation, every timer/readback path, every microphone mode, or compatibility with different BLE controller firmware.

Do not mark a feature "hardware verified" solely because a BLE write call returned successfully.
