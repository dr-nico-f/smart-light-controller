"""Tests for scene loading and lookup."""

from __future__ import annotations

import pytest

from smart_lights.scenes import SceneLibrary


def test_scene_names_include_expected(scene_library: SceneLibrary) -> None:
    names = scene_library.names()
    assert "movie-time" in names
    assert "all-off" in names
    assert "party" in names


def test_party_scene_has_three_actions(scene_library: SceneLibrary) -> None:
    scene = scene_library.get("party")
    assert len(scene.actions) == 3


def test_scene_actions_have_targets(scene_library: SceneLibrary) -> None:
    scene = scene_library.get("movie-time")
    assert all(action.target for action in scene.actions)


def test_unknown_scene_raises(scene_library: SceneLibrary) -> None:
    with pytest.raises(KeyError, match="Unknown scene"):
        scene_library.get("nonexistent-scene")
