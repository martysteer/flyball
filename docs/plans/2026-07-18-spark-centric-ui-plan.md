# Spark-Centric UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move all interaction to Spark's 4 buttons with local exploration state, variable-width bounce-scroll font, ~15fps ticker rendering, and explicit-send-only Slate e-ink redraws.

**Architecture:** Spark (Controller) owns exploration state locally (channel, indices, committed words) and renders via a pure `(state, tick) → frame` function driven by a ~15fps ticker. Slate (Conductor) redraws e-ink only on an explicit `send` message. Per-press `button` messages are removed. Long-press (≥600ms, fires while held) detected by a pure poll-based detector.

**Tech Stack:** Python 3, asyncio, pydantic (messages), pygame (sim), websockets, pytest + pytest-asyncio.

**Spec:** `docs/specs/2026-07-18-spark-centric-ui-design.md`

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `shared/font.py` | Create | Variable-width column font table, `render_columns`, `text_width`, `bounce_offset` |
| `shared/config.py` | Modify | `get_spark_brightness()` |
| `shared/interfaces/display.py` | Modify | Add `CHANNEL_COLORS` (shared by both sides) |
| `shared/messages.py` | Modify | Add `SendMessage` |
| `controller/render.py` | Create | Pure `render_frame(state, tick, effects) → 7×17 RGB grid` |
| `controller/state.py` | Create | `LocalState` — channels, indices, committed words, engine settings |
| `controller/longpress.py` | Create | `LongPressDetector` — pure, poll-based |
| `controller/display.py` | Modify | Replace `render(state)`+font dicts with `push(frame)`; brightness config |
| `controller/controller.py` | Modify | Ticker loop, local state wiring, remove button messages, send |
| `controller/buttons.py` | Modify | GPIO `when_released` → release events |
| `controller/unicorn_mock.py` | Modify | KEYUP → release callback |
| `conductor/conductor.py` | Modify | `_on_send` handler; slate buttons no-op; hello no longer renders |
| `conductor/state_machine.py` | Modify | Import `CHANNEL_COLORS` from shared |
| `tests/test_font.py` | Create | Font + bounce math |
| `tests/test_render.py` | Create | Pure frame rendering |
| `tests/test_local_state.py` | Create | State transitions |
| `tests/test_longpress.py` | Create | Timing with fake clock |
| `tests/test_send_roundtrip.py` | Create | Send message over bus updates Conductor registry |

Font glyph shape: dict `char → list of column ints`; column = 5 bits, **bit 0 = top row**. Glyphs authored as human-readable row-strings, columns computed at import.

---

## Stage S1 — Font, bounce math, brightness

### Task 1: Variable-width font module

**Files:**
- Create: `shared/font.py`
- Test: `tests/test_font.py`

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for shared/font.py — variable-width column font."""

from shared.font import FONT, render_columns, text_width


def test_i_is_single_full_column():
    # 'I' = 1 column, all 5 bits set (bit 0 = top)
    assert FONT["I"] == [0b11111]


def test_h_columns():
    # H rows: 101/101/111/101/101 → cols [31, 4, 31]
    assert FONT["H"] == [0b11111, 0b00100, 0b11111]


def test_render_columns_concatenates_with_gap():
    # H (3 cols) + 1 blank + I (1 col) = 5 cols
    assert render_columns("HI") == [0b11111, 0b00100, 0b11111, 0, 0b11111]


def test_text_width():
    assert text_width("HI") == 5
    assert text_width("") == 0


def test_lowercase_maps_to_uppercase():
    assert render_columns("hi") == render_columns("HI")


def test_unknown_char_skipped():
    assert render_columns("H~I") == render_columns("HI")


def test_full_charset_present():
    for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -'[]":
        assert ch in FONT, f"missing glyph: {ch}"


def test_all_glyphs_are_5_rows_max():
    for ch, cols in FONT.items():
        for col in cols:
            assert 0 <= col < 32, f"{ch} column exceeds 5 bits"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_font.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'shared.font'`

- [ ] **Step 3: Write implementation**

```python
"""Variable-width LED font: char → list of columns (5 bits, bit 0 = top)."""

# Glyphs authored as row-strings (top to bottom); width varies per char.
_GLYPHS = {
    "A": ["010", "101", "111", "101", "101"],
    "B": ["110", "101", "110", "101", "110"],
    "C": ["011", "100", "100", "100", "011"],
    "D": ["110", "101", "101", "101", "110"],
    "E": ["111", "100", "110", "100", "111"],
    "F": ["111", "100", "110", "100", "100"],
    "G": ["011", "100", "101", "101", "011"],
    "H": ["101", "101", "111", "101", "101"],
    "I": ["1", "1", "1", "1", "1"],
    "J": ["001", "001", "001", "101", "010"],
    "K": ["101", "101", "110", "101", "101"],
    "L": ["100", "100", "100", "100", "111"],
    "M": ["10001", "11011", "10101", "10001", "10001"],
    "N": ["1001", "1101", "1011", "1001", "1001"],
    "O": ["010", "101", "101", "101", "010"],
    "P": ["110", "101", "110", "100", "100"],
    "Q": ["010", "101", "101", "010", "001"],
    "R": ["110", "101", "110", "101", "101"],
    "S": ["011", "100", "010", "001", "110"],
    "T": ["111", "010", "010", "010", "010"],
    "U": ["101", "101", "101", "101", "111"],
    "V": ["101", "101", "101", "101", "010"],
    "W": ["10001", "10001", "10101", "10101", "01010"],
    "X": ["101", "101", "010", "101", "101"],
    "Y": ["101", "101", "010", "010", "010"],
    "Z": ["111", "001", "010", "100", "111"],
    "0": ["010", "101", "101", "101", "010"],
    "1": ["010", "110", "010", "010", "111"],
    "2": ["110", "001", "010", "100", "111"],
    "3": ["110", "001", "010", "001", "110"],
    "4": ["101", "101", "111", "001", "001"],
    "5": ["111", "100", "110", "001", "110"],
    "6": ["011", "100", "110", "101", "010"],
    "7": ["111", "001", "010", "010", "010"],
    "8": ["010", "101", "010", "101", "010"],
    "9": ["010", "101", "011", "001", "110"],
    " ": ["00", "00", "00", "00", "00"],
    "-": ["000", "000", "111", "000", "000"],
    "'": ["1", "1", "0", "0", "0"],
    "[": ["11", "10", "10", "10", "11"],
    "]": ["11", "01", "01", "01", "11"],
}

# char → list of column ints; column bit 0 = top row
FONT = {
    ch: [
        sum(1 << y for y, row in enumerate(rows) if row[x] == "1")
        for x in range(len(rows[0]))
    ]
    for ch, rows in _GLYPHS.items()
}


def render_columns(text: str) -> list:
    """Concatenate glyph columns with 1 blank column between chars."""
    cols = []
    for ch in text.upper():
        glyph = FONT.get(ch)
        if glyph is None:
            continue
        if cols:
            cols.append(0)
        cols.extend(glyph)
    return cols


def text_width(text: str) -> int:
    """Total column count for text (including inter-char gaps)."""
    return len(render_columns(text))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_font.py -v`
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add shared/font.py tests/test_font.py
git commit -m "feat: shared variable-width column font (S1)"
```

### Task 2: Bounce-scroll math

**Files:**
- Modify: `shared/font.py`
- Test: `tests/test_font.py`

- [ ] **Step 1: Write the failing tests** (append to `tests/test_font.py`)

```python
from shared.font import bounce_offset


def test_bounce_static_when_text_fits():
    assert bounce_offset(17, 17, tick=0) == 0
    assert bounce_offset(10, 17, tick=999) == 0


def test_bounce_scrolls_to_max_then_back():
    # 20 cols in 17 window → max offset 3; ticks_per_col=5
    assert bounce_offset(20, 17, tick=0) == 0
    assert bounce_offset(20, 17, tick=5) == 1
    assert bounce_offset(20, 17, tick=15) == 3   # end visible
    assert bounce_offset(20, 17, tick=20) == 2   # reversing
    assert bounce_offset(20, 17, tick=30) == 0   # back at start


def test_bounce_never_exceeds_bounds():
    for tick in range(200):
        off = bounce_offset(40, 17, tick)
        assert 0 <= off <= 23
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_font.py -v`
Expected: FAIL — `ImportError: cannot import name 'bounce_offset'`

- [ ] **Step 3: Implement** (append to `shared/font.py`)

```python
def bounce_offset(total_cols: int, window: int, tick: int, ticks_per_col: int = 5) -> int:
    """Triangle-wave scroll offset: left until end visible, then reverse.

    At 15fps, ticks_per_col=5 → 3 cols/s (medium speed per spec).
    """
    max_off = total_cols - window
    if max_off <= 0:
        return 0
    step = tick // ticks_per_col
    period = 2 * max_off
    pos = step % period
    return pos if pos <= max_off else period - pos
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_font.py -v`
Expected: 11 passed

- [ ] **Step 5: Commit**

```bash
git add shared/font.py tests/test_font.py
git commit -m "feat: bounce-scroll offset math (S1)"
```

### Task 3: Brightness config + font wired into current displays

**Files:**
- Modify: `shared/config.py`
- Modify: `controller/display.py`

- [ ] **Step 1: Add brightness config** (append to `shared/config.py`)

```python
def get_spark_brightness() -> float:
    """Unicorn HAT brightness 0.0–1.0. Default dim per spec."""
    # ponytail: env-only knob, calibrate on hardware
    return float(os.getenv("FLYBALL_SPARK_BRIGHTNESS", "0.2"))
```

- [ ] **Step 2: Replace both duplicated 3×5 font dicts in `controller/display.py`**

Delete `SparkMock._render_text` (lines ~63–107) and `SparkDisplay._render_text_hw` (lines ~202–246) including both `font_3x5` dicts. Replace with one module-level helper:

```python
from shared.config import IS_SIMULATION, get_spark_brightness
from shared.font import render_columns
from shared.interfaces.display import Display, StateSnapshot


def draw_text(set_pixel, text: str, r: int, g: int, b: int, offset: int = 0, width: int = 17) -> None:
    """Draw text columns onto rows 2-6 via a set_pixel(x, y, r, g, b) callable."""
    cols = render_columns(text)
    for x in range(width):
        i = x + offset
        if 0 <= i < len(cols):
            col = cols[i]
            for y in range(5):
                if col >> y & 1:
                    set_pixel(x, 2 + y, r, g, b)
```

In `SparkMock.render`, replace `self._render_text(text, r, g, b)` with:

```python
            draw_text(self.unicorn.set_pixel, text, r, g, b)
```

In `SparkDisplay.render`, replace `self._render_text_hw(text, r, g, b)` with:

```python
        draw_text(self.hat.set_pixel, text, r, g, b)
```

- [ ] **Step 3: Apply brightness config**

In `SparkMock.__init__`: `self.unicorn.set_brightness(get_spark_brightness())` (was 0.5).
In `SparkDisplay.__init__` hardware branch: `self.hat.set_brightness(get_spark_brightness())` (was 0.5).

- [ ] **Step 4: Run full test suite**

Run: `python -m pytest tests/ -v`
Expected: all pass (no display unit tests exist; this guards regressions)

- [ ] **Step 5: Sim demo**

Run conductor + controller (`python -m conductor` and `python -m controller` in two terminals). Cycle to a long word (e.g. "Detective") — first 17 columns visible, variable-width, dimmer. Static is expected (ticker arrives in S2).

- [ ] **Step 6: Commit**

```bash
git add shared/config.py controller/display.py
git commit -m "feat: wire shared font + brightness config into Spark displays (S1)"
```

---

## Stage S2 — Ticker + pure render

### Task 4: Pure `render_frame`

**Files:**
- Create: `controller/render.py`
- Test: `tests/test_render.py`

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for controller/render.py — pure (state, tick) → frame."""

from controller.render import render_frame, WIDTH, HEIGHT
from shared.interfaces.display import StateSnapshot


def make_state(**kw):
    defaults = dict(
        channel="subject",
        channel_color=(0, 200, 80),
        option_index=1,
        option_count=5,
        candidate="HI",
        committed=False,
        mode="word",
        engine=None,
    )
    defaults.update(kw)
    return StateSnapshot(**defaults)


def test_frame_dimensions():
    frame = render_frame(make_state(), tick=0)
    assert len(frame) == HEIGHT
    assert all(len(row) == WIDTH for row in frame)


def test_row0_dim_bar_when_uncommitted():
    frame = render_frame(make_state(committed=False), tick=0)
    assert frame[0][0] == (0, 200 // 4, 80 // 4)


def test_row0_solid_bar_when_committed():
    frame = render_frame(make_state(committed=True), tick=0)
    assert frame[0][0] == (0, 200, 80)


def test_row1_pip_bright_at_index():
    frame = render_frame(make_state(option_index=1, option_count=5), tick=0)
    assert frame[1][1] == (0, 200, 80)
    assert frame[1][0] == (0, 200 // 8, 80 // 8)


def test_text_pixels_short_word_static():
    # 'H' col 0 has top bit set → pixel at (row 2, col 0)
    frame = render_frame(make_state(candidate="HI"), tick=0)
    assert frame[2][0] == (0, 200, 80)
    assert frame[2][3] == (0, 0, 0)  # gap column


def test_long_word_scrolls_with_tick():
    state = make_state(candidate="DETECTIVE STORY")
    f0 = render_frame(state, tick=0)
    f1 = render_frame(state, tick=30)
    assert f0 != f1


def test_engine_mode_shows_candidate_text():
    state = make_state(mode="engine", channel="engine",
                       channel_color=(200, 150, 0), candidate="SEND",
                       engine={"operator": "swap"})
    frame = render_frame(state, tick=0)
    # 'S' col 0: rows 011/100/010/001/110 → bit1,bit4 → pixel at row 3 col 0
    assert frame[3][0] == (200, 150, 0)
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_render.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'controller.render'`

- [ ] **Step 3: Implement `controller/render.py`**

```python
"""Pure Spark frame renderer: (state, tick) → 7×17 RGB grid."""

from shared.font import render_columns, bounce_offset
from shared.interfaces.display import StateSnapshot

WIDTH = 17
HEIGHT = 7

Frame = list  # list[HEIGHT] of list[WIDTH] of (r, g, b)


def blank_frame() -> Frame:
    return [[(0, 0, 0) for _ in range(WIDTH)] for _ in range(HEIGHT)]


def render_frame(state: StateSnapshot, tick: int) -> Frame:
    """Pure render. No I/O, no side effects."""
    frame = blank_frame()
    r, g, b = state.channel_color

    # Row 0: channel bar — solid if committed, dim otherwise
    bar = (r, g, b) if state.committed else (r // 4, g // 4, b // 4)
    for x in range(WIDTH):
        frame[0][x] = bar

    # Row 1: option pips, bright at current index
    for i in range(min(state.option_count, WIDTH)):
        frame[1][i] = (r, g, b) if i == state.option_index else (r // 8, g // 8, b // 8)

    # Rows 2-6: candidate text with bounce scroll
    cols = render_columns(state.candidate)
    off = bounce_offset(len(cols), WIDTH, tick)
    for x in range(WIDTH):
        i = x + off
        if 0 <= i < len(cols):
            col = cols[i]
            for y in range(5):
                if col >> y & 1:
                    frame[2 + y][x] = (r, g, b)

    return frame
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_render.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add controller/render.py tests/test_render.py
git commit -m "feat: pure (state, tick) frame renderer for Spark (S2)"
```

### Task 5: Ticker task + `push(frame)` displays

**Files:**
- Modify: `controller/display.py`
- Modify: `controller/controller.py`

- [ ] **Step 1: Add `push(frame)` to displays; delete state-render path**

In `controller/display.py`:
- `SparkMock`: add `push`, delete `render(state)` and the `draw_text` call inside it.
- `SparkDisplay`: add `push` proxying to mock or hardware; delete `render(state)`.
- Delete the module-level `draw_text` helper (render.py owns drawing now).
- Remove `Display` ABC inheritance from both classes (its abstract `render(state)` no longer applies; classes stay duck-typed with `push`/`poll_events`/`close`). Keep `StateSnapshot` import if still referenced, else drop it.

```python
class SparkMock:
    """Mock Spark display: pygame window showing 17x7 LED matrix."""
    # __init__, poll_events, _on_button_pin, close unchanged

    def push(self, frame) -> None:
        """Push a rendered 7x17 RGB frame to the window."""
        if not self.unicorn:
            return
        try:
            self.unicorn.clear()
            for y, row in enumerate(frame):
                for x, (r, g, b) in enumerate(row):
                    if r or g or b:
                        self.unicorn.set_pixel(x, y, r, g, b)
            self.unicorn.show()
        except Exception:
            return
```

```python
    # SparkDisplay
    def push(self, frame) -> None:
        """Push a rendered frame to mock or hardware."""
        if self.mock:
            self.mock.push(frame)
            return
        self.hat.clear()
        for y, row in enumerate(frame):
            for x, (r, g, b) in enumerate(row):
                if r or g or b:
                    self.hat.set_pixel(x, y, r, g, b)
        self.hat.show()
```

- [ ] **Step 2: Replace render queue with ticker in `controller/controller.py`**

Remove `self.render_queue`, `self.render_task`, `_render_loop`, and the `put_nowait`/`QueueFull` blocks in `_on_state`/`_on_patch` (handlers just set `self.current_state`). Add:

```python
from controller.render import render_frame

    # in __init__:
        self.tick = 0
        self.ticker_task: Optional[asyncio.Task] = None

    # in _send_hello() where render_task was created:
        if not self.ticker_task:
            self.ticker_task = asyncio.create_task(self._ticker_loop())

    async def _ticker_loop(self) -> None:
        """~15fps animation ticker: render current state every frame."""
        while self.running:
            if self.current_state:
                self.display.push(render_frame(self.current_state, self.tick))
            self.tick += 1
            await asyncio.sleep(1 / 15)
```

In `shutdown()`, cancel `self.ticker_task` (same pattern as old `render_task`).

Note: `_send_hello` runs on every reconnect — the `if not self.ticker_task` guard (and same for `heartbeat_task`) prevents duplicate tasks:

```python
        if not self.heartbeat_task:
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
```

- [ ] **Step 3: Run full suite**

Run: `python -m pytest tests/ -v`
Expected: all pass

- [ ] **Step 4: Sim demo**

Run both apps. Long candidate word bounce-scrolls smoothly left/right at ~3 cols/s; short words static.

- [ ] **Step 5: Commit**

```bash
git add controller/display.py controller/controller.py
git commit -m "feat: 15fps ticker + push-frame displays replace render queue (S2)"
```

---

## Stage S3 — Local state on Spark

### Task 6: Move `CHANNEL_COLORS` to shared

**Files:**
- Modify: `shared/interfaces/display.py`
- Modify: `conductor/state_machine.py`

- [ ] **Step 1: Add to `shared/interfaces/display.py`**

```python
CHANNEL_COLORS = {
    "subject": (0, 200, 80),    # green
    "context": (0, 100, 200),   # blue
    "style": (200, 0, 150),     # magenta
    "engine": (200, 150, 0),    # amber
}
```

- [ ] **Step 2: In `conductor/state_machine.py`**, delete the local `CHANNEL_COLORS` dict and import instead:

```python
from shared.interfaces.display import CHANNEL_COLORS
```

- [ ] **Step 3: Run suite, commit**

Run: `python -m pytest tests/ -v` — all pass.

```bash
git add shared/interfaces/display.py conductor/state_machine.py
git commit -m "refactor: move CHANNEL_COLORS to shared (S3 prep)"
```

### Task 7: `LocalState`

**Files:**
- Create: `controller/state.py`
- Test: `tests/test_local_state.py`

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for controller/state.py — Spark local exploration state."""

from controller.state import LocalState, CHANNEL_ORDER


def make_state():
    return LocalState()  # loads shared/data/word_blocks.json


def test_starts_on_subject_uncommitted():
    s = make_state()
    assert s.active == "subject"
    snap = s.snapshot()
    assert snap.channel == "subject"
    assert snap.committed is False
    assert snap.option_count > 0


def test_next_prev_wrap():
    s = make_state()
    n = len(s.options["subject"])
    for _ in range(n):
        s.next_option()
    assert s.index["subject"] == 0
    s.prev_option()
    assert s.index["subject"] == n - 1


def test_jump_wraps():
    s = make_state()
    n = len(s.options["subject"])
    s.jump(-5)
    assert s.index["subject"] == (n - 5) % n


def test_commit_and_uncommit():
    s = make_state()
    word = s.snapshot().candidate
    s.commit()
    assert s.committed_word["subject"] == word
    assert s.snapshot().committed is True
    s.uncommit()
    assert s.committed_word["subject"] is None
    assert s.snapshot().committed is False


def test_channel_cycle_wraps():
    s = make_state()
    for expected in ["context", "style", "engine", "subject"]:
        s.next_channel()
        assert s.active == expected


def test_engine_snapshot():
    s = make_state()
    while s.active != "engine":
        s.next_channel()
    snap = s.snapshot()
    assert snap.mode == "engine"
    assert snap.candidate == "SEND"
    assert snap.channel_color == (200, 150, 0)


def test_randomize_stays_in_range():
    s = make_state()
    for _ in range(20):
        s.randomize()
        assert 0 <= s.index["subject"] < len(s.options["subject"])


def test_send_payload_shape():
    s = make_state()
    s.commit()
    payload = s.send_payload()
    assert payload["channels"]["subject"] == s.committed_word["subject"]
    assert payload["channels"]["context"] is None
    assert payload["engine"]["operator"] == "swap"
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_local_state.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'controller.state'`

- [ ] **Step 3: Implement `controller/state.py`**

```python
"""Spark-local exploration state (spec: local-state inversion).

Spark owns channel/index/committed-word during exploration; Conductor
stays authority for sentence-of-record via the explicit `send` message.
"""

import json
import random

from shared.config import get_word_blocks_path
from shared.interfaces.display import StateSnapshot, CHANNEL_COLORS

CHANNEL_ORDER = ["subject", "context", "style", "engine"]
WORD_CHANNELS = ["subject", "context", "style"]
ENGINE_SETTINGS = ["send", "op"]
OPERATORS = ["swap", "lang", "ltr", "+con", "-con"]


class LocalState:
    """Owns exploration state; every mutation is instant and local."""

    def __init__(self, word_blocks_path=None):
        path = word_blocks_path or get_word_blocks_path()
        with open(path) as f:
            data = json.load(f)
        theme = data["theme_specific"]["cinematic_noir"]
        self.options = {c: theme[c.title()] for c in WORD_CHANNELS}
        self.index = {c: 0 for c in WORD_CHANNELS}
        self.committed_word = {c: None for c in WORD_CHANNELS}
        self.active = "subject"
        self.engine_setting = 0   # index into ENGINE_SETTINGS
        self.operator = 0         # index into OPERATORS

    # --- exploration ---

    def next_option(self) -> None:
        self._shift(1)

    def prev_option(self) -> None:
        self._shift(-1)

    def jump(self, delta: int) -> None:
        self._shift(delta)

    def _shift(self, delta: int) -> None:
        if self.active == "engine":
            if ENGINE_SETTINGS[self.engine_setting] == "op":
                self.operator = (self.operator + delta) % len(OPERATORS)
            return
        opts = self.options[self.active]
        self.index[self.active] = (self.index[self.active] + delta) % len(opts)

    def randomize(self) -> None:
        if self.active in WORD_CHANNELS:
            self.index[self.active] = random.randrange(len(self.options[self.active]))

    # --- commitment ---

    def commit(self) -> None:
        if self.active in WORD_CHANNELS:
            self.committed_word[self.active] = self._candidate()

    def uncommit(self) -> None:
        if self.active in WORD_CHANNELS:
            self.committed_word[self.active] = None

    def next_channel(self) -> None:
        i = CHANNEL_ORDER.index(self.active)
        self.active = CHANNEL_ORDER[(i + 1) % len(CHANNEL_ORDER)]

    def cycle_engine_setting(self) -> None:
        self.engine_setting = (self.engine_setting + 1) % len(ENGINE_SETTINGS)

    # --- views ---

    def _candidate(self) -> str:
        if self.active == "engine":
            setting = ENGINE_SETTINGS[self.engine_setting]
            return "SEND" if setting == "send" else f"OP {OPERATORS[self.operator]}"
        return self.options[self.active][self.index[self.active]]

    def snapshot(self) -> StateSnapshot:
        if self.active == "engine":
            return StateSnapshot(
                channel="engine",
                channel_color=CHANNEL_COLORS["engine"],
                option_index=self.engine_setting,
                option_count=len(ENGINE_SETTINGS),
                candidate=self._candidate(),
                committed=False,
                mode="engine",
                engine={"operator": OPERATORS[self.operator]},
            )
        word = self._candidate()
        return StateSnapshot(
            channel=self.active,
            channel_color=CHANNEL_COLORS[self.active],
            option_index=self.index[self.active],
            option_count=len(self.options[self.active]),
            candidate=word,
            committed=self.committed_word[self.active] == word,
            mode="word",
        )

    def send_payload(self) -> dict:
        return {
            "channels": dict(self.committed_word),
            "engine": {"operator": OPERATORS[self.operator]},
        }
```

Note on `committed` in snapshot: row-0 bar is solid only when the *current* candidate equals the committed word — cycling away from a committed word dims the bar, showing you've drifted off your commitment.

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_local_state.py -v`
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add controller/state.py tests/test_local_state.py
git commit -m "feat: Spark-local exploration state (S3)"
```

### Task 8: Wire buttons → LocalState; remove button messages

**Files:**
- Modify: `controller/controller.py`
- Modify: `conductor/conductor.py`

- [ ] **Step 1: Controller uses LocalState**

In `controller/controller.py`:

```python
from controller.state import LocalState
```

In `__init__`: add `self.local = LocalState()`; delete `self.current_state`. Remove the `self.bus.on("state", ...)` and `self.bus.on("patch", ...)` registrations and delete `_on_state`, `_on_patch` (Conductor state broadcasts are ignored now — Spark owns exploration). Remove `StateMessage`, `ButtonMessage` imports.

Ticker reads local state each frame:

```python
    async def _ticker_loop(self) -> None:
        """~15fps animation ticker: render local state every frame."""
        while self.running:
            self.display.push(render_frame(self.local.snapshot(), self.tick))
            self.tick += 1
            await asyncio.sleep(1 / 15)
```

Replace `_on_button_event`:

```python
    def _on_button_event(self, btn: str, event: str) -> None:
        """Local state update per press. No network traffic while exploring."""
        if event != "press":
            return
        print(f"[Spark] {btn} {event}", flush=True)
        if btn == "A":
            self.local.prev_option()
        elif btn == "B":
            self.local.next_option()
        elif btn == "X":
            self.local.commit()
        elif btn == "Y":
            self.local.next_channel()
```

- [ ] **Step 2: Conductor stops reacting to buttons/hello with renders**

In `conductor/conductor.py`:
- `_on_button`: replace body with a log-only stub (Controller no longer sends these; keymap dispatch dies with it):

```python
    def _on_button(self, msg: dict) -> None:
        """Legacy button events — ignored (Spark owns exploration now)."""
        logger.debug(f"Ignoring button message: {msg}")
```

- `_on_slate_button`: replace `_dispatch` call with log-only (spec: listener stays, slate keymap ignored):

```python
    def _on_slate_button(self, btn: str, event: str) -> None:
        """Slate buttons unwired per spark-centric-ui spec."""
        logger.debug(f"Slate button ignored: {btn} {event}")
```

- `_on_hello`: log only — no `_broadcast_state()` (e-ink must not redraw on reconnect):

```python
    def _on_hello(self, msg: dict) -> None:
        """Handle hello from Controller."""
        logger.info(f"Controller connected: {msg.get('device')} fw {msg.get('fw')}")
```

- In `start()`: replace the trailing `self._broadcast_state()` with `self._render_current()` — one boot render so the e-ink isn't blank; extract render-queueing from `_broadcast_state` so send (S4) reuses it:

```python
    def _render_current(self) -> None:
        """Queue an e-ink render of current registry state (latest-only)."""
        snapshot = StateSnapshot.from_registry(self.registry, mode="word")
        frame = self.image_backend.render_frame(snapshot)
        try:
            self.render_queue.put_nowait(frame)
        except asyncio.QueueFull:
            self.render_queue.get_nowait()
            self.render_queue.put_nowait(frame)
```

`_broadcast_state` can be deleted (nothing calls it after this task; S4's `_on_send` uses `_render_current`). Also delete the now-unused `_dispatch`, `_on_key` keymap plumbing? **No** — keep `_on_key` (it feeds `_on_slate_button` for quit handling in sim) but delete `_dispatch`, `self.actions`, and the keymap loads (`self.spark_keymap`, `self.slate_keymap`, `KEYMAPS_DIR`) plus `StateMessage`, `ButtonMessage`, `Keymap`, `normalize_action` imports. Dead code goes.

- [ ] **Step 3: Run suite**

Run: `python -m pytest tests/ -v`
Expected: all pass (bus tests exercise hello/state plumbing, unaffected)

- [ ] **Step 4: Sim demo**

Run both apps. All four Spark keys (a/b/x/y in pygame window) explore instantly; Slate window shows boot render then stays silent. Conductor terminal shows no button traffic.

- [ ] **Step 5: Commit**

```bash
git add controller/controller.py conductor/conductor.py
git commit -m "feat: local-state exploration on Spark, button messages removed (S3)"
```

---

## Stage S4 — Long-press + send

### Task 9: Release events through the input stack

**Files:**
- Modify: `controller/unicorn_mock.py`
- Modify: `controller/display.py`
- Modify: `controller/buttons.py`
- Modify: `controller/controller.py`

- [ ] **Step 1: Mock emits release**

In `controller/unicorn_mock.py` `_process_events`, KEYUP branch — after `self.button_states[button] = False` add:

```python
                    if self.button_release_callback:
                        self.button_release_callback(button)
```

In `__init__` (next to `self.button_callback = None`):

```python
        self.button_release_callback = None
```

Add registration method (next to `on_button_pressed`):

```python
    def on_button_released(self, callback):
        """Register callback for button release events."""
        self.button_release_callback = callback
```

- [ ] **Step 2: SparkMock forwards event kind**

In `controller/display.py` `SparkMock.__init__` add:

```python
        self.unicorn.on_button_released(self._on_button_release)
```

Change `_on_button_pin` and add release handler — `on_key` callback signature becomes `(char, event)`:

```python
    def _on_button_pin(self, pin) -> None:
        """Handle button press from unicorn mock."""
        self._emit(pin, "press")

    def _on_button_release(self, pin) -> None:
        self._emit(pin, "release")

    def _emit(self, pin, event: str) -> None:
        if pin == 'q':
            if self.on_key:
                self.on_key('q', "press")
            return
        pin_map = {5: 'a', 6: 'b', 16: 'x', 24: 'y'}
        char = pin_map.get(pin)
        if char and self.on_key:
            self.on_key(char, event)
```

- [ ] **Step 3: GPIO wires `when_released`**

In `controller/buttons.py` `GPIOButtonListener.__init__` hardware loop:

```python
                    btn.when_pressed = lambda n=name: self._on_event(n, "press")
                    btn.when_released = lambda n=name: self._on_event(n, "release")
```

Rename `_on_press` accordingly:

```python
    def _on_event(self, btn_name: str, event: str) -> None:
        """Handle GPIO button edge."""
        if self.handler:
            self.handler(btn_name, event)
```

`KeyboardListener` (termios fallback) stays press-only:

```python
# ponytail: termios gives no key-up — long-press unsupported in terminal
# fallback; pygame window (sim) and GPIO (hardware) both deliver releases
```

- [ ] **Step 4: Controller `_on_key` accepts event**

In `controller/controller.py`:

```python
    def _on_key(self, char: str, event: str = "press") -> None:
        """Handle key event from pygame display."""
        key_map = {'a': 'A', 'b': 'B', 'x': 'X', 'y': 'Y'}
        if char == 'q':
            self._on_exit_signal()
        elif char in key_map:
            self._on_button_event(key_map[char], event)
```

`_on_button_event` already ignores `event != "press"` — releases flow through harmlessly until Task 12 consumes them.

- [ ] **Step 5: Run suite + sim smoke test, commit**

Run: `python -m pytest tests/ -v` — all pass. Sim: presses still work.

```bash
git add controller/unicorn_mock.py controller/display.py controller/buttons.py controller/controller.py
git commit -m "feat: button release events through sim + GPIO input stack (S4)"
```

### Task 10: `LongPressDetector`

**Files:**
- Create: `controller/longpress.py`
- Test: `tests/test_longpress.py`

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for controller/longpress.py — fake-clock timing."""

from controller.longpress import LongPressDetector


def test_short_press():
    d = LongPressDetector(threshold=0.6)
    d.press("A", now=0.0)
    assert d.poll(now=0.3) == []
    assert d.release("A", now=0.3) == "short"


def test_long_fires_while_held():
    d = LongPressDetector(threshold=0.6)
    d.press("Y", now=0.0)
    assert d.poll(now=0.5) == []
    assert d.poll(now=0.61) == ["Y"]
    assert d.poll(now=0.7) == []          # fires once
    assert d.release("Y", now=1.0) is None  # no short after long


def test_release_without_press_is_noop():
    d = LongPressDetector(threshold=0.6)
    assert d.release("X", now=1.0) is None


def test_hold_fraction():
    d = LongPressDetector(threshold=0.6)
    d.press("B", now=0.0)
    assert d.hold_fraction("B", now=0.3) == 0.5
    assert d.hold_fraction("B", now=0.9) == 1.0
    assert d.hold_fraction("A", now=0.3) == 0.0
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_longpress.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Implement `controller/longpress.py`**

```python
"""Long-press detection: fires at threshold while held (not on release)."""

# ponytail: threshold constant, tune on hardware
THRESHOLD_S = 0.6


class LongPressDetector:
    """Pure, poll-based. Feed press/release with timestamps; poll each tick."""

    def __init__(self, threshold: float = THRESHOLD_S):
        self.threshold = threshold
        self.down = {}      # btn -> press timestamp
        self.fired = set()  # btns whose long already fired this hold

    def press(self, btn: str, now: float) -> None:
        self.down[btn] = now
        self.fired.discard(btn)

    def release(self, btn: str, now: float):
        """Returns 'short' if released before threshold, else None."""
        t = self.down.pop(btn, None)
        if t is None or btn in self.fired:
            self.fired.discard(btn)
            return None
        return "short"

    def poll(self, now: float) -> list:
        """Buttons whose long-press fires at this instant (each fires once)."""
        longs = [
            b for b, t in self.down.items()
            if now - t >= self.threshold and b not in self.fired
        ]
        self.fired.update(longs)
        return longs

    def hold_fraction(self, btn: str, now: float) -> float:
        """0..1 progress toward threshold — drives the growing glint."""
        t = self.down.get(btn)
        if t is None:
            return 0.0
        return min(1.0, (now - t) / self.threshold)
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_longpress.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add controller/longpress.py tests/test_longpress.py
git commit -m "feat: poll-based long-press detector (S4)"
```

### Task 11: `SendMessage` + Conductor send handler

**Files:**
- Modify: `shared/messages.py`
- Modify: `conductor/conductor.py`
- Test: `tests/test_send_roundtrip.py`

- [ ] **Step 1: Write the failing test**

```python
"""Send round-trip: SendMessage over bus updates Conductor registry."""

import asyncio
import pytest
from pathlib import Path

from conductor.conductor import Conductor
from shared.bus_websocket import WebSocketClient
from shared.messages import SendMessage
from shared.config import get_word_blocks_path


@pytest.mark.asyncio
async def test_send_updates_registry_and_queues_render():
    conductor = Conductor(get_word_blocks_path())
    client = WebSocketClient()

    await conductor.start("localhost", 18768)
    await client.connect("localhost", 18768)
    await asyncio.sleep(0.1)

    word = conductor.registry.channels["subject"].options[2]
    msg = SendMessage(
        channels={"subject": word, "context": None, "style": None},
        engine={"operator": "lang"},
    )
    await client.send(msg.model_dump())
    await asyncio.sleep(0.2)

    subject = conductor.registry.channels["subject"]
    assert subject.committed is True
    assert subject.get_candidate() == word
    assert conductor.registry.channels["context"].committed is False
    assert conductor.registry.channels["engine"].operator == "lang"

    await client.disconnect()
    conductor.server_running = False
    await conductor.shutdown()
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_send_roundtrip.py -v`
Expected: FAIL — `ImportError: cannot import name 'SendMessage'`

- [ ] **Step 3: Add `SendMessage`** (in `shared/messages.py`, after `PatchMessage`)

```python
class SendMessage(BaseMessage):
    """Explicit send from Controller: committed words + engine settings."""
    type: str = Field(default="send", frozen=True)
    channels: Dict[str, Optional[str]]  # subject/context/style -> word or None
    engine: Dict[str, Any] = Field(default_factory=dict)
```

And a branch in `message_from_dict`:

```python
    elif msg_type == "send":
        return SendMessage(**data)
```

- [ ] **Step 4: Conductor handles send** (in `conductor/conductor.py`)

Register in `__init__`:

```python
        self.bus.on("send", self._on_send)
```

Handler:

```python
    def _on_send(self, msg: dict) -> None:
        """Explicit send: adopt committed words, queue one e-ink render."""
        for ch_id, word in msg.get("channels", {}).items():
            ch = self.registry.channels.get(ch_id)
            if ch is None or ch_id == "engine":
                continue
            if word in ch.options:
                ch.option_index = ch.options.index(word)
                ch.committed = True
            else:
                ch.committed = False  # None or unknown word → cleared
        op = msg.get("engine", {}).get("operator")
        if op:
            self.registry.channels["engine"].operator = op
        logger.info(f"Send: {self.registry.render_sentence()}")
        self._render_current()
```

Empty sentence is allowed (spec edge case) — `render_sentence()` yields `"[empty]"` placeholder, render proceeds.

- [ ] **Step 5: Run tests**

Run: `python -m pytest tests/test_send_roundtrip.py tests/ -v`
Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add shared/messages.py conductor/conductor.py tests/test_send_roundtrip.py
git commit -m "feat: SendMessage + Conductor send handler (S4)"
```

### Task 12: Controller long-press wiring + send

**Files:**
- Modify: `controller/controller.py`

- [ ] **Step 1: Route events through detector; dispatch gestures**

In `controller/controller.py`:

```python
import time
from controller.longpress import LongPressDetector
from shared.messages import SendMessage
```

In `__init__`: `self.detector = LongPressDetector()`.

Replace `_on_button_event` and add gesture dispatch:

```python
    def _on_button_event(self, btn: str, event: str) -> None:
        """Feed press/release into long-press detector."""
        now = time.monotonic()
        if event == "press":
            self.detector.press(btn, now)
        elif event == "release":
            if self.detector.release(btn, now) == "short":
                self._on_gesture(btn, "short")

    def _on_gesture(self, btn: str, kind: str) -> None:
        """Dispatch button grammar (spec §2, revised for spatial mapping)."""
        print(f"[Spark] {btn} {kind}", flush=True)
        s = self.local
        if btn == "A":
            s.prev_option()          # long: jump -5 (S5)
        elif btn == "X":
            s.next_option()          # long: jump +5 (S5)
        elif btn == "B":
            s.commit()               # long: uncommit (S5)
        elif btn == "Y":
            if kind == "long" and s.active == "engine":
                self._schedule(self._send())
            elif kind == "short":
                s.next_channel()
            # long on non-engine: randomize (S5)

    async def _send(self) -> None:
        """Explicit send → Conductor renders e-ink once."""
        msg = SendMessage(**self.local.send_payload())
        await self.bus.send(msg.model_dump())
        logger.info("Sent to Slate")
```

Ticker polls the detector for long-press firing:

```python
    async def _ticker_loop(self) -> None:
        """~15fps animation ticker: long-press poll + render."""
        while self.running:
            for btn in self.detector.poll(time.monotonic()):
                self._on_gesture(btn, "long")
            self.display.push(render_frame(self.local.snapshot(), self.tick))
            self.tick += 1
            await asyncio.sleep(1 / 15)
```

Note: short actions now fire on **release** (must wait to distinguish from long); long fires at 600ms while held. Terminal keyboard fallback (press-only) still triggers shorts because `release()` is never called there — add compatibility: in `_on_button_event`, if the source can't produce releases nothing happens. Acceptable: pygame window is the sim input (per spec §7); terminal fallback loses buttons but keeps `q` to quit.

- [ ] **Step 2: Run suite**

Run: `python -m pytest tests/ -v`
Expected: all pass

- [ ] **Step 3: Sim demo (end-to-end send)**

Run both apps. Explore + commit words, Y to Engine (shows `SEND`), hold Y ≥600ms → Slate renders once with the sent sentence. Rapid exploring never touches Slate.

- [ ] **Step 4: Commit**

```bash
git add controller/controller.py
git commit -m "feat: long-press gestures + explicit send to Slate (S4)"
```

---

## Stage S5 — Polish

### Task 13: Effects plumbing + commit flash + uncommit

**Files:**
- Modify: `controller/render.py`
- Modify: `controller/controller.py`
- Test: `tests/test_render.py`

- [ ] **Step 1: Write the failing tests** (append to `tests/test_render.py`)

```python
from controller.render import Effects


def test_commit_flash_fills_matrix():
    e = Effects(flash_until=2, flash_color=(0, 200, 80))
    frame = render_frame(make_state(), tick=0, effects=e)
    assert frame[3][8] == (0, 200, 80)
    assert frame[0][0] == (0, 200, 80)


def test_flash_expires():
    e = Effects(flash_until=2, flash_color=(0, 200, 80))
    frame = render_frame(make_state(candidate="HI"), tick=2, effects=e)
    assert frame[2][3] == (0, 0, 0)  # normal render resumed
```

- [ ] **Step 2: Run to verify failure** — `ImportError: cannot import name 'Effects'`

- [ ] **Step 3: Implement** (in `controller/render.py`)

```python
from dataclasses import dataclass


@dataclass
class Effects:
    """Transient overlay state owned by the ticker."""
    flash_until: int = 0                      # tick before which full-matrix flash shows
    flash_color: tuple = (255, 255, 255)
    glint_until: int = 0                      # tick before which press glint shows
    glint_btn: str = ""                       # "A" | "B" | "X" | "Y"
    hold_btn: str = ""                        # button currently held
    hold_frac: float = 0.0                    # 0..1 growing glint
```

Change signature and add flash short-circuit at top of `render_frame`:

```python
def render_frame(state: StateSnapshot, tick: int, effects: Effects = None) -> Frame:
    """Pure render. No I/O, no side effects."""
    if effects and tick < effects.flash_until:
        return [[effects.flash_color for _ in range(WIDTH)] for _ in range(HEIGHT)]
    frame = blank_frame()
    ...
```

(Glint overlay lands in Task 15; `Effects` carries the fields now so the shape is stable.)

- [ ] **Step 4: Wire flash + uncommit** (in `controller/controller.py`)

```python
from controller.render import render_frame, Effects
```

In `__init__`: `self.effects = Effects()`.

In `_on_gesture`, X branch:

```python
        elif btn == "X":
            if kind == "long":
                s.uncommit()
            else:
                s.commit()
                snap = s.snapshot()
                self.effects.flash_until = self.tick + 2
                self.effects.flash_color = snap.channel_color
```

Ticker passes effects:

```python
            self.display.push(render_frame(self.local.snapshot(), self.tick, self.effects))
```

- [ ] **Step 5: Run suite, sim demo, commit**

Run: `python -m pytest tests/ -v` — all pass. Sim: X flashes channel color 2 frames; hold X clears channel (row-0 bar dims).

```bash
git add controller/render.py controller/controller.py tests/test_render.py
git commit -m "feat: effects overlay, commit flash, uncommit (S5)"
```

### Task 14: Jump ±5 + randomize

**Files:**
- Modify: `controller/controller.py`

- [ ] **Step 1: Fill remaining long-press branches in `_on_gesture`**

```python
        if btn == "A":
            s.jump(-5) if kind == "long" else s.prev_option()
        elif btn == "X":
            s.jump(5) if kind == "long" else s.next_option()
        ...
        elif btn == "Y":
            if kind == "long":
                if s.active == "engine":
                    self._schedule(self._send())
                else:
                    s.randomize()
            else:
                s.next_channel()
```

- [ ] **Step 2: Run suite, sim demo, commit**

State transitions already covered by `tests/test_local_state.py` (jump/randomize). Sim: hold A/B jumps 5; hold Y on a word channel randomizes.

```bash
git add controller/controller.py
git commit -m "feat: jump +-5 and randomize long-presses (S5)"
```

### Task 15: Edge glints (press + growing hold)

**Files:**
- Modify: `controller/render.py`
- Modify: `controller/controller.py`
- Test: `tests/test_render.py`

- [ ] **Step 1: Write the failing tests** (append to `tests/test_render.py`)

```python
def test_press_glint_left_top_for_a():
    e = Effects(glint_until=1, glint_btn="A")
    frame = render_frame(make_state(), tick=0, effects=e)
    assert frame[0][0] == (255, 255, 255)
    assert frame[2][0] == (255, 255, 255)
    assert frame[6][0] != (255, 255, 255)  # bottom half untouched


def test_hold_glint_grows():
    e = Effects(hold_btn="Y", hold_frac=1.0)
    frame = render_frame(make_state(), tick=0, effects=e)
    assert frame[4][16] == (255, 255, 255)
    assert frame[6][16] == (255, 255, 255)
```

- [ ] **Step 2: Run to verify failure** — asserts fail (no glint drawn)

- [ ] **Step 3: Implement overlay** (append before `return frame` in `render_frame`)

```python
    # Edge glints: left col for A/B, right col for X/Y; top half A/X, bottom B/Y
    _GLINT = {"A": (0, range(0, 3)), "B": (0, range(4, 7)),
              "X": (WIDTH - 1, range(0, 3)), "Y": (WIDTH - 1, range(4, 7))}
    if effects:
        if tick < effects.glint_until and effects.glint_btn in _GLINT:
            x, rows = _GLINT[effects.glint_btn]
            for y in rows:
                frame[y][x] = (255, 255, 255)
        if effects.hold_btn in _GLINT and effects.hold_frac > 0:
            x, rows = _GLINT[effects.hold_btn]
            rows = list(rows)
            lit = round(len(rows) * effects.hold_frac)
            for y in rows[:lit]:
                frame[y][x] = (255, 255, 255)
```

(Move `_GLINT` to module level next to `WIDTH`/`HEIGHT`.)

- [ ] **Step 4: Wire in controller**

In `_on_button_event` press branch:

```python
        if event == "press":
            self.detector.press(btn, now)
            self.effects.glint_until = self.tick + 1
            self.effects.glint_btn = btn
```

In `_ticker_loop`, before push — growing glint tracks the longest-held button:

```python
            now = time.monotonic()
            for btn in self.detector.poll(now):
                self._on_gesture(btn, "long")
            held = min(self.detector.down, key=self.detector.down.get, default="")
            self.effects.hold_btn = held
            self.effects.hold_frac = self.detector.hold_fraction(held, now) if held else 0.0
```

- [ ] **Step 5: Run suite, sim demo, commit**

Run: `python -m pytest tests/ -v` — all pass. Sim: taps show 1-frame edge glint; holding shows the glint growing until the long fires at 600ms.

```bash
git add controller/render.py controller/controller.py tests/test_render.py
git commit -m "feat: press glints + growing hold glint (S5)"
```

### Task 16: Engine OP setting + send-fail red flash

**Files:**
- Modify: `shared/bus_websocket.py`
- Modify: `controller/controller.py`
- Test: `tests/test_local_state.py`

- [ ] **Step 1: Write the failing test** (append to `tests/test_local_state.py`)

```python
def test_engine_op_setting_cycles_operator():
    s = make_state()
    while s.active != "engine":
        s.next_channel()
    s.cycle_engine_setting()           # setting: send -> op
    assert s.snapshot().candidate == "OP SWAP"
    s.next_option()                    # B cycles operator value
    assert s.snapshot().candidate == "OP LANG"
    assert s.send_payload()["engine"]["operator"] == "lang"
```

- [ ] **Step 2: Run to verify failure**

`"OP swap"` vs `"OP SWAP"` — `_candidate` needs uppercase. Fix in `controller/state.py`:

```python
            return "SEND" if setting == "send" else f"OP {OPERATORS[self.operator].upper()}"
```

Setting cycling needs a gesture: X on engine cycles settings (X commit is word-channel-only, so the button is free there). In `controller/controller.py` `_on_gesture` X branch:

```python
        elif btn == "X":
            if s.active == "engine":
                s.cycle_engine_setting()
            elif kind == "long":
                s.uncommit()
            else:
                s.commit()
                ...
```

- [ ] **Step 3: Run tests** — `python -m pytest tests/test_local_state.py -v` — all pass.

- [ ] **Step 4: `bus.send` reports success; red flash on failure**

In `shared/bus_websocket.py`, replace `WebSocketClient.send` (currently lines 89–96) with:

```python
    async def send(self, msg: Dict[str, Any]) -> bool:
        """Send message to server. Returns False if dropped (disconnected)."""
        if not self.websocket:
            return False
        try:
            await self.websocket.send(json.dumps(msg))
            return True
        except websockets.exceptions.ConnectionClosed:
            logger.warning(f"Send dropped (disconnected): {msg.get('type')}")
            return False
```

(Existing callers ignore the return value — no other changes needed.)

In `controller/controller.py` `_send`:

```python
    async def _send(self) -> None:
        """Explicit send → Conductor renders e-ink once."""
        msg = SendMessage(**self.local.send_payload())
        if await self.bus.send(msg.model_dump()):
            logger.info("Sent to Slate")
        else:
            self.effects.flash_until = self.tick + 3
            self.effects.flash_color = (255, 0, 0)  # spec: red flash when disconnected
```

- [ ] **Step 5: Run full suite, sim demo, commit**

Run: `python -m pytest tests/ -v` — all pass. Sim demo full grammar: explore, commit-flash, uncommit, jump, randomize, engine OP cycling, send; kill Conductor and long-Y → red flash.

```bash
git add shared/bus_websocket.py controller/controller.py controller/state.py tests/test_local_state.py
git commit -m "feat: engine OP setting, send-failure red flash (S5)"
```

---

## Final verification

- [ ] `python -m pytest tests/ -v` — full suite green
- [ ] Sim demo: full S5 grammar end-to-end (checklist per stage demos above)
- [ ] Hardware check (when available): brightness, 600ms threshold feel, long-press on GPIO — knobs: `FLYBALL_SPARK_BRIGHTNESS`, `controller/longpress.py:THRESHOLD_S`
