"""Device inventory and lookup helpers."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import re
from typing import Iterable

from smart_lights import config as config_store
from smart_lights.models import DeviceConfig


def normalize_name(value: str) -> str:
    """Normalize names for flexible lookups."""
    return value.strip().lower().replace("_", "-").replace(" ", "-")


def slugify(value: str) -> str:
    """Create a stable slug from a device name."""
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    return cleaned.strip("-") or "unnamed-device"


def _coalesce_str(value: object, fallback: str | None) -> str | None:
    """Return a string value when present, otherwise preserve the fallback."""
    if value in (None, ""):
        return fallback
    return str(value)


class DeviceRegistry:
    """Holds configured devices and resolves names, rooms, and groups."""

    def __init__(self, devices: list[DeviceConfig], path: str | Path | None = None) -> None:
        self._devices = devices
        self._path = Path(path) if path is not None else None

    @classmethod
    def from_config(cls, path: str | Path | None = None) -> "DeviceRegistry":
        """Load the registry from the configured devices file."""
        return cls(config_store.load_devices(path), path=path)

    def all_devices(self) -> list[DeviceConfig]:
        """Return every configured device."""
        return list(self._devices)

    def get(self, target: str) -> DeviceConfig:
        """Return a single device by slug, name, or device id."""
        normalized = normalize_name(target)
        for device in self._devices:
            if normalized in {
                normalize_name(device.slug),
                normalize_name(device.name),
                normalize_name(device.device_id),
            }:
                return device
        raise KeyError(f"Unknown device target: {target}")

    def resolve(self, target: str) -> list[DeviceConfig]:
        """Resolve a target name into one or more devices."""
        normalized = normalize_name(target)
        if normalized == "all":
            return self.all_devices()

        matches: list[DeviceConfig] = []
        for device in self._devices:
            candidates = {
                normalize_name(device.slug),
                normalize_name(device.name),
                normalize_name(device.device_id),
            }
            if device.room:
                candidates.add(normalize_name(device.room))
            candidates.update(normalize_name(group) for group in device.groups)
            if normalized in candidates:
                matches.append(device)

        if matches:
            return matches
        raise KeyError(f"Unknown target: {target}")

    def update_device(self, updated: DeviceConfig) -> DeviceConfig:
        """Replace a device config in the registry."""
        for index, existing in enumerate(self._devices):
            if existing.device_id == updated.device_id:
                self._devices[index] = updated
                return updated
        raise KeyError(f"Unknown device id: {updated.device_id}")

    def refresh_from_scan(self, scanned: Iterable[dict[str, str]]) -> list[DeviceConfig]:
        """Update known devices with IP/version data from a LAN scan."""
        refreshed: list[DeviceConfig] = []
        for item in scanned:
            device_id = item.get("device_id")
            if not device_id:
                continue
            try:
                device = self.get(device_id)
            except KeyError:
                continue
            updated = replace(
                device,
                ip_address=item.get("ip_address", device.ip_address),
                version=item.get("version", device.version),
                product_key=item.get("product_key", device.product_key),
            )
            self.update_device(updated)
            refreshed.append(updated)
        return refreshed

    def refresh_from_cloud(self, cloud_devices: Iterable[dict[str, object]]) -> list[DeviceConfig]:
        """Update known devices from cloud metadata when available."""
        refreshed: list[DeviceConfig] = []
        by_id = {str(item.get("id")): item for item in cloud_devices if item.get("id")}
        for device in list(self._devices):
            cloud_item = by_id.get(device.device_id)
            if not cloud_item:
                continue
            updated = replace(
                device,
                name=_coalesce_str(cloud_item.get("name"), device.name) or device.name,
                ip_address=_coalesce_str(cloud_item.get("ip"), device.ip_address) or device.ip_address,
                local_key=_coalesce_str(cloud_item.get("local_key", cloud_item.get("key")), device.local_key)
                or device.local_key,
                product_key=_coalesce_str(
                    cloud_item.get("product_id", cloud_item.get("productKey")),
                    device.product_key,
                ),
            )
            self.update_device(updated)
            refreshed.append(updated)
        return refreshed

    def merge_tinytuya_devices(self, discovered_devices: Iterable[dict[str, object]]) -> list[DeviceConfig]:
        """Merge TinyTuya wizard output into the structured registry."""
        merged: list[DeviceConfig] = []
        for item in discovered_devices:
            device_id = _coalesce_str(item.get("id"), None)
            if not device_id:
                continue

            name = _coalesce_str(item.get("name"), device_id) or device_id
            ip_address = (
                _coalesce_str(item.get("last_ip"), None)
                or _coalesce_str(item.get("ip"), None)
                or ""
            )
            local_key = _coalesce_str(item.get("key"), "") or ""
            version = _coalesce_str(item.get("version"), "3.3") or "3.3"
            product_key = _coalesce_str(item.get("product_id", item.get("productKey")), None)
            mac = _coalesce_str(item.get("mac"), None)
            category = _coalesce_str(item.get("category"), None)

            try:
                existing = self.get(device_id)
                updated = replace(
                    existing,
                    name=name,
                    ip_address=ip_address or existing.ip_address,
                    local_key=local_key or existing.local_key,
                    version=version or existing.version,
                    product_key=product_key or existing.product_key,
                    mac=mac or existing.mac,
                    category=category or existing.category,
                )
                self.update_device(updated)
                merged.append(updated)
            except KeyError:
                new_device = DeviceConfig(
                    slug=slugify(name),
                    name=name,
                    device_id=device_id,
                    local_key=local_key,
                    ip_address=ip_address,
                    version=version,
                    product_key=product_key,
                    mac=mac,
                    category=category,
                )
                self._devices.append(new_device)
                merged.append(new_device)
        return merged

    def save(self) -> None:
        """Persist the current registry back to disk."""
        config_store.save_devices(self._devices, self._path)
