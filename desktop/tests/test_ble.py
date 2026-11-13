"""Mocked BLE regression tests; no physical controller needed."""
import asyncio
import os
import sys
from pathlib import Path
from types import ModuleType
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

fake_bleak = ModuleType('bleak')

class FakeScanner:
    calls = []

    @staticmethod
    async def find_device_by_name(name, timeout):
        FakeScanner.calls.append(('name', name))
        return name

    @staticmethod
    async def find_device_by_address(address, timeout):
        FakeScanner.calls.append(('address', address))
        return address

class FakeClient:
    def __init__(self, device, timeout, disconnected_callback):
        self.device = device
        self.is_connected = False
        self.writes = []
        self.notify = None
        self.disconnected_callback = disconnected_callback

    async def connect(self):
        self.is_connected = True

    async def start_notify(self, uuid, callback):
        self.notify = callback

    async def write_gatt_char(self, uuid, frame, response=False):
        await asyncio.sleep(0.015)
        self.writes.append(bytes(frame))

    async def disconnect(self):
        self.is_connected = False
        self.disconnected_callback(self)

fake_bleak.BleakClient = FakeClient
fake_bleak.BleakScanner = FakeScanner

with patch.dict(sys.modules, {'bleak': fake_bleak}):
    from mrstar.ble import Controller
    from mrstar import protocol


class BleTests(unittest.TestCase):
    def setUp(self):
        FakeScanner.calls.clear()

    def test_name_based_discovery_does_not_publish_a_device_address(self):
        async def run():
            with patch.dict(os.environ, {'LUNA_BLE_ADDRESS': ''}):
                ctrl = Controller(lambda s: None)
                await ctrl.connect()
                self.assertEqual(FakeScanner.calls, [('name', 'GATT--DEMO')])
                await ctrl.disconnect()
        asyncio.run(run())

    def test_optional_private_address_override(self):
        async def run():
            with patch.dict(os.environ, {'LUNA_BLE_ADDRESS': '00:11:22:33:44:55'}):
                ctrl = Controller(lambda s: None)
                await ctrl.connect()
                self.assertEqual(FakeScanner.calls, [('address', '00:11:22:33:44:55')])
                await ctrl.disconnect()
        asyncio.run(run())

    def test_connection_does_not_change_strip_state(self):
        async def run():
            ctrl = Controller(lambda s: None, lambda payload: None)
            await ctrl.connect()
            self.assertEqual(ctrl.client.writes, [])
            self.assertTrue(ctrl.client.notify is not None)
            await ctrl.disconnect()
        asyncio.run(run())

    def test_power_packet_serialisation(self):
        async def run():
            ctrl = Controller(lambda s: None)
            await ctrl.connect()
            await asyncio.gather(ctrl.send(protocol.power_frame(False)),
                                 ctrl.send(protocol.power_frame(True)))
            self.assertEqual(ctrl.client.writes,
                             [protocol.power_frame(False), protocol.power_frame(True)])
            await ctrl.disconnect()
        asyncio.run(run())

    def test_sequence_is_not_interleaved(self):
        async def run():
            ctrl = Controller(lambda s: None)
            await ctrl.connect()
            sequence = asyncio.create_task(ctrl.send_many([
                protocol.clock_frame(), protocol.timer_read_frame()]))
            await asyncio.sleep(0.005)
            power = asyncio.create_task(ctrl.send(protocol.power_frame(False)))
            await asyncio.gather(sequence, power)
            self.assertEqual(ctrl.client.writes[1], protocol.timer_read_frame())
            self.assertEqual(ctrl.client.writes[2], protocol.power_frame(False))
            await ctrl.disconnect()
        asyncio.run(run())


if __name__ == '__main__':
    unittest.main()
