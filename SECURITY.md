# Security and privacy

LUNA sends commands directly to a local Bluetooth Low Energy controller. The current source does not implement cloud accounts, telemetry, or a remote control server.

## Data handling

- Desktop saved colours and preferences are stored locally using Qt `QSettings`.
- Android saved colours and preferences are stored locally using `SharedPreferences`.
- The desktop audio-reactive mode processes a selected local audio input; the source does not intentionally record audio to disk.
- The public source scans by the advertised BLE name and contains no private controller address.

## Before publishing logs or issues

Remove personal Bluetooth addresses, device identifiers, filesystem paths containing usernames, private settings, tokens and any unrelated traffic. Raw HCI captures may contain data from other connected devices and should not be uploaded publicly.

## Reporting a security concern

Until a private vulnerability-reporting contact is configured, avoid posting exploitable details in public issues. The repository owner should enable GitHub's private vulnerability reporting in **Settings → Security → Code security and analysis** before announcing a formal reporting channel.

## Hardware caution

LUNA is not designed for safety-critical lighting. Experimental timer features must be supervised during validation. Avoid sending arbitrary undocumented BLE opcodes or changing physical wiring/voltage without identifying the hardware.
