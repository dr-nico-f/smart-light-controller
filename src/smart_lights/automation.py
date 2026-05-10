"""Automation primitives for future menu bar and event integrations."""

from __future__ import annotations

from collections.abc import Callable

from smart_lights import config as config_store
from smart_lights.models import AutomationRule


SceneRunner = Callable[[str], object]


class AutomationEngine:
    """Matches simple triggers to scene executions."""

    def __init__(self, rules: list[AutomationRule], scene_runner: SceneRunner) -> None:
        self._rules = rules
        self._scene_runner = scene_runner

    @classmethod
    def from_config(cls, scene_runner: SceneRunner) -> "AutomationEngine":
        """Build an automation engine from repo config."""
        return cls(config_store.load_automation_rules(), scene_runner=scene_runner)

    def rules(self) -> list[AutomationRule]:
        """Return all configured automation rules."""
        return list(self._rules)

    def dispatch(self, trigger_kind: str, trigger_value: str) -> list[object]:
        """Run every scene bound to the given trigger."""
        results: list[object] = []
        for rule in self._rules:
            if rule.trigger.kind == trigger_kind and rule.trigger.value == trigger_value:
                results.append(self._scene_runner(rule.scene))
        return results
