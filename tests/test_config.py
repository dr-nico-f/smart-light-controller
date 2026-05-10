"""Tests for configuration loading."""

from __future__ import annotations

from pathlib import Path

from smart_lights.config import load_cloud_config, load_devices, load_scenes
from smart_lights.models import CloudConfig, DeviceConfig, SceneConfig


def test_load_devices(fixtures_dir: Path) -> None:
    devices = load_devices(fixtures_dir / "devices.json")
    assert len(devices) == 3
    assert devices[0].dps.switch == 20
    assert devices[0].slug == "living-room-top"


def test_load_devices_returns_typed_models(fixtures_dir: Path) -> None:
    devices = load_devices(fixtures_dir / "devices.json")
    assert all(isinstance(d, DeviceConfig) for d in devices)


def test_load_cloud_config(fixtures_dir: Path) -> None:
    cloud = load_cloud_config(fixtures_dir / "cloud.json")
    assert isinstance(cloud, CloudConfig)
    assert cloud.api_region == "us"
    assert cloud.api_device_id == "scan"


def test_load_scenes(fixtures_dir: Path) -> None:
    scenes = load_scenes(fixtures_dir / "scenes.json")
    assert len(scenes) >= 3
    assert scenes[0].name == "all-off"
    assert all(isinstance(s, SceneConfig) for s in scenes)
