"""Tests for configuration loading."""

from __future__ import annotations

import unittest

from smart_lights.config import load_cloud_config, load_devices, load_scenes


class ConfigTests(unittest.TestCase):
    """Validate repo configuration files load into typed models."""

    def test_load_devices(self) -> None:
        devices = load_devices()
        self.assertEqual(len(devices), 3)
        self.assertEqual(devices[0].dps.switch, 20)

    def test_load_cloud_config(self) -> None:
        cloud = load_cloud_config()
        self.assertEqual(cloud.api_region, "us")
        self.assertEqual(cloud.api_device_id, "scan")

    def test_load_scenes(self) -> None:
        scenes = load_scenes()
        self.assertGreaterEqual(len(scenes), 3)
        self.assertEqual(scenes[0].name, "all-off")


if __name__ == "__main__":
    unittest.main()
