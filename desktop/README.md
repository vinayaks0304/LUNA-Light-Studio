# LUNA desktop (Linux + Windows)

The **same** PySide6/Bleak source is used on both desktop platforms. Both platform installers build a standalone executable locally using PyInstaller.

- **Linux / CachyOS:** `./install-luna.sh` — see [Linux build instructions](../docs/BUILDING.md#linux-cachyos--arch--kde).
- **Windows 10/11:** double-click `install-windows.bat` — see [Windows build instructions](../docs/BUILDING.md#windows-1011).
- **Development:** create a Python virtual environment, install `requirements.txt`, run `python main.py`.
- **Tests:** `python -m unittest discover -s tests -v`.

### Bluetooth discovery

LUNA searches for a BLE peripheral advertising the name **`GATT--DEMO`**. If the device doesn't advertise its name consistently, the desktop app also accepts an optional `LUNA_BLE_ADDRESS` environment variable. Keep your own BLE address private rather than committing it to the repository.

### Saved settings

Qt `QSettings('LUNA Light Studio', 'LUNA')` stores preferences outside the source and executable directories. On Linux this is normally `~/.config/LUNA Light Studio/LUNA.conf`; Windows uses the user-specific Qt settings backend. Saved colours use the JSON key `saved_colours_v1`.

For implementation details and limitations, read the [main README](../README.md) and [architecture](../docs/ARCHITECTURE.md).
