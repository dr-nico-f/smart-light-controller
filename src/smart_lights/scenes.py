"""Scene loading and lookup helpers."""

from __future__ import annotations

from pathlib import Path

from smart_lights import config as config_store
from smart_lights.models import SceneConfig


class SceneLibrary:
    """Loads and serves reusable scene definitions."""

    def __init__(self, scenes: list[SceneConfig]) -> None:
        self._scenes = {scene.name: scene for scene in scenes}

    @classmethod
    def from_config(cls, path: str | Path | None = None) -> "SceneLibrary":
        """Load scenes from disk."""
        return cls(config_store.load_scenes(path))

    def all(self) -> list[SceneConfig]:
        """Return all configured scenes."""
        return list(self._scenes.values())

    def names(self) -> list[str]:
        """Return sorted scene names."""
        return sorted(self._scenes)

    def get(self, name: str) -> SceneConfig:
        """Return one scene by name."""
        try:
            return self._scenes[name]
        except KeyError as exc:
            raise KeyError(f"Unknown scene: {name}") from exc
