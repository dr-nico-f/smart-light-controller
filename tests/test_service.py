"""Tests for local-first fallback behavior in the service layer."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from smart_lights.config import load_devices
from smart_lights.registry import DeviceRegistry
from smart_lights.scenes import SceneLibrary
from smart_lights.service import SmartLightsService


class FakeLocalClient:
    """Test double that simulates a stale IP followed by a successful refresh."""

    def status(self, device):
        if device.ip_address == "192.168.40.250":
            return {"Err": "901", "Error": "Network Error: Unable to Connect"}
        return {"dps": {"20": True}}

    def turn_on(self, device):
        return {"updated": device.ip_address}

    def turn_off(self, device):
        return {"updated": device.ip_address}

    def set_mode(self, device, mode):
        return {"mode": mode, "ip": device.ip_address}

    def set_brightness(self, device, brightness):
        return {"brightness": brightness, "ip": device.ip_address}

    def set_white(self, device, brightness=None, colourtemp=None):
        return {"brightness": brightness, "colourtemp": colourtemp, "ip": device.ip_address}

    def set_colour_hsv(self, device, hue, saturation, value):
        return {"hsv": [hue, saturation, value], "ip": device.ip_address}

    def set_scene(self, device, scene):
        return {"scene": scene, "ip": device.ip_address}

    def set_value(self, device, dps, value):
        return {"dps": dps, "value": value, "ip": device.ip_address}

    def scan_devices(self, max_seconds=5):
        return [
            {
                "device_id": "ebdcf642f6e599f9e4v425",
                "ip_address": "192.168.40.211",
                "version": "3.3",
            }
        ]

    def get_local_network_info(self):
        return {
            "local_ip": "192.168.40.89",
            "tuya_port": 6668,
            "hostname": "test-host",
            "default_gateway": "192.168.40.1",
            "default_interface": "en0",
            "wifi_ssid": "Home WiFi",
            "active_vpn_interfaces": [],
        }

    def probe_address(self, ip_address, *, port=6668, timeout=1.5):
        del timeout
        return {"reachable": ip_address.endswith(".211"), "error": None if ip_address.endswith(".211") else "No route", "port": port}

    def run_wizard(
        self,
        cloud_config,
        *,
        credentials_file,
        device_file,
        snapshot_file,
        raw_file,
        retries=5,
        forcescan=True,
        skip_poll=False,
    ):
        del cloud_config, credentials_file, snapshot_file, raw_file, retries, forcescan, skip_poll
        return [
            {
                "name": "Living Room Top",
                "id": "ebdcf642f6e599f9e4v425",
                "key": "pzUvM:<NTy~6z[4u",
                "ip": "192.168.40.230",
                "version": "3.3",
                "productKey": "lfpa01cpai5cs0kk",
            },
            {
                "name": "Desk Lamp",
                "id": "new-desk-device",
                "key": "desk-lamp-key",
                "ip": "192.168.40.250",
                "version": "3.3",
                "productKey": "lfpa01cpai5cs0kk",
            },
        ]


class FakeCloudClient:
    """Disabled cloud client for service tests."""

    is_enabled = False
    config = None


class FakeCloudClientWithConfig:
    """Cloud client double exposing static credentials for wizard discovery tests."""

    is_enabled = True

    class _Config:
        api_key = "key"
        api_secret = "secret"
        api_region = "us"
        api_device_id = "scan"

    config = _Config()

    def get_devices(self):
        return [
            {"id": "ebdcf642f6e599f9e4v425", "name": "Living Room Top"},
            {"id": "ebe1fa3b1179117e04gszt", "name": "Living Room Bottom"},
        ]


class ServiceTests(unittest.TestCase):
    """Validate service orchestration behavior."""

    def test_status_retries_after_scan_refresh(self) -> None:
        devices = load_devices()
        devices[1].ip_address = "192.168.40.250"
        registry = DeviceRegistry(devices)
        service = SmartLightsService(
            registry=registry,
            scenes=SceneLibrary.from_config(),
            local_client=FakeLocalClient(),
            cloud_client=FakeCloudClient(),
        )

        results = service.status("living-room-top")

        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].success)
        self.assertEqual(results[0].transport, "local-refreshed")
        self.assertEqual(registry.get("living-room-top").ip_address, "192.168.40.211")

    def test_wizard_discovery_updates_registry_and_adds_new_device(self) -> None:
        devices = load_devices()
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / "devices.json"
            registry = DeviceRegistry(devices, path=registry_path)
            service = SmartLightsService(
                registry=registry,
                scenes=SceneLibrary.from_config(),
                local_client=FakeLocalClient(),
                cloud_client=FakeCloudClientWithConfig(),
            )

            result = service.discover_with_wizard(
                retries=1,
                skip_poll=True,
                credentials_path=Path(temp_dir) / "cloud.json",
                device_output_path=Path(temp_dir) / "wizard-devices.json",
                snapshot_output_path=Path(temp_dir) / "wizard-snapshot.json",
                raw_output_path=Path(temp_dir) / "wizard-raw.json",
            )

            self.assertEqual(result["wizard_devices"], 2)
            self.assertEqual(result["imported"], 2)
            self.assertEqual(registry.get("living-room-top").ip_address, "192.168.40.230")
            self.assertEqual(registry.get("new-desk-device").name, "Desk Lamp")
            self.assertTrue(registry_path.exists())

    def test_diagnose_reports_local_and_cloud_visibility(self) -> None:
        service = SmartLightsService(
            registry=DeviceRegistry(load_devices()),
            scenes=SceneLibrary.from_config(),
            local_client=FakeLocalClient(),
            cloud_client=FakeCloudClientWithConfig(),
        )

        result = service.diagnose("living-room-top")

        self.assertEqual(result["local_network"]["local_ip"], "192.168.40.89")
        self.assertEqual(result["local_scan"]["matching_targets"], 1)
        self.assertEqual(result["cloud"]["matching_targets"], 1)
        self.assertEqual(len(result["devices"]), 1)
        self.assertTrue(result["devices"][0]["tcp_probe"]["reachable"])
        self.assertTrue(result["devices"][0]["same_24_prefix_as_laptop"])
        self.assertTrue(result["local_network"]["wifi_ssid"])
        self.assertTrue(result["likely_causes"])


if __name__ == "__main__":
    unittest.main()
