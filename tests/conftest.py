"""Shared pytest fixtures for smart_lights tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from smart_lights.config import load_cloud_config, load_devices, load_scenes
from smart_lights.models import CloudConfig, DeviceConfig, SceneConfig
from smart_lights.registry import DeviceRegistry
from smart_lights.scenes import SceneLibrary

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture
def devices(fixtures_dir: Path) -> list[DeviceConfig]:
    return load_devices(fixtures_dir / "devices.json")


@pytest.fixture
def cloud_config(fixtures_dir: Path) -> CloudConfig:
    return load_cloud_config(fixtures_dir / "cloud.json")


@pytest.fixture
def scenes(fixtures_dir: Path) -> list[SceneConfig]:
    return load_scenes(fixtures_dir / "scenes.json")


@pytest.fixture
def registry(devices: list[DeviceConfig]) -> DeviceRegistry:
    return DeviceRegistry(devices)


@pytest.fixture
def scene_library(fixtures_dir: Path) -> SceneLibrary:
    return SceneLibrary.from_config(fixtures_dir / "scenes.json")
