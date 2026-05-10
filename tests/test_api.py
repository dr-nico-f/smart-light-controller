"""Tests for the HTTP API endpoints."""

from __future__ import annotations

from typing import Any

import pytest

try:
    import fastapi  # noqa: F401
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

pytestmark = pytest.mark.skipif(not HAS_FASTAPI, reason="fastapi not installed (install with .[api])")

from smart_lights.models import DeviceConfig, DeviceDpsConfig


@pytest.fixture
def client():
    """Create a FastAPI test client with a mocked service."""
    from fastapi.testclient import TestClient
    from smart_lights import api as api_module
    from smart_lights.api import app
    from smart_lights.registry import DeviceRegistry
    from smart_lights.scenes import SceneLibrary
    from smart_lights.service import SmartLightsService

    devices = [
        DeviceConfig(
            slug="test-bulb", name="Test Bulb", device_id="dev-test",
            local_key="key", ip_address="192.168.1.1", room="office",
            groups=["desk"], dps=DeviceDpsConfig(),
        ),
    ]

    class FakeLocal:
        def status(self, device: Any) -> dict:
            return {"dps": {"20": True}}
        def turn_on(self, device: Any) -> dict:
            return {"dps": {"20": True}}
        def turn_off(self, device: Any) -> dict:
            return {"dps": {"20": False}}
        def set_brightness(self, device: Any, brightness: int) -> dict:
            return {"dps": {"22": brightness}}
        def set_white(self, device: Any, **kwargs: Any) -> dict:
            return {"dps": {"21": "white"}}
        def set_colour_hsv(self, device: Any, h: int, s: int, v: int) -> dict:
            return {"dps": {"24": f"{h}{s}{v}"}}
        def set_mode(self, device: Any, mode: str) -> dict:
            return {"dps": {"21": mode}}
        def set_value(self, device: Any, dps: int, value: Any) -> dict:
            return {"dps": {str(dps): value}}
        def scan_devices(self, max_seconds: int = 5) -> list:
            return []
        def get_local_network_info(self) -> dict:
            return {"local_ip": "192.168.1.100"}
        def probe_address(self, ip: str, **kwargs: Any) -> dict:
            return {"reachable": True, "error": None, "port": 6668}

    class FakeCloud:
        is_enabled = False
        config = None
        def get_devices(self) -> list:
            return []

    from pathlib import Path
    fixtures_dir = Path(__file__).parent / "fixtures"
    service = SmartLightsService(
        registry=DeviceRegistry(devices),
        scenes=SceneLibrary.from_config(fixtures_dir / "scenes.json"),
        local_client=FakeLocal(),
        cloud_client=FakeCloud(),
    )
    api_module._service = service
    yield TestClient(app)
    api_module._service = None


def test_list_devices(client: Any) -> None:
    resp = client.get("/devices")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["slug"] == "test-bulb"


def test_list_scenes(client: Any) -> None:
    resp = client.get("/scenes")
    assert resp.status_code == 200
    assert "movie-time" in resp.json()


def test_list_colours(client: Any) -> None:
    resp = client.get("/colours")
    assert resp.status_code == 200
    assert len(resp.json()) >= 20


def test_device_status(client: Any) -> None:
    resp = client.get("/devices/test-bulb/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data[0]["success"] is True


def test_turn_on(client: Any) -> None:
    resp = client.post("/devices/test-bulb/on")
    assert resp.status_code == 200
    assert resp.json()[0]["success"] is True


def test_turn_off(client: Any) -> None:
    resp = client.post("/devices/test-bulb/off")
    assert resp.status_code == 200


def test_set_brightness(client: Any) -> None:
    resp = client.post("/devices/test-bulb/brightness", json={"brightness": 75})
    assert resp.status_code == 200


def test_set_colour_by_preset(client: Any) -> None:
    resp = client.post("/devices/test-bulb/colour", json={"preset": "ocean-blue"})
    assert resp.status_code == 200


def test_set_colour_by_hsv(client: Any) -> None:
    resp = client.post("/devices/test-bulb/colour", json={"hue": 120, "saturation": 800, "value": 600})
    assert resp.status_code == 200


def test_unknown_device_returns_404(client: Any) -> None:
    resp = client.get("/devices/nonexistent/status")
    assert resp.status_code == 404


def test_apply_scene(client: Any) -> None:
    resp = client.post("/scenes/all-off")
    assert resp.status_code == 200
