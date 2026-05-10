"""Tests for service layer orchestration and fallback behavior."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import pytest

from smart_lights.models import CloudConfig, DeviceConfig
from smart_lights.registry import DeviceRegistry
from smart_lights.scenes import SceneLibrary
from smart_lights.service import SmartLightsService


class FakeLocalClient:
    """Test double that simulates connectivity behavior."""

    def __init__(self, stale_ip: str = "192.168.1.99") -> None:
        self._stale_ip = stale_ip

    def status(self, device: DeviceConfig) -> dict[str, Any]:
        if device.ip_address == self._stale_ip:
            return {"Err": "901", "Error": "Network Error: Unable to Connect"}
        return {"dps": {"20": True, "21": "white", "22": 1000}}

    def turn_on(self, device: DeviceConfig) -> dict[str, Any]:
        return {"dps": {"20": True}}

    def turn_off(self, device: DeviceConfig) -> dict[str, Any]:
        return {"dps": {"20": False}}

    def set_mode(self, device: DeviceConfig, mode: str) -> dict[str, Any]:
        return {"dps": {"21": mode}}

    def set_brightness(self, device: DeviceConfig, brightness: int) -> dict[str, Any]:
        return {"dps": {"22": brightness}}

    def set_white(self, device: DeviceConfig, brightness: int | None = None, colourtemp: int | None = None) -> dict[str, Any]:
        return {"dps": {"21": "white", "22": brightness, "23": colourtemp}}

    def set_colour_hsv(self, device: DeviceConfig, hue: int, saturation: int, value: int) -> dict[str, Any]:
        return {"dps": {"21": "colour", "24": f"{hue:04x}{saturation:04x}{value:04x}"}}

    def set_scene(self, device: DeviceConfig, scene: int | str) -> dict[str, Any]:
        return {"dps": {"25": scene}}

    def set_value(self, device: DeviceConfig, dps: int, value: Any) -> dict[str, Any]:
        return {"dps": {str(dps): value}}

    def scan_devices(self, max_seconds: int = 5) -> list[dict[str, Any]]:
        return [
            {"device_id": "dev001", "ip_address": "192.168.1.10", "version": "3.3"},
            {"device_id": "dev002", "ip_address": "192.168.1.11", "version": "3.3"},
        ]

    def get_local_network_info(self) -> dict[str, Any]:
        return {
            "local_ip": "192.168.1.100",
            "tuya_port": 6668,
            "hostname": "test-host",
            "default_gateway": "192.168.1.1",
            "default_interface": "en0",
            "wifi_ssid": "TestNetwork",
            "active_vpn_interfaces": [],
        }

    def probe_address(self, ip_address: str, *, port: int = 6668, timeout: float = 1.5) -> dict[str, Any]:
        return {"reachable": True, "error": None, "port": port}

    def run_wizard(self, cloud_config: Any, **kwargs: Any) -> list[dict[str, Any]]:
        return [
            {"name": "Living Room Top", "id": "dev001", "key": "updated-key", "ip": "192.168.1.200", "version": "3.3"},
            {"name": "New Device", "id": "dev-new", "key": "new-key", "ip": "192.168.1.201", "version": "3.3"},
        ]


class FakeCloudClient:
    """Disabled cloud client."""

    is_enabled = False
    config = None

    def get_devices(self) -> list[dict[str, Any]]:
        return []


class FakeCloudClientWithConfig:
    """Cloud client with credentials for wizard tests."""

    is_enabled = True
    config = CloudConfig(api_key="key", api_secret="secret", api_region="us", api_device_id="scan")

    def get_devices(self) -> list[dict[str, Any]]:
        return [
            {"id": "dev001", "name": "Living Room Top"},
            {"id": "dev002", "name": "Living Room Bottom"},
        ]


@pytest.fixture
def service(devices: list[DeviceConfig], scene_library: SceneLibrary) -> SmartLightsService:
    return SmartLightsService(
        registry=DeviceRegistry(devices),
        scenes=scene_library,
        local_client=FakeLocalClient(),
        cloud_client=FakeCloudClient(),
    )


def test_status_returns_results_for_all_devices(service: SmartLightsService) -> None:
    results = service.status("all")
    assert len(results) == 3
    assert all(r.success for r in results)


def test_status_single_device(service: SmartLightsService) -> None:
    results = service.status("living-room-top")
    assert len(results) == 1
    assert results[0].target == "living-room-top"
    assert results[0].success


def test_turn_on(service: SmartLightsService) -> None:
    results = service.turn_on("living-room-top")
    assert len(results) == 1
    assert results[0].success
    assert results[0].transport == "local"


def test_turn_off(service: SmartLightsService) -> None:
    results = service.turn_off("living-room-top")
    assert results[0].success


def test_set_brightness(service: SmartLightsService) -> None:
    results = service.set_brightness("living-room-top", 75)
    assert results[0].success


def test_set_white(service: SmartLightsService) -> None:
    results = service.set_white("living-room-top", brightness=80, colourtemp=50)
    assert results[0].success


def test_set_colour(service: SmartLightsService) -> None:
    results = service.set_colour("living-room-top", 120, 800, 600)
    assert results[0].success


def test_apply_scene(service: SmartLightsService) -> None:
    results = service.apply_scene("all-off")
    assert len(results) >= 1
    assert all(r.success for r in results)


def test_status_retries_after_stale_ip(
    devices: list[DeviceConfig], scene_library: SceneLibrary
) -> None:
    devices[0].ip_address = "192.168.1.99"
    registry = DeviceRegistry(devices)
    service = SmartLightsService(
        registry=registry,
        scenes=scene_library,
        local_client=FakeLocalClient(stale_ip="192.168.1.99"),
        cloud_client=FakeCloudClient(),
    )

    results = service.status("living-room-top")
    assert len(results) == 1
    assert results[0].success
    assert results[0].transport == "local-refreshed"
    assert registry.get("living-room-top").ip_address == "192.168.1.10"


def test_wizard_discovery_imports_devices(
    devices: list[DeviceConfig], scene_library: SceneLibrary
) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        registry = DeviceRegistry(devices, path=tmp_path / "devices.json")
        service = SmartLightsService(
            registry=registry,
            scenes=scene_library,
            local_client=FakeLocalClient(),
            cloud_client=FakeCloudClientWithConfig(),
        )

        result = service.discover_with_wizard(
            retries=1,
            skip_poll=True,
            credentials_path=tmp_path / "cloud.json",
            device_output_path=tmp_path / "wizard-devices.json",
            snapshot_output_path=tmp_path / "wizard-snapshot.json",
            raw_output_path=tmp_path / "wizard-raw.json",
        )

        assert result["wizard_devices"] == 2
        assert result["imported"] == 2
        assert registry.get("living-room-top").ip_address == "192.168.1.200"
        assert registry.get("dev-new").name == "New Device"


def test_diagnose_returns_structured_report(service: SmartLightsService) -> None:
    result = service.diagnose("living-room-top")
    assert "local_network" in result
    assert "local_scan" in result
    assert "cloud" in result
    assert "devices" in result
    assert "likely_causes" in result
    assert result["local_network"]["local_ip"] == "192.168.1.100"
    assert len(result["devices"]) == 1


def test_list_devices(service: SmartLightsService) -> None:
    devices = service.list_devices()
    assert len(devices) == 3


def test_list_scene_names(service: SmartLightsService) -> None:
    names = service.list_scene_names()
    assert "movie-time" in names
    assert "party" in names
