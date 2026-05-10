"""Named colour presets for human-friendly CLI usage."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ColourPreset:
    """An HSV colour preset with a human-readable name."""

    name: str
    hue: int
    saturation: int
    value: int


PRESETS: dict[str, ColourPreset] = {p.name: p for p in [
    ColourPreset("red", 0, 1000, 1000),
    ColourPreset("orange", 30, 1000, 1000),
    ColourPreset("sunset-orange", 20, 900, 800),
    ColourPreset("yellow", 60, 1000, 1000),
    ColourPreset("warm-white", 40, 200, 1000),
    ColourPreset("green", 120, 1000, 1000),
    ColourPreset("cyan", 180, 1000, 1000),
    ColourPreset("ocean-blue", 210, 800, 700),
    ColourPreset("blue", 240, 1000, 1000),
    ColourPreset("purple", 270, 1000, 1000),
    ColourPreset("magenta", 300, 1000, 1000),
    ColourPreset("pink", 330, 700, 1000),
    ColourPreset("hot-pink", 340, 900, 1000),
    ColourPreset("lavender", 260, 400, 900),
    ColourPreset("teal", 165, 900, 700),
    ColourPreset("lime", 90, 1000, 1000),
    ColourPreset("coral", 16, 800, 1000),
    ColourPreset("gold", 45, 900, 1000),
    ColourPreset("ice-blue", 195, 500, 1000),
    ColourPreset("forest-green", 140, 900, 600),
    ColourPreset("crimson", 348, 950, 800),
    ColourPreset("amber", 38, 1000, 1000),
    ColourPreset("daylight", 200, 100, 1000),
    ColourPreset("candlelight", 30, 600, 600),
    ColourPreset("moonlight", 220, 150, 700),
]}


def resolve_colour(name: str) -> ColourPreset:
    """Look up a named colour preset, raising KeyError if not found."""
    normalized = name.strip().lower().replace(" ", "-").replace("_", "-")
    if normalized in PRESETS:
        return PRESETS[normalized]
    raise KeyError(
        f"Unknown colour: '{name}'. Available: {', '.join(sorted(PRESETS))}"
    )


def list_presets() -> list[ColourPreset]:
    """Return all available colour presets sorted by hue."""
    return sorted(PRESETS.values(), key=lambda p: p.hue)
