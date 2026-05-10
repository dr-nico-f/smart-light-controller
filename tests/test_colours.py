"""Tests for named colour presets."""

from __future__ import annotations

import pytest

from smart_lights.colours import ColourPreset, list_presets, resolve_colour


def test_resolve_known_colour() -> None:
    preset = resolve_colour("sunset-orange")
    assert isinstance(preset, ColourPreset)
    assert preset.hue == 20


def test_resolve_is_case_insensitive() -> None:
    assert resolve_colour("Ocean-Blue") == resolve_colour("ocean-blue")


def test_resolve_normalizes_underscores() -> None:
    assert resolve_colour("ocean_blue") == resolve_colour("ocean-blue")


def test_resolve_unknown_raises() -> None:
    with pytest.raises(KeyError, match="Unknown colour"):
        resolve_colour("unicorn-sparkle")


def test_list_presets_sorted_by_hue() -> None:
    presets = list_presets()
    assert len(presets) >= 20
    hues = [p.hue for p in presets]
    assert hues == sorted(hues)


def test_all_presets_have_valid_ranges() -> None:
    for preset in list_presets():
        assert 0 <= preset.hue <= 360
        assert 0 <= preset.saturation <= 1000
        assert 0 <= preset.value <= 1000
