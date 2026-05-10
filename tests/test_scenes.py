"""Tests for scene loading and lookup."""

from __future__ import annotations

import unittest

from smart_lights.scenes import SceneLibrary


class SceneTests(unittest.TestCase):
    """Validate configured scenes can be discovered and retrieved."""

    def test_scene_names_include_movie_time(self) -> None:
        library = SceneLibrary.from_config()
        self.assertIn("movie-time", library.names())

    def test_scene_contains_actions(self) -> None:
        library = SceneLibrary.from_config()
        scene = library.get("party")
        self.assertEqual(len(scene.actions), 3)


if __name__ == "__main__":
    unittest.main()
