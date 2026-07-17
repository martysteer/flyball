# Pluggable Keymaps

## Problem

Button-to-action mappings are hardcoded across ~11 locations in 7 files. Changing what a button does means editing conductor.py, display modules, and button modules. No single place to see "what does each button do." Can't experiment with different bindings without code changes. No way to verify code matches intended bindings.

## Design

### Layers

Three distinct layers, currently tangled:

| Layer | Concern | Where it lives |
|-------|---------|---------------|
| **Physical** | GPIO pin / pygame key → button name (`K_a` → `"A"`) | Display + buttons modules (unchanged) |
| **Semantic** | Button name → action name (`"A"` + `"subject"` channel → `"prev"`) | **JSON keymaps (new)** |
| **Execution** | Action name → state change (`"prev"` → `registry.button_prev()`) | State machine + conductor action handlers (unchanged) |

Only the semantic layer moves — from hardcoded if/elif chains to JSON files.

### Keymap Files

Two JSON files in `shared/keymaps/`:

**`spark.json`**:
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

**`slate.json`**:
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

**Format rules:**
- `role` — device role name, matches `hello` message device field
- `buttons` — declares which physical buttons exist (for validation/display hints)
- `default` — bindings that apply unless overridden by a channel-specific entry
- `channels` — optional per-channel overrides, keyed by channel name. Override entries deep-merge over default for that channel only.
- Action value is either:
  - A string: `"prev"` (simple action, no params)
  - An object: `{"action": "channel", "target": "subject"}` (action with params)

### Keymap Loader

New module: `shared/keymap.py`

```python
class Keymap:
    def __init__(self, data: dict):
        self.role = data["role"]
        self.buttons = data["buttons"]
        self.default = data["default"]
        self.channels = data.get("channels", {})

    @classmethod
    def load(cls, path: Path) -> "Keymap":
        with open(path) as f:
            return cls(json.load(f))

    def resolve(self, btn: str, channel: str) -> str | dict | None:
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


def normalize_action(raw) -> tuple[str, dict]:
    """Normalize action value to (name, params)."""
    if isinstance(raw, str):
        return (raw, {})
    if isinstance(raw, dict):
        params = {k: v for k, v in raw.items() if k != "action"}
        return (raw["action"], params)
    return (None, {})


def _action_name(v) -> str:
    if isinstance(v, str):
        return v
    if isinstance(v, dict):
        return v["action"]
    return ""
```

### Conductor Changes

**`conductor/conductor.py`:**

Load keymaps at init:
```python
from shared.keymap import Keymap, normalize_action

class Conductor:
    def __init__(self, word_blocks_path):
        keymaps_dir = Path(__file__).parent.parent / "shared" / "keymaps"
        self.spark_keymap = Keymap.load(keymaps_dir / "spark.json")
        self.slate_keymap = Keymap.load(keymaps_dir / "slate.json")

        self.actions = {
            "prev": lambda: self.registry.button_prev(),
            "next": lambda: self.registry.button_next(),
            "commit": lambda: self.registry.button_commit(),
            "shift": lambda: self.registry.button_shift(),
            "cycle_setting": lambda: self.registry.button_shift(),
            "channel": lambda target: self.registry.set_active_channel(target),
        }
```

Replace `_on_button` if/elif:
```python
def _on_button(self, msg: dict):
    btn, event = msg.get("btn"), msg.get("event")
    if event != "press":
        return
    raw = self.spark_keymap.resolve(btn, self.registry.active_channel)
    if raw is None:
        return
    action, params = normalize_action(raw)
    handler = self.actions.get(action)
    if handler:
        handler(**params)
    self._broadcast_state()
```

Replace `_on_slate_button` hardcoded channel_map:
```python
def _on_slate_button(self, btn: str, event: str):
    if event != "press":
        return
    raw = self.slate_keymap.resolve(btn, self.registry.active_channel)
    if raw is None:
        return
    action, params = normalize_action(raw)
    handler = self.actions.get(action)
    if handler:
        print(f"[Slate] {btn} → {action} {params or ''}", flush=True)
        handler(**params)
        self._broadcast_state()
```

### What Does NOT Change

- **Physical mappings** — GPIO pins, pygame key codes, pin→char maps in display modules. These are hardware/platform concerns, not keymap concerns.
- **State machine** — `ChannelRegistry` methods (`button_prev`, `button_next`, etc.) remain the action implementations.
- **Controller** — doesn't interpret actions. Sends button names over bus. Correct per architecture.
- **Bus protocol** — `ButtonMessage` still sends button name + event. Conductor resolves semantics.

### Future: 3+ Devices

Adding a third device (e.g. a "Dial" with rotary encoder):
1. Add `shared/keymaps/dial.json`
2. Dial sends `hello` with `device: "dial"`
3. Conductor loads the matching keymap
4. Dial's actions use the same action names (`prev`, `next`, or new ones)
5. New action names require adding a handler to `self.actions`

MQTT upgrade doesn't change keymap design — keymaps are transport-agnostic.

### Test Strategy

New file: `tests/test_keymap.py`

**1. Load + resolve tests:**
- Load spark.json, verify `resolve("A", "subject")` → `"prev"`
- Load spark.json, verify `resolve("Y", "engine")` → `"cycle_setting"` (channel override)
- Load spark.json, verify `resolve("Y", "subject")` → `"shift"` (default fallback)
- Load slate.json, verify `resolve("A", "subject")` → `{"action": "channel", "target": "subject"}`
- Verify `resolve("Z", "subject")` → `None` (unknown button)

**2. Coverage test (code matches keymaps):**
```python
def test_all_keymap_actions_have_handlers():
    """Every action in every keymap must have a handler in Conductor."""
    conductor = Conductor(word_blocks_path)
    keymaps_dir = Path("shared/keymaps")
    for keymap_file in keymaps_dir.glob("*.json"):
        keymap = Keymap.load(keymap_file)
        for action_name in keymap.all_actions():
            assert action_name in conductor.actions, \
                f"{keymap_file.name}: action '{action_name}' has no handler"
```

This is the key test — prevents drift between keymaps and code.

**3. Existing integration tests** — must still pass unchanged. Button press → state change flow is the same, just routed through keymap resolution instead of if/elif.

### Files Summary

| Action | Path |
|--------|------|
| Create | `shared/keymaps/spark.json` |
| Create | `shared/keymaps/slate.json` |
| Create | `shared/keymap.py` |
| Create | `tests/test_keymap.py` |
| Modify | `conductor/conductor.py` (replace if/elif with keymap dispatch) |
