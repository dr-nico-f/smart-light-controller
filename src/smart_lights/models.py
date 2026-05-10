"""Typed models for smart light configuration and actions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class DeviceDpsConfig:
    """DPS indexes for a Tuya bulb profile."""

    switch: int = 20
    mode: int = 21
    brightness: int = 22
    colourtemp: int = 23
    colour: int = 24
    scene: int = 25
    timer: int = 26
    music: int = 28

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "DeviceDpsConfig":
        """Build a DPS mapping from JSON data."""
        return cls(**(data or {}))


@dataclass(slots=True)
class DeviceConfig:
    """Configuration for one physical smart light."""

    slug: str
    name: str
    device_id: str
    local_key: str
    ip_address: str
    version: str = "3.3"
    product_key: str | None = None
    mac: str | None = None
    category: str | None = None
    room: str | None = None
    groups: list[str] = field(default_factory=list)
    dps: DeviceDpsConfig = field(default_factory=DeviceDpsConfig)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DeviceConfig":
        """Build a device config from JSON data."""
        return cls(
            slug=data["slug"],
            name=data["name"],
            device_id=data["device_id"],
            local_key=data["local_key"],
            ip_address=data["ip_address"],
            version=data.get("version", "3.3"),
            product_key=data.get("product_key"),
            mac=data.get("mac"),
            category=data.get("category"),
            room=data.get("room"),
            groups=list(data.get("groups", [])),
            dps=DeviceDpsConfig.from_dict(data.get("dps")),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert the config back into JSON-friendly data."""
        return {
            "slug": self.slug,
            "name": self.name,
            "device_id": self.device_id,
            "local_key": self.local_key,
            "ip_address": self.ip_address,
            "version": self.version,
            "product_key": self.product_key,
            "mac": self.mac,
            "category": self.category,
            "room": self.room,
            "groups": self.groups,
            "dps": {
                "switch": self.dps.switch,
                "mode": self.dps.mode,
                "brightness": self.dps.brightness,
                "colourtemp": self.dps.colourtemp,
                "colour": self.dps.colour,
                "scene": self.dps.scene,
                "timer": self.dps.timer,
                "music": self.dps.music,
            },
        }


@dataclass(slots=True)
class CloudConfig:
    """Tuya cloud API credentials."""

    api_key: str
    api_secret: str
    api_region: str
    api_device_id: str = "scan"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CloudConfig":
        """Build cloud config from JSON data."""
        return cls(
            api_key=data["apiKey"],
            api_secret=data["apiSecret"],
            api_region=data["apiRegion"],
            api_device_id=data.get("apiDeviceID", "scan"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert config to the TinyTuya cloud JSON format."""
        return {
            "apiKey": self.api_key,
            "apiSecret": self.api_secret,
            "apiRegion": self.api_region,
            "apiDeviceID": self.api_device_id,
        }


@dataclass(slots=True)
class LightAction:
    """Declarative action that can be applied to one or more bulbs."""

    target: str
    power: bool | None = None
    brightness: int | None = None
    colourtemp: int | None = None
    hsv: tuple[int, int, int] | None = None
    mode: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LightAction":
        """Build an action from JSON data."""
        hsv = data.get("hsv")
        return cls(
            target=data["target"],
            power=data.get("power"),
            brightness=data.get("brightness"),
            colourtemp=data.get("colourtemp"),
            hsv=tuple(hsv) if hsv is not None else None,
            mode=data.get("mode"),
        )


@dataclass(slots=True)
class SceneConfig:
    """Reusable scene definition composed of one or more actions."""

    name: str
    description: str
    actions: list[LightAction]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SceneConfig":
        """Build a scene from JSON data."""
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            actions=[LightAction.from_dict(item) for item in data.get("actions", [])],
        )


@dataclass(slots=True)
class AutomationTrigger:
    """Future-facing trigger definition for automation hooks."""

    kind: str
    value: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AutomationTrigger":
        """Build a trigger from JSON data."""
        return cls(kind=data["kind"], value=data["value"])


@dataclass(slots=True)
class AutomationRule:
    """Associates an automation trigger with a scene or command target."""

    name: str
    description: str
    trigger: AutomationTrigger
    scene: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AutomationRule":
        """Build an automation rule from JSON data."""
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            trigger=AutomationTrigger.from_dict(data["trigger"]),
            scene=data["scene"],
        )


@dataclass(slots=True)
class CommandResult:
    """Normalized command response returned by the service layer."""

    target: str
    success: bool
    response: dict[str, Any]
    transport: str

