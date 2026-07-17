# Pluggable Keymaps Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace hardcoded button-to-action mappings in conductor with JSON keymap files that serve as both configuration and documentation.

**Architecture:** Two JSON keymap files (`shared/keymaps/spark.json`, `shared/keymaps/slate.json`) define button→action bindings with optional per-channel overrides. A small loader module (`shared/keymap.py`) resolves `(button, channel) → action`. Conductor replaces its if/elif dispatch with a dict of action handlers looked up by keymap resolution.

**Tech Stack:** Python 3, JSON, pytest

**Spec:** `docs/specs/2026-07-17-pluggable-keymaps.md`

---

## File Structure

| Action | Path | Responsibility |
|--------|------|---------------|
| Create | `shared/keymaps/spark.json` | Spark button→action bindings |
| Create | `shared/keymaps/slate.json` | Slate button→action bindings |
| Create | `shared/keymap.py` | Keymap loader + resolver + normalize helper |
| Create | `tests/test_keymap.py` | Keymap unit tests + action coverage test |
| Modify | `conductor/conductor.py` | Replace if/elif with keymap dispatch |

---

### Task 1: Keymap JSON Files

**Files:**
- Create: `shared/keymaps/spark.json`
- Create: `shared/keymaps/slate.json`

- [ ] **Step 1: Create keymaps directory**

```bash
mkdir -p shared/keymaps
```

- [ ] **Step 2: Create spark.json**

Write `shared/keymaps/spark.json`:

```json
{
  "role": "spark",
  "buttons": ["A", "B", "X", "Y"],
  "default": {
    "A": "prev",
    "B": "next",
    "X": "commit",
    "Y": "shift"
  },
  "channels": {
    "engine": {
      "Y": "cycle_setting"
    }
  }
}
```

- [ ] **Step 3: Create slate.json**

Write `shared/keymaps/slate.json`:

```json
{
  "role": "slate",
  "buttons": ["A", "B", "C", "D"],
  "default": {
    "A": { "action": "channel", "target": "subject" },
    "B": { "action": "channel", "target": "context" },
    "C": { "action": "channel", "target": "style" },
    "D": { "action": "channel", "target": "engine" }
  }
}
```

- [ ] **Step 4: Commit**

```bash
git add shared/keymaps/spark.json shared/keymaps/slate.json
git commit -m "feat: add keymap JSON files for spark and slate"
```

---

### Task 2: Keymap Loader Module

**Files:**
- Create: `tests/test_keymap.py`
- Create: `shared/keymap.py`

- [ ] **Step 1: Write failing tests for Keymap loader and resolver**

Write `tests/test_keymap.py`:

```python
"""Test keymap loader, resolver, and action coverage."""

import json
from pathlib import Path
import pytest
from shared.keymap import Keymap, normalize_action


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_keymap.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'shared.keymap'`

- [ ] **Step 3: Write the Keymap loader module**

Write `shared/keymap.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_keymap.py -v`
Expected: All 13 tests PASS

- [ ] **Step 5: Commit**

```bash
git add shared/keymap.py tests/test_keymap.py
git commit -m "feat: keymap loader with resolve + normalize + tests"
```

---

### Task 3: Conductor Keymap Dispatch

**Files:**
- Modify: `conductor/conductor.py:1-108` (imports, `__init__`, `_on_button`, `_on_slate_button`)

- [ ] **Step 1: Run all tests to confirm baseline**

Run: `pytest -v`
Expected: All 27 tests PASS (plus the 13 new keymap tests = 40 total)

- [ ] **Step 2: Refactor conductor to use keymap dispatch**

Edit `conductor/conductor.py`. The full updated file:

```python
"""Conductor (Slate authority): state machine + server."""

import asyncio
import logging
from pathlib import Path
from typing import Optional

from conductor.state_machine import ChannelRegistry, StateSnapshot
from conductor.display import InkyMock, SlateDisplay
from conductor.buttons import KeyboardListener
from shared.bus_websocket import WebSocketServer
from shared.messages import ButtonMessage, StateMessage, PongMessage
from shared.config import IS_SIMULATION
from shared.keymap import Keymap, normalize_action

logger = logging.getLogger(__name__)

KEYMAPS_DIR = Path(__file__).parent.parent / "shared" / "keymaps"


class Conductor:
    """State authority; runs on Slate."""

    def __init__(self, word_blocks_path: Path):
        """Initialize Conductor."""
        self.registry = ChannelRegistry(word_blocks_path)
        self.bus = WebSocketServer()
        self.display = InkyMock() if IS_SIMULATION else SlateDisplay()
        self.loop = None  # Store event loop for thread-safe scheduling
        self.buttons: Optional[KeyboardListener] = None
        self.server_running = True  # Track server state for exit

        # Load keymaps
        self.spark_keymap = Keymap.load(KEYMAPS_DIR / "spark.json")
        self.slate_keymap = Keymap.load(KEYMAPS_DIR / "slate.json")

        # Action handlers — keyed by action name from keymap JSON
        self.actions = {
            "prev": lambda: self.registry.button_prev(),
            "next": lambda: self.registry.button_next(),
            "commit": lambda: self.registry.button_commit(),
            "shift": lambda: self.registry.button_shift(),
            "cycle_setting": lambda: self.registry.button_shift(),
            "channel": lambda target: self.registry.set_active_channel(target),
        }

        # Register message handlers
        self.bus.on("hello", self._on_hello)
        self.bus.on("button", self._on_button)
        self.bus.on("ping", self._on_ping)

    async def start(self, host: str, port: int) -> None:
        """Start WebSocket server and display."""
        self.loop = asyncio.get_running_loop()  # Capture loop for thread-safe calls
        await self.bus.start(host, port)

        # Wire keyboard input
        if IS_SIMULATION and hasattr(self.display, 'on_key'):
            # Pygame displays handle keyboard directly
            self.display.on_key = self._on_key
        else:
            # Hardware: use GPIO button listener
            self.buttons = KeyboardListener(device="slate", on_exit=self._on_exit_signal)
            self.buttons.on(self._on_slate_button)
            self.buttons.start()

        # Render initial state
        self._broadcast_state()

    async def shutdown(self) -> None:
        """Shut down server."""
        await self.bus.disconnect()
        self.display.close()

    def _on_hello(self, msg: dict) -> None:
        """Handle hello from Controller."""
        logger.info(f"Controller connected: {msg.get('device')} fw {msg.get('fw')}")
        # Send current state snapshot
        self._broadcast_state()

    def _dispatch(self, keymap: Keymap, btn: str, event: str, label: str) -> None:
        """Resolve button via keymap and dispatch action."""
        if event != "press":
            return
        raw = keymap.resolve(btn, self.registry.active_channel)
        if raw is None:
            return
        action, params = normalize_action(raw)
        handler = self.actions.get(action)
        if handler:
            print(f"[{label}] {btn} → {action}{(' ' + str(params)) if params else ''}", flush=True)
            handler(**params)
            self._broadcast_state()

    def _on_button(self, msg: dict) -> None:
        """Handle button event from Controller (Spark)."""
        btn = msg.get("btn")
        event = msg.get("event")
        logger.info(f"Button: {btn} {event}")
        self._dispatch(self.spark_keymap, btn, event, "Spark")

    def _on_ping(self, msg: dict) -> None:
        """Handle ping from Controller."""
        pong = PongMessage()
        asyncio.create_task(self.bus.send(pong.model_dump()))

    def _on_key(self, char: str) -> None:
        """Handle key press from pygame display."""
        # Map char to button name (physical layer — not keymap concern)
        key_map = {'a': 'A', 'b': 'B', 'c': 'C', 'd': 'D'}
        if char == 'q':
            self._on_exit_signal()
        elif char in key_map:
            self._on_slate_button(key_map[char], "press")

    def _on_slate_button(self, btn: str, event: str) -> None:
        """Handle button press on Slate."""
        self._dispatch(self.slate_keymap, btn, event, "Slate")

    def _schedule(self, coro) -> None:
        """Schedule a coroutine from either the event loop or a thread."""
        if not self.loop:
            return
        try:
            if asyncio.get_running_loop() == self.loop:
                asyncio.create_task(coro)
            else:
                asyncio.run_coroutine_threadsafe(coro, self.loop)
        except RuntimeError:
            asyncio.run_coroutine_threadsafe(coro, self.loop)

    def _on_exit_signal(self) -> None:
        """Handle exit signal from button listener (Ctrl+C or q)."""
        self.server_running = False
        self._schedule(self.shutdown())

    def _broadcast_state(self) -> None:
        """Send current state to all connected Controllers."""
        snapshot = StateSnapshot.from_registry(self.registry, mode="word")
        msg = StateMessage(
            channel=snapshot.channel,
            channel_color=snapshot.channel_color,
            option_index=snapshot.option_index,
            option_count=snapshot.option_count,
            candidate=snapshot.candidate,
            committed=snapshot.committed,
            mode=snapshot.mode,
            engine=snapshot.engine,
        )
        self._schedule(self.bus.send(msg.model_dump()))

        # Also render to Slate display
        self.display.render(snapshot)
```

Key changes from old code:
- Added imports: `from shared.keymap import Keymap, normalize_action`
- Added `KEYMAPS_DIR` constant
- `__init__`: loads `spark_keymap` and `slate_keymap`, defines `self.actions` dict
- New `_dispatch()` method: shared resolution logic for both keymaps
- `_on_button()`: replaced if/elif chain (lines 72-83) with `self._dispatch(self.spark_keymap, ...)`
- `_on_slate_button()`: replaced `channel_map` dict (line 104) with `self._dispatch(self.slate_keymap, ...)`

- [ ] **Step 3: Run all tests to verify nothing broke**

Run: `pytest -v`
Expected: All 40 tests PASS

- [ ] **Step 4: Commit**

```bash
git add conductor/conductor.py
git commit -m "refactor: conductor uses keymap dispatch instead of hardcoded if/elif"
```

---

### Task 4: Action Coverage Test

**Files:**
- Modify: `tests/test_keymap.py` (add coverage test)

- [ ] **Step 1: Add coverage test**

Append to `tests/test_keymap.py`:

```python
from conductor.conductor import Conductor


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
```

- [ ] **Step 2: Run the coverage test**

Run: `pytest tests/test_keymap.py::test_all_keymap_actions_have_handlers -v`
Expected: PASS

- [ ] **Step 3: Run full test suite**

Run: `pytest -v`
Expected: All 41 tests PASS

- [ ] **Step 4: Commit**

```bash
git add tests/test_keymap.py
git commit -m "test: add keymap-to-handler coverage test"
```
