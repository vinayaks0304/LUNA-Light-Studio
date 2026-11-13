#!/usr/bin/env python3
"""Read-only GATT inventory for a controller advertising as GATT--DEMO.

Install Bleak first (`python -m pip install bleak`). Close LUNA/Mr Star.
No characteristic writes or notifications are requested.

For privacy, the device address is not printed by default.
"""
import argparse
import asyncio
import os
from bleak import BleakClient, BleakScanner


async def probe(show_address=False):
    address = os.environ.get('LUNA_BLE_ADDRESS', '').strip()
    name = 'GATT--DEMO'
    print(f'Searching for {name}...')
    if address:
        device = await BleakScanner.find_device_by_address(address, timeout=20)
    else:
        device = await BleakScanner.find_device_by_name(name, timeout=20)
    if device is None:
        raise RuntimeError('Device not found. Check Bluetooth and close other controller apps.')
    print(f'Found: {device.name or "(unnamed)"}' + (f' [{device.address}]' if show_address else ''))
    async with BleakClient(device, timeout=20) as client:
        print('Connected:', client.is_connected)
        for service in client.services:
            print('SERVICE', service.uuid, service.description)
            for characteristic in service.characteristics:
                print('  CHAR', characteristic.uuid, ', '.join(characteristic.properties))
                if 'write-without-response' in characteristic.properties:
                    print('    Max write-without-response bytes:', characteristic.max_write_without_response_size)
                for descriptor in characteristic.descriptors:
                    print('    DESCRIPTOR', descriptor.uuid)
    print('Disconnected. No commands sent.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--show-address', action='store_true', help='Show private BLE address in terminal output')
    args = parser.parse_args()
    asyncio.run(probe(args.show_address))
