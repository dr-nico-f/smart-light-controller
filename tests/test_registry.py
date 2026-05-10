"""Tests for device registry targeting and lookup."""

from __future__ import annotations

import pytest

from smart_lights.models import DeviceConfig
from smart_lights.registry import DeviceRegistry, normalize_name, slugify


def test_resolve_all(registry: DeviceRegistry) -> None:
    assert len(registry.resolve("all")) == 3


def test_resolve_room(registry: DeviceRegistry) -> None:
    devices = registry.resolve("living-room")
    assert len(devices) == 3


def test_resolve_group(registry: DeviceRegistry) -> None:
    devices = registry.resolve("ceiling")
    assert len(devices) == 2


def test_resolve_single_device_by_slug(registry: DeviceRegistry) -> None:
    device = registry.get("living-room-top")
    assert device.device_id == "dev001"


def test_resolve_unknown_target_raises(registry: DeviceRegistry) -> None:
    with pytest.raises(KeyError, match="Unknown target"):
        registry.resolve("nonexistent")


def test_normalize_name() -> None:
    assert normalize_name("Living Room Top") == "living-room-top"
    assert normalize_name("LIVING_ROOM_TOP") == "living-room-top"


def test_slugify() -> None:
    assert slugify("Living Room Top") == "living-room-top"
    assert slugify("  Multiple   Spaces  ") == "multiple-spaces"


def test_refresh_from_scan_updates_ip(registry: DeviceRegistry) -> None:
    scanned = [{"device_id": "dev001", "ip_address": "192.168.1.99", "version": "3.3"}]
    refreshed = registry.refresh_from_scan(scanned)
    assert len(refreshed) == 1
    assert registry.get("living-room-top").ip_address == "192.168.1.99"


def test_refresh_from_scan_ignores_unknown_devices(registry: DeviceRegistry) -> None:
    scanned = [{"device_id": "unknown-id", "ip_address": "192.168.1.50", "version": "3.3"}]
    refreshed = registry.refresh_from_scan(scanned)
    assert len(refreshed) == 0


def test_merge_tinytuya_devices_adds_new(registry: DeviceRegistry) -> None:
    discovered = [
        {"name": "New Bulb", "id": "dev-new", "key": "new-key", "ip": "192.168.1.50", "version": "3.3"},
    ]
    merged = registry.merge_tinytuya_devices(discovered)
    assert len(merged) == 1
    assert registry.get("dev-new").name == "New Bulb"


def test_merge_tinytuya_devices_updates_existing(registry: DeviceRegistry) -> None:
    discovered = [
        {"name": "Living Room Top", "id": "dev001", "key": "updated-key", "ip": "192.168.1.200", "version": "3.4"},
    ]
    merged = registry.merge_tinytuya_devices(discovered)
    assert len(merged) == 1
    device = registry.get("living-room-top")
    assert device.ip_address == "192.168.1.200"
    assert device.local_key == "updated-key"
