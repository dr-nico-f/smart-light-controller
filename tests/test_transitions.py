"""Tests for lighting transition functions."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from smart_lights.models import DeviceConfig, DeviceDpsConfig
from smart_lights.transitions import _lerp, breathe, fade_brightness


def _make_device() -> DeviceConfig:
    return DeviceConfig(
        slug="test-bulb",
        name="Test Bulb",
        device_id="dev-test",
        local_key="test-key",
        ip_address="192.168.1.1",
        dps=DeviceDpsConfig(),
    )


def _make_client() -> MagicMock:
    client = MagicMock()
    client.set_brightness.return_value = {"dps": {"22": 100}}
    return client


def test_lerp_basic() -> None:
    assert _lerp(0, 100, 0.0) == 0
    assert _lerp(0, 100, 1.0) == 100
    assert _lerp(0, 100, 0.5) == 50


def test_lerp_reverse() -> None:
    assert _lerp(100, 0, 0.5) == 50


def test_fade_brightness_calls_client(monkeypatch: Any) -> None:
    import smart_lights.transitions as mod
    monkeypatch.setattr(mod.time, "sleep", lambda _: None)

    device = _make_device()
    client = _make_client()

    result = fade_brightness(device, client, start=0, end=100, duration=1.0, steps=5)

    assert result["final_brightness"] == 100
    assert result["steps"] == 5
    assert client.set_brightness.call_count == 6  # 0..5 inclusive


def test_breathe_completes_cycles(monkeypatch: Any) -> None:
    import smart_lights.transitions as mod
    monkeypatch.setattr(mod.time, "sleep", lambda _: None)

    device = _make_device()
    client = _make_client()

    result = breathe(device, client, low=10, high=100, cycle_duration=1.0, cycles=2, steps_per_half=5)

    assert result["cycles"] == 2
    assert client.set_brightness.call_count == 2 * 2 * 6  # 2 cycles, 2 halves, 6 steps each
