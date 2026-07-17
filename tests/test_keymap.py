"""Test keymap loader, resolver, and action coverage."""

import json
from pathlib import Path
import pytest
from shared.keymap import Keymap, normalize_action
from conductor.conductor import Conductor


@pytest.fixture
def keymaps_dir():
    return Path(__file__).parent.parent / "shared" / "keymaps"


@pytest.fixture
def spark_keymap(keymaps_dir):
    return Keymap.load(keymaps_dir / "spark.json")


@pytest.fixture
def slate_keymap(keymaps_dir):
    return Keymap.load(keymaps_dir / "slate.json")


def test_spark_keymap_loads(spark_keymap):
    """Spark keymap loads with correct role and buttons."""
    assert spark_keymap.role == "spark"
    assert spark_keymap.buttons == ["A", "B", "X", "Y"]


def test_slate_keymap_loads(slate_keymap):
    """Slate keymap loads with correct role and buttons."""
    assert slate_keymap.role == "slate"
    assert slate_keymap.buttons == ["A", "B", "C", "D"]


def test_spark_default_resolve(spark_keymap):
    """Spark default bindings resolve correctly."""
    assert spark_keymap.resolve("A", "subject") == "prev"
    assert spark_keymap.resolve("B", "subject") == "next"
    assert spark_keymap.resolve("X", "subject") == "commit"
    assert spark_keymap.resolve("Y", "subject") == "shift"


def test_spark_channel_override(spark_keymap):
    """Engine channel overrides Y from shift to cycle_setting."""
    assert spark_keymap.resolve("Y", "engine") == "cycle_setting"


def test_spark_channel_override_fallback(spark_keymap):
    """Non-overridden buttons still resolve to default in engine channel."""
    assert spark_keymap.resolve("A", "engine") == "prev"


def test_slate_resolve_returns_dict(slate_keymap):
    """Slate bindings resolve to action dicts with params."""
    result = slate_keymap.resolve("A", "subject")
    assert result == {"action": "channel", "target": "subject"}


def test_unknown_button_returns_none(spark_keymap):
    """Unknown button resolves to None."""
    assert spark_keymap.resolve("Z", "subject") is None


def test_normalize_action_string():
    """String action normalizes to (name, {})."""
    assert normalize_action("prev") == ("prev", {})


def test_normalize_action_dict():
    """Dict action normalizes to (name, params)."""
    result = normalize_action({"action": "channel", "target": "subject"})
    assert result == ("channel", {"target": "subject"})


def test_normalize_action_none():
    """None action normalizes to (None, {})."""
    assert normalize_action(None) == (None, {})


def test_all_actions_spark(spark_keymap):
    """all_actions collects every action name from spark keymap."""
    actions = spark_keymap.all_actions()
    assert actions == {"prev", "next", "commit", "shift", "cycle_setting"}


def test_all_actions_slate(slate_keymap):
    """all_actions collects every action name from slate keymap."""
    actions = slate_keymap.all_actions()
    assert actions == {"channel"}


@pytest.fixture
def word_blocks_path():
    return Path(__file__).parent.parent / "shared" / "data" / "word_blocks.json"


def test_all_keymap_actions_have_handlers(word_blocks_path, keymaps_dir):
    """Every action in every keymap JSON must have a handler in Conductor.actions."""
    conductor = Conductor(word_blocks_path)
    for keymap_file in keymaps_dir.glob("*.json"):
        keymap = Keymap.load(keymap_file)
        for action_name in keymap.all_actions():
            assert action_name in conductor.actions, \
                f"{keymap_file.name}: action '{action_name}' has no handler in Conductor"
