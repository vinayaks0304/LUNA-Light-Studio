# Development tools

## Read-only GATT probe

`ble_gatt_probe.py` inventories the BLE services, characteristics and descriptors advertised by a `GATT--DEMO` controller. It **does not send LED commands**.

```bash
python -m pip install bleak
python tools/ble_gatt_probe.py
```

Close LUNA and Mr Star before running it. The probe hides the device address in its default output; `--show-address` is intended for local diagnosis only. Avoid publishing output with identifying device addresses.
