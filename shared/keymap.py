"""Keymap loader: JSON button→action bindings with per-channel overrides."""

import json
from pathlib import Path
from typing import Optional, Union


class Keymap:
    """Load and resolve button→action bindings from a JSON keymap file."""

    def __init__(self, data: dict):
        self.role: str = data["role"]
        self.buttons: list[str] = data["buttons"]
        self.default: dict = data["default"]
        self.channels: dict = data.get("channels", {})

    @classmethod
    def load(cls, path: Path) -> "Keymap":
        """Load keymap from a JSON file."""
        with open(path) as f:
            return cls(json.load(f))

    def resolve(self, btn: str, channel: str) -> Union[str, dict, None]:
        """Resolve (button, channel) → action. Channel override wins over default."""
        override = self.channels.get(channel, {}).get(btn)
        if override is not None:
            return override
        return self.default.get(btn)

    def all_actions(self) -> set[str]:
        """Collect every action name referenced in this keymap."""
        actions = set()
        for v in self.default.values():
            actions.add(_action_name(v))
        for ch_overrides in self.channels.values():
            for v in ch_overrides.values():
                actions.add(_action_name(v))
        return actions


def normalize_action(raw) -> tuple[Optional[str], dict]:
    """Normalize action value to (name, params).

    String actions: ("prev", {})
    Dict actions:   ("channel", {"target": "subject"})
    None/unknown:   (None, {})
    """
    if isinstance(raw, str):
        return (raw, {})
    if isinstance(raw, dict):
        params = {k: v for k, v in raw.items() if k != "action"}
        return (raw["action"], params)
    return (None, {})


def _action_name(v) -> str:
    """Extract action name from a string or dict action value."""
    if isinstance(v, str):
        return v
    if isinstance(v, dict):
        return v["action"]
    return ""
