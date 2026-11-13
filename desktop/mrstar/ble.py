"""BLE connection and ordered writes; preserves LUNA's working power fix."""
import asyncio
import os
from bleak import BleakClient, BleakScanner

TARGET_NAME = 'GATT--DEMO'
WRITE_UUID = '0000fff3-0000-1000-8000-00805f9b34fb'
NOTIFY_UUID = '0000fff4-0000-1000-8000-00805f9b34fb'


class Controller:
    def __init__(self, status, notification=None, disconnected=None):
        self.client = None
        self.status = status
        self.notification = notification
        self.disconnected = disconnected
        self._write_lock = asyncio.Lock()
        self._intentional_disconnect = False

    @property
    def connected(self):
        return bool(self.client and self.client.is_connected)

    def _on_disconnect(self, _client):
        if not self._intentional_disconnect and self.disconnected:
            self.disconnected()

    async def connect(self):
        if self.connected:
            return
        self.status('Searching for GATT--DEMO…')
        # Public source has no hard-coded private controller address.
        # Set LUNA_BLE_ADDRESS to target a specific controller if name scanning fails.
        target_address = os.environ.get('LUNA_BLE_ADDRESS', '').strip()
        if target_address:
            device = await BleakScanner.find_device_by_address(target_address, timeout=15)
        else:
            device = await BleakScanner.find_device_by_name(TARGET_NAME, timeout=15)
        if device is None:
            raise RuntimeError('GATT--DEMO not found. Check power and Bluetooth.')
        self._intentional_disconnect = False
        self.client = BleakClient(device, timeout=20, disconnected_callback=self._on_disconnect)
        try:
            await self.client.connect()
            if self.notification:
                try:
                    await self.client.start_notify(NOTIFY_UUID,
                        lambda _sender, data: self.notification(bytes(data)))
                except Exception as exc:
                    self.status(f'Connected; timer readback unavailable: {exc}')
            self.status('Connected to GATT--DEMO')
        except Exception:
            if self.client and self.client.is_connected:
                await self.client.disconnect()
            self.client = None
            raise

    async def disconnect(self):
        self._intentional_disconnect = True
        try:
            if self.connected:
                await self.client.disconnect()
        finally:
            self.client = None
            self.status('Disconnected')

    async def send(self, frame, *, drop_if_busy=False):
        if not self.connected:
            raise RuntimeError('Connect to the controller first.')
        if drop_if_busy and self._write_lock.locked():
            return False
        async with self._write_lock:
            if not self.connected:
                raise RuntimeError('LED controller disconnected.')
            await self.client.write_gatt_char(WRITE_UUID, bytes(frame), response=False)
        return True

    async def send_many(self, frames):
        """Keep a short related sequence contiguous (e.g. clock then schedule)."""
        if not self.connected:
            raise RuntimeError('Connect to the controller first.')
        async with self._write_lock:
            for frame in frames:
                if not self.connected:
                    raise RuntimeError('LED controller disconnected.')
                await self.client.write_gatt_char(WRITE_UUID, bytes(frame), response=False)
                # The original Android BLE library also spaced writes.
                await asyncio.sleep(0.08)
        return True
