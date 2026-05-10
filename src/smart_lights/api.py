"""HTTP API server exposing the smart lights service layer."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from smart_lights.colours import list_presets, resolve_colour
from smart_lights.service import SmartLightsService

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(
    title="Smart Light Controller",
    description="Local-first HTTP API for controlling Tuya RGBCW smart bulbs.",
    version="1.0.0",
)

_service: SmartLightsService | None = None


def get_service() -> SmartLightsService:
    global _service
    if _service is None:
        _service = SmartLightsService.from_config()
    return _service


class BrightnessRequest(BaseModel):
    brightness: int


class WhiteRequest(BaseModel):
    brightness: int | None = None
    colourtemp: int | None = None


class ColourRequest(BaseModel):
    hue: int | None = None
    saturation: int | None = None
    value: int | None = None
    preset: str | None = None


class FadeRequest(BaseModel):
    brightness: int
    start: int = 0
    duration: float = 3.0
    steps: int = 20


class BreatheRequest(BaseModel):
    low: int = 10
    high: int = 100
    cycles: int = 3
    cycle_duration: float = 4.0


def _format_results(results: list[Any]) -> list[dict[str, Any]]:
    return [
        {"target": r.target, "success": r.success, "transport": r.transport, "response": r.response}
        for r in results
    ]


@app.get("/devices")
def list_devices() -> list[dict[str, Any]]:
    """List all configured devices."""
    service = get_service()
    return [
        {"slug": d.slug, "name": d.name, "ip_address": d.ip_address, "room": d.room, "groups": d.groups}
        for d in service.list_devices()
    ]


@app.get("/scenes")
def list_scenes() -> list[str]:
    """List available scene names."""
    return get_service().list_scene_names()


@app.get("/colours")
def list_colours() -> list[dict[str, Any]]:
    """List available colour presets."""
    return [
        {"name": p.name, "hue": p.hue, "saturation": p.saturation, "value": p.value}
        for p in list_presets()
    ]


@app.get("/devices/{target}/status")
def device_status(target: str) -> list[dict[str, Any]]:
    """Get status for a device or group."""
    try:
        return _format_results(get_service().status(target))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/devices/{target}/on")
def turn_on(target: str) -> list[dict[str, Any]]:
    """Turn on a device or group."""
    try:
        return _format_results(get_service().turn_on(target))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/devices/{target}/off")
def turn_off(target: str) -> list[dict[str, Any]]:
    """Turn off a device or group."""
    try:
        return _format_results(get_service().turn_off(target))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/devices/{target}/brightness")
def set_brightness(target: str, body: BrightnessRequest) -> list[dict[str, Any]]:
    """Set brightness for a device or group."""
    try:
        return _format_results(get_service().set_brightness(target, body.brightness))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/devices/{target}/white")
def set_white(target: str, body: WhiteRequest) -> list[dict[str, Any]]:
    """Set white mode for a device or group."""
    try:
        return _format_results(get_service().set_white(target, brightness=body.brightness, colourtemp=body.colourtemp))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/devices/{target}/colour")
def set_colour(target: str, body: ColourRequest) -> list[dict[str, Any]]:
    """Set colour by preset name or raw HSV."""
    service = get_service()
    try:
        if body.preset:
            preset = resolve_colour(body.preset)
            return _format_results(service.set_colour(target, preset.hue, preset.saturation, preset.value))
        elif body.hue is not None and body.saturation is not None and body.value is not None:
            return _format_results(service.set_colour(target, body.hue, body.saturation, body.value))
        else:
            raise HTTPException(status_code=400, detail="Provide 'preset' or 'hue'+'saturation'+'value'")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/devices/{target}/fade")
def fade(target: str, body: FadeRequest) -> list[dict[str, Any]]:
    """Smoothly fade brightness over time."""
    from smart_lights.transitions import fade_brightness
    service = get_service()
    try:
        devices = service.registry.resolve(target)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    results = []
    for device in devices:
        result = fade_brightness(
            device, service.local_client,
            start=body.start, end=body.brightness,
            duration=body.duration, steps=body.steps,
        )
        results.append({"target": device.slug, **result})
    return results


@app.post("/devices/{target}/breathe")
def breathe_endpoint(target: str, body: BreatheRequest) -> list[dict[str, Any]]:
    """Pulse brightness in a breathing pattern."""
    from smart_lights.transitions import breathe
    service = get_service()
    try:
        devices = service.registry.resolve(target)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    results = []
    for device in devices:
        result = breathe(
            device, service.local_client,
            low=body.low, high=body.high,
            cycle_duration=body.cycle_duration, cycles=body.cycles,
        )
        results.append({"target": device.slug, **result})
    return results


@app.post("/scenes/{name}")
def apply_scene(name: str) -> list[dict[str, Any]]:
    """Apply a configured scene."""
    try:
        return _format_results(get_service().apply_scene(name))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/diagnose/{target}")
def diagnose(target: str = "all") -> dict[str, Any]:
    """Run network diagnostics for a device or group."""
    try:
        return get_service().diagnose(target)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/", include_in_schema=False)
def dashboard() -> FileResponse:
    """Serve the web dashboard."""
    return FileResponse(STATIC_DIR / "index.html")
