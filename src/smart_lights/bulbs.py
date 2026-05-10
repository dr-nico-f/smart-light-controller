"""High-level bulb operations built on TinyTuya."""

from __future__ import annotations

from typing import Any

from smart_lights.models import DeviceConfig
from smart_lights.tuya_client import LocalTuyaClient


class TuyaBulbController:
    """High-level operations for a single Tuya bulb."""

    def __init__(self, device: DeviceConfig, client: LocalTuyaClient | None = None) -> None:
        self.device = device
        self.client = client or LocalTuyaClient()

    def get_status(self) -> dict[str, Any]:
        """Return the current device status."""
        return self.client.status(self.device)

    def turn_on(self) -> dict[str, Any]:
        """Power the bulb on."""
        return self.client.turn_on(self.device)

    def turn_off(self) -> dict[str, Any]:
        """Power the bulb off."""
        return self.client.turn_off(self.device)

    def set_mode(self, mode: str) -> dict[str, Any]:
        """Set the device mode."""
        return self.client.set_mode(self.device, mode)

    def set_brightness(self, brightness: int) -> dict[str, Any]:
        """Set brightness as a percentage from 0-100."""
        return self.client.set_brightness(self.device, brightness)

    def set_white(
        self,
        brightness: int | None = None,
        colourtemp: int | None = None,
    ) -> dict[str, Any]:
        """Set white mode with optional brightness and colour temperature percentages."""
        return self.client.set_white(self.device, brightness=brightness, colourtemp=colourtemp)

    def set_colour_hsv(self, hue: int, saturation: int, value: int) -> dict[str, Any]:
        """Set colour using hue 0-360 and saturation/value 0-1000."""
        return self.client.set_colour_hsv(self.device, hue, saturation, value)

    def set_scene(self, scene: int | str) -> dict[str, Any]:
        """Set a built-in scene on the bulb."""
        return self.client.set_scene(self.device, scene)

    def set_raw_dps(self, dps: int, value: Any) -> dict[str, Any]:
        """Send a raw DPS value for exact control."""
        return self.client.set_value(self.device, dps, value)
