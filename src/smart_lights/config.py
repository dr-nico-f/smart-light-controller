"""Configuration loading helpers for the smart lights app."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from smart_lights.models import AutomationRule, CloudConfig, DeviceConfig, SceneConfig


PACKAGE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_ROOT.parents[1]
CONFIG_DIR = REPO_ROOT / "config"
DEFAULT_DEVICES_PATH = CONFIG_DIR / "devices.json"
DEFAULT_CLOUD_PATH = CONFIG_DIR / "cloud.json"
DEFAULT_SCENES_PATH = CONFIG_DIR / "scenes.json"
DEFAULT_AUTOMATIONS_PATH = CONFIG_DIR / "automations.json"
DEFAULT_WIZARD_DEVICES_PATH = CONFIG_DIR / "wizard-devices.json"
DEFAULT_WIZARD_SNAPSHOT_PATH = CONFIG_DIR / "wizard-snapshot.json"
DEFAULT_WIZARD_RAW_PATH = CONFIG_DIR / "wizard-raw.json"


def load_json_file(path: Path) -> Any:
    """Load raw JSON content from a file path."""
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json_file(path: Path, payload: Any) -> None:
    """Write JSON content to disk with stable formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def get_devices_path(path: str | Path | None = None) -> Path:
    """Resolve the device config file path."""
    if path is not None:
        return Path(path)
    return Path(os.environ.get("SMART_LIGHTS_DEVICES_PATH", DEFAULT_DEVICES_PATH))


def get_cloud_path(path: str | Path | None = None) -> Path:
    """Resolve the cloud config file path."""
    if path is not None:
        return Path(path)
    return Path(os.environ.get("SMART_LIGHTS_CLOUD_PATH", DEFAULT_CLOUD_PATH))


def get_scenes_path(path: str | Path | None = None) -> Path:
    """Resolve the scenes config file path."""
    if path is not None:
        return Path(path)
    return Path(os.environ.get("SMART_LIGHTS_SCENES_PATH", DEFAULT_SCENES_PATH))


def get_automations_path(path: str | Path | None = None) -> Path:
    """Resolve the automation config file path."""
    if path is not None:
        return Path(path)
    return Path(os.environ.get("SMART_LIGHTS_AUTOMATIONS_PATH", DEFAULT_AUTOMATIONS_PATH))


def get_wizard_devices_path(path: str | Path | None = None) -> Path:
    """Resolve the TinyTuya wizard device output file path."""
    if path is not None:
        return Path(path)
    return Path(os.environ.get("SMART_LIGHTS_WIZARD_DEVICES_PATH", DEFAULT_WIZARD_DEVICES_PATH))


def get_wizard_snapshot_path(path: str | Path | None = None) -> Path:
    """Resolve the TinyTuya wizard snapshot output file path."""
    if path is not None:
        return Path(path)
    return Path(os.environ.get("SMART_LIGHTS_WIZARD_SNAPSHOT_PATH", DEFAULT_WIZARD_SNAPSHOT_PATH))


def get_wizard_raw_path(path: str | Path | None = None) -> Path:
    """Resolve the TinyTuya wizard raw response output file path."""
    if path is not None:
        return Path(path)
    return Path(os.environ.get("SMART_LIGHTS_WIZARD_RAW_PATH", DEFAULT_WIZARD_RAW_PATH))


def load_devices(path: str | Path | None = None) -> list[DeviceConfig]:
    """Load the configured smart lights inventory."""
    payload = load_json_file(get_devices_path(path))
    return [DeviceConfig.from_dict(item) for item in payload["devices"]]


def save_devices(devices: list[DeviceConfig], path: str | Path | None = None) -> None:
    """Persist the smart lights inventory back to disk."""
    payload = {"devices": [device.to_dict() for device in devices]}
    write_json_file(get_devices_path(path), payload)


def load_cloud_config(path: str | Path | None = None) -> CloudConfig:
    """Load Tuya cloud credentials from disk."""
    payload = load_json_file(get_cloud_path(path))
    return CloudConfig.from_dict(payload)


def load_scenes(path: str | Path | None = None) -> list[SceneConfig]:
    """Load scene definitions from disk."""
    payload = load_json_file(get_scenes_path(path))
    return [SceneConfig.from_dict(item) for item in payload.get("scenes", [])]


def load_automation_rules(path: str | Path | None = None) -> list[AutomationRule]:
    """Load automation rules when a config file exists."""
    config_path = get_automations_path(path)
    if not config_path.exists():
        return []
    payload = load_json_file(config_path)
    return [AutomationRule.from_dict(item) for item in payload.get("automations", [])]
