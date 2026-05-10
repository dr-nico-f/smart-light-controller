"""Smooth lighting transitions (fade, breathe) over time."""

from __future__ import annotations

import time
import threading
from typing import Any, Callable

from smart_lights.models import DeviceConfig
from smart_lights.tuya_client import LocalTuyaClient


StepCallback = Callable[[int], None]


def _lerp(start: int, end: int, t: float) -> int:
    """Linear interpolation between two integers."""
    return int(start + (end - start) * t)


def fade_brightness(
    device: DeviceConfig,
    client: LocalTuyaClient,
    *,
    start: int,
    end: int,
    duration: float,
    steps: int = 20,
    on_step: StepCallback | None = None,
) -> dict[str, Any]:
    """Smoothly transition brightness from start to end over duration seconds."""
    interval = duration / steps
    for i in range(steps + 1):
        t = i / steps
        brightness = _lerp(start, end, t)
        client.set_brightness(device, brightness)
        if on_step:
            on_step(brightness)
        if i < steps:
            time.sleep(interval)
    return {"final_brightness": end, "steps": steps, "duration": duration}


def fade_colour(
    device: DeviceConfig,
    client: LocalTuyaClient,
    *,
    start_hsv: tuple[int, int, int],
    end_hsv: tuple[int, int, int],
    duration: float,
    steps: int = 20,
) -> dict[str, Any]:
    """Smoothly transition colour from start HSV to end HSV over duration seconds."""
    interval = duration / steps
    for i in range(steps + 1):
        t = i / steps
        hue = _lerp(start_hsv[0], end_hsv[0], t)
        sat = _lerp(start_hsv[1], end_hsv[1], t)
        val = _lerp(start_hsv[2], end_hsv[2], t)
        client.set_colour_hsv(device, hue, sat, val)
        if i < steps:
            time.sleep(interval)
    return {"final_hsv": list(end_hsv), "steps": steps, "duration": duration}


def breathe(
    device: DeviceConfig,
    client: LocalTuyaClient,
    *,
    low: int = 10,
    high: int = 100,
    cycle_duration: float = 4.0,
    cycles: int = 3,
    steps_per_half: int = 15,
) -> dict[str, Any]:
    """Pulse brightness up and down in a breathing pattern."""
    half_interval = (cycle_duration / 2) / steps_per_half
    for cycle in range(cycles):
        for i in range(steps_per_half + 1):
            t = i / steps_per_half
            brightness = _lerp(low, high, t)
            client.set_brightness(device, brightness)
            if i < steps_per_half:
                time.sleep(half_interval)
        for i in range(steps_per_half + 1):
            t = i / steps_per_half
            brightness = _lerp(high, low, t)
            client.set_brightness(device, brightness)
            if i < steps_per_half:
                time.sleep(half_interval)
    return {"cycles": cycles, "low": low, "high": high, "duration": cycle_duration * cycles}


def fade_brightness_async(
    device: DeviceConfig,
    client: LocalTuyaClient,
    *,
    start: int,
    end: int,
    duration: float,
    steps: int = 20,
) -> threading.Thread:
    """Run a brightness fade in a background thread."""
    thread = threading.Thread(
        target=fade_brightness,
        kwargs={"device": device, "client": client, "start": start, "end": end, "duration": duration, "steps": steps},
        daemon=True,
    )
    thread.start()
    return thread
