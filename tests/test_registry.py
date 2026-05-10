"""Tests for device registry targeting and persistence-free updates."""

from __future__ import annotations

import unittest

from smart_lights.config import load_devices
from smart_lights.registry import DeviceRegistry


class RegistryTests(unittest.TestCase):
    """Exercise registry lookup behavior."""

    def setUp(self) -> None:
        self.registry = DeviceRegistry(load_devices())

    def test_resolve_all(self) -> None:
        self.assertEqual(len(self.registry.resolve("all")), 3)

    def test_resolve_room(self) -> None:
        devices = self.registry.resolve("living-room")
        self.assertEqual(len(devices), 3)

    def test_resolve_device_by_slug(self) -> None:
        device = self.registry.get("living-room-top")
        self.assertEqual(device.device_id, "ebdcf642f6e599f9e4v425")


if __name__ == "__main__":
    unittest.main()
