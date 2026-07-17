# Flyball M0–M1: Bus + State Machine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the core WebSocket bus, state machine (channels/options/stack), and both terminal/e-paper mocks so the full two-handed UI loop runs in macOS simulation before any hardware.

**Architecture:**
- **Conductor** (Slate authority) runs a WebSocket server on `localhost:8765`, owns all state (channels, option indices, sentence stack), and interprets button events into state mutations.
- **Controller** (Spark client) connects to the Conductor, receives semantic state snapshots, renders a 17×7 ANSI terminal mock with colour bar + pips + scrolling text, and emits button events on keyboard presses.
- **Bus abstraction** (`shared/interfaces/bus.py`) defines `send(msg)` / `on(msg_type, handler)`, letting WebSocket swap for MQTT later without touching app code.
- **Display abstractions** (`shared/interfaces/display.py`) separate real Inky/Unicorn from `InkyMock` (PIL image) and `SparkMock` (ANSI terminal), so sim works on macOS.
- **State machine** lives in `conductor/state_machine.py` — channels (Subject/Context/Style/Engine), option lists loaded from `shared/data/word_blocks.json`, stack of committed options assembles into a sentence string.
- **TDD throughout:** every component has a failing test first, then minimal implementation.

**Tech Stack:**
- Python 3.11+, WebSocket (`websockets` lib), PIL (Pillow) for `InkyMock`, ANSI terminal colours for `SparkMock`.
- Message schema: flat JSON objects with `{"type": "...", ...}` per `docs/03-architecture.md`.
- Config via env vars / `config.toml` (no hardcoded secrets/IPs).

---

## File Structure

### New Files

**Shared (interfaces + config):**
- `shared/__init__.py` — empty marker.
- `shared/config.py` — load `FLYBALL_CONDUCTOR_HOST` (default `localhost`), `FLYBALL_CONDUCTOR_PORT` (default `8765`), image gen key, etc. from env / `config.toml`.
- `shared/messages.py` — Pydantic models for message types: `HelloMessage`, `StateMessage`, `ButtonMessage`, `PingMessage`, `PongMessage`, `ToastMessage`, `PatchMessage`.
- `shared/interfaces/__init__.py` — empty marker.
- `shared/interfaces/bus.py` — Abstract base classes `Bus` (with `send(msg: Dict)`, `on(msg_type: str, handler)`, `connect()`, `disconnect()`), `BusServer`, `BusClient`.
- `shared/interfaces/display.py` — Abstract base `Display` with `render(state: StateSnapshot)`, `close()`. Concrete: `InkyMock` (PIL → show), `SparkMock` (ANSI → stdout).
- `shared/interfaces/buttons.py` — Abstract `ButtonListener` with `on(btn_event, handler)`, `start()`, `stop()`. Concrete: `KeyboardListener` (stdin polling / getch sim), `GPIOListener` (stub for hardware).
- `shared/interfaces/image_backend.py` — Abstract `ImageBackend` with `generate(prompt: str) -> PIL.Image`. M1: stub returns a solid-colour placeholder.
- `shared/interfaces/evolver.py` — Abstract `Evolver` with `evolve(prompt: str, lineage: List) -> str`. M1: stub returns the same prompt.

**Conductor (Slate):**
- `conductor/__init__.py` — empty marker.
- `conductor/__main__.py` — entry point; instantiate Conductor, run async loop.
- `conductor/conductor.py` — Main `Conductor` class: owns the WebSocket server, state, and button handlers. Methods: `handle_button(btn, event)`, `button_prev()`, `button_next()`, `button_commit()`, `button_shift()`, `change_channel(channel_id)`, `broadcast_state()`.
- `conductor/state_machine.py` — `StateSnapshot` (current channel, option index, count, candidate text, committed flag, engine settings, mode). `ChannelRegistry` (load channels + options from `word_blocks.json`). Methods: `next_option()`, `prev_option()`, `commit_option()`, `get_current_candidate()`, `render_sentence()`, `shift_operator()`, etc.
- `conductor/display.py` — `SlateDisplay` abstract class; `InkyMock` concrete: renders PIL image with sideways menu strip (A/B/C/D labels) + sentence ribbon at bottom, calls PIL `.show()`.

**Controller (Spark):**
- `controller/__init__.py` — empty marker.
- `controller/__main__.py` — entry point; instantiate Controller, connect to Conductor, run loop.
- `controller/controller.py` — Main `Controller` class: holds WebSocket client, listens for button events, re-renders on state updates. Methods: `connect()`, `on_state(state_msg)`, `on_button_press(btn)`, `render()`.
- `controller/display.py` — `SparkDisplay` abstract class; `SparkMock` concrete: renders 17×7 ANSI matrix (row 0 = colour bar, row 1 = pips, rows 2–4 = first line of text, row 5 = spacer, rows 6 = second line), scrolls candidate text right-to-left in channel colour.

**Tests:**
- `tests/__init__.py` — empty marker.
- `tests/test_messages.py` — Pydantic encoding/decoding for all message types.
- `tests/test_state_machine.py` — `ChannelRegistry`, `StateSnapshot`, prev/next/commit logic, sentence rendering.
- `tests/test_bus_integration.py` — WebSocket client/server round-trip: `hello` → `state`, `button` → conductor receives it, `ping` → `pong`.
- `tests/test_display_mocks.py` — `SparkMock` renders without crashing, `InkyMock` generates a PIL image.

### Modified Files

- `shared/data/word_blocks.json` — already exists; will load from here.
- `.gitignore` — add `__pycache__/`, `*.pyc`, `.pytest_cache/`, `config.toml`.

---

## Task Breakdown

### Task 1: Scaffold repo structure + shared config

**Files:**
- Create: `shared/__init__.py`, `shared/config.py`
- Create: `shared/interfaces/__init__.py`, `shared/interfaces/bus.py`, `shared/interfaces/display.py`, `shared/interfaces/buttons.py`, `shared/interfaces/image_backend.py`, `shared/interfaces/evolver.py`
- Create: `conductor/__init__.py`, `controller/__init__.py`
- Create: `tests/__init__.py`
- Modify: `.gitignore`

#### Steps

- [ ] **Step 1: Create shared module structure**

```bash
mkdir -p shared/interfaces conductor controller tests
touch shared/__init__.py shared/interfaces/__init__.py conductor/__init__.py controller/__init__.py tests/__init__.py
```

- [ ] **Step 2: Write config.py with env loader**

Create `shared/config.py`:

```python
"""Config loader from environment / config.toml."""

import os
import platform
from pathlib import Path
from typing import Optional

IS_SIMULATION = platform.system() != "Linux"

def get_conductor_host() -> str:
    """Resolve Conductor hostname: env → localhost (sim) → slate.local (hardware)."""
    if os.getenv("FLYBALL_CONDUCTOR_HOST"):
        return os.getenv("FLYBALL_CONDUCTOR_HOST")
    return "localhost" if IS_SIMULATION else "slate.local"

def get_conductor_port() -> int:
    """WebSocket port."""
    return int(os.getenv("FLYBALL_CONDUCTOR_PORT", "8765"))

def get_config_path() -> Optional[Path]:
    """Path to config.toml if it exists."""
    config_path = Path.home() / ".flyball" / "config.toml"
    return config_path if config_path.exists() else None

def get_word_blocks_path() -> Path:
    """Path to word_blocks.json data file."""
    return Path(__file__).parent / "data" / "word_blocks.json"
```

- [ ] **Step 3: Create abstract Bus interface**

Create `shared/interfaces/bus.py`:

```python
"""Bus abstraction for transport (WebSocket now, MQTT later)."""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional


class Bus(ABC):
    """Abstract message bus."""

    @abstractmethod
    async def send(self, msg: Dict[str, Any]) -> None:
        """Send a message."""
        pass

    @abstractmethod
    def on(self, msg_type: str, handler: Callable[[Dict[str, Any]], None]) -> None:
        """Register handler for message type."""
        pass

    @abstractmethod
    async def connect(self) -> None:
        """Connect to the bus."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the bus."""
        pass


class BusServer(Bus):
    """Server-side bus (Conductor listens)."""

    @abstractmethod
    async def start(self, host: str, port: int) -> None:
        """Start listening."""
        pass


class BusClient(Bus):
    """Client-side bus (Controller connects)."""

    @abstractmethod
    async def connect(self, host: str, port: int) -> None:
        """Connect to a server."""
        pass
```

- [ ] **Step 4: Create abstract Display interface**

Create `shared/interfaces/display.py`:

```python
"""Display abstraction (Inky / Unicorn + mocks)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List


@dataclass
class StateSnapshot:
    """Current state snapshot sent by Conductor to Controller."""
    channel: str  # "subject" | "context" | "style" | "engine"
    channel_color: tuple  # (r, g, b)
    option_index: int
    option_count: int
    candidate: str  # text to display
    committed: bool
    mode: str  # "word" | "engine"
    engine: Optional[dict] = None  # {"loop": bool, "speed_s": int, "operator": str, "queue_depth": int}


class Display(ABC):
    """Abstract display."""

    @abstractmethod
    def render(self, state: StateSnapshot) -> None:
        """Render state to display."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Clean up display."""
        pass
```

- [ ] **Step 5: Create abstract Buttons interface**

Create `shared/interfaces/buttons.py`:

```python
"""Button listener abstraction (GPIO / keyboard sim)."""

from abc import ABC, abstractmethod
from typing import Callable


class ButtonListener(ABC):
    """Abstract button listener."""

    @abstractmethod
    def on(self, handler: Callable[[str, str], None]) -> None:
        """Register handler: (btn: str, event: str) -> None. Events: press, release, hold."""
        pass

    @abstractmethod
    def start(self) -> None:
        """Start listening."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stop listening."""
        pass
```

- [ ] **Step 6: Create stub ImageBackend interface**

Create `shared/interfaces/image_backend.py`:

```python
"""Image generation backend abstraction."""

from abc import ABC, abstractmethod
from PIL import Image


class ImageBackend(ABC):
    """Abstract image generator."""

    @abstractmethod
    async def generate(self, prompt: str) -> Image.Image:
        """Generate image from prompt."""
        pass
```

- [ ] **Step 7: Create stub Evolver interface**

Create `shared/interfaces/evolver.py`:

```python
"""Evolution operator abstraction."""

from abc import ABC, abstractmethod
from typing import List


class Evolver(ABC):
    """Abstract prompt evolver."""

    @abstractmethod
    def evolve(self, prompt: str, lineage: List[str]) -> str:
        """Mutate prompt. Lineage is history of past prompts."""
        pass
```

- [ ] **Step 8: Update .gitignore**

Add to `.gitignore`:

```
__pycache__/
*.pyc
.pytest_cache/
*.egg-info/
dist/
build/
config.toml
.env
.DS_Store
```

- [ ] **Step 9: Commit**

```bash
git add shared/ conductor/ controller/ tests/ .gitignore
git commit -m "feat: scaffold repo structure + shared interfaces"
```

---

### Task 2: Message schema (Pydantic models)

**Files:**
- Create: `shared/messages.py`
- Create: `tests/test_messages.py`

#### Steps

- [ ] **Step 1: Write test for message encoding/decoding**

Create `tests/test_messages.py`:

```python
"""Test message schema."""

import json
import pytest
from shared.messages import (
    HelloMessage,
    StateMessage,
    ButtonMessage,
    PingMessage,
    PongMessage,
    ToastMessage,
    PatchMessage,
)


def test_hello_message():
    """HelloMessage serializes to dict."""
    msg = HelloMessage(device="spark", fw="0.1.0")
    as_dict = msg.model_dump()
    assert as_dict["type"] == "hello"
    assert as_dict["device"] == "spark"
    assert as_dict["fw"] == "0.1.0"


def test_hello_message_from_json():
    """HelloMessage deserializes from dict."""
    data = {"type": "hello", "device": "spark", "fw": "0.1.0"}
    msg = HelloMessage(**data)
    assert msg.device == "spark"


def test_state_message():
    """StateMessage includes all state fields."""
    msg = StateMessage(
        channel="subject",
        channel_color=(0, 200, 80),
        option_index=2,
        option_count=5,
        candidate="Detective",
        committed=True,
        mode="word",
    )
    as_dict = msg.model_dump()
    assert as_dict["type"] == "state"
    assert as_dict["channel"] == "subject"
    assert as_dict["option_index"] == 2


def test_button_message():
    """ButtonMessage captures press/release/hold."""
    msg = ButtonMessage(btn="A", event="press")
    as_dict = msg.model_dump()
    assert as_dict["type"] == "button"
    assert as_dict["btn"] == "A"
    assert as_dict["event"] == "press"


def test_button_message_hold_with_ms():
    """ButtonMessage hold includes duration."""
    msg = ButtonMessage(btn="Y", event="hold", ms=800)
    as_dict = msg.model_dump(exclude_none=True)
    assert as_dict["ms"] == 800


def test_ping_pong():
    """Ping and Pong messages."""
    ping = PingMessage()
    assert ping.model_dump()["type"] == "ping"

    pong = PongMessage()
    assert pong.model_dump()["type"] == "pong"


def test_toast_message():
    """Toast message for brief Spark flash."""
    msg = ToastMessage(text="SENT", color=(255, 180, 0))
    as_dict = msg.model_dump()
    assert as_dict["type"] == "toast"
    assert as_dict["text"] == "SENT"


def test_patch_message():
    """Patch message for incremental updates."""
    msg = PatchMessage(candidate="Silent Dancer", option_index=3)
    as_dict = msg.model_dump(exclude_none=True)
    assert as_dict["type"] == "patch"
    assert "candidate" in as_dict
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_messages.py -v
```

Expected: `ModuleNotFoundError: No module named 'shared.messages'`

- [ ] **Step 3: Write messages.py with Pydantic models**

Create `shared/messages.py`:

```python
"""Message schema for bus transport."""

from pydantic import BaseModel, Field
from typing import Optional, Tuple, Dict, Any


class BaseMessage(BaseModel):
    """Base message with type field."""
    type: str


class HelloMessage(BaseMessage):
    """Controller introduction."""
    type: str = Field(default="hello", frozen=True)
    device: str  # "spark" or "slate"
    fw: str  # firmware version


class StateMessage(BaseMessage):
    """Full state snapshot from Conductor to Controller."""
    type: str = Field(default="state", frozen=True)
    channel: str
    channel_color: Tuple[int, int, int]
    option_index: int
    option_count: int
    candidate: str
    committed: bool
    mode: str  # "word" | "engine"
    engine: Optional[Dict[str, Any]] = None


class ButtonMessage(BaseMessage):
    """Button event from Controller to Conductor."""
    type: str = Field(default="button", frozen=True)
    btn: str  # "A", "B", "X", "Y" (Spark) or "A", "B", "C", "D" (Slate)
    event: str  # "press", "release", "hold"
    ms: Optional[int] = None  # hold duration


class PingMessage(BaseMessage):
    """Heartbeat from either side."""
    type: str = Field(default="ping", frozen=True)


class PongMessage(BaseMessage):
    """Heartbeat response."""
    type: str = Field(default="pong", frozen=True)


class ToastMessage(BaseMessage):
    """Brief toast message for Spark (e.g. flash on commit)."""
    type: str = Field(default="toast", frozen=True)
    text: str
    color: Tuple[int, int, int]


class PatchMessage(BaseMessage):
    """Incremental state update (optimization; optional for M0)."""
    type: str = Field(default="patch", frozen=True)
    candidate: Optional[str] = None
    option_index: Optional[int] = None
    committed: Optional[bool] = None


# Helper: create message from dict
def message_from_dict(data: Dict[str, Any]) -> BaseMessage:
    """Deserialize message dict to appropriate type."""
    msg_type = data.get("type")
    if msg_type == "hello":
        return HelloMessage(**data)
    elif msg_type == "state":
        return StateMessage(**data)
    elif msg_type == "button":
        return ButtonMessage(**data)
    elif msg_type == "ping":
        return PingMessage(**data)
    elif msg_type == "pong":
        return PongMessage(**data)
    elif msg_type == "toast":
        return ToastMessage(**data)
    elif msg_type == "patch":
        return PatchMessage(**data)
    else:
        raise ValueError(f"Unknown message type: {msg_type}")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_messages.py -v
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add shared/messages.py tests/test_messages.py
git commit -m "feat: add message schema with Pydantic models"
```

---

### Task 3: State machine (channels, options, stack)

**Files:**
- Create: `conductor/state_machine.py`
- Create: `tests/test_state_machine.py`

#### Steps

- [ ] **Step 1: Write tests for state machine**

Create `tests/test_state_machine.py`:

```python
"""Test state machine: channels, options, stack."""

import json
from pathlib import Path
import pytest
from conductor.state_machine import (
    Channel,
    ChannelRegistry,
    StateSnapshot,
)


@pytest.fixture
def word_blocks_path():
    """Path to word_blocks.json."""
    return Path(__file__).parent.parent / "shared" / "data" / "word_blocks.json"


def test_channel_registry_loads_from_json(word_blocks_path):
    """ChannelRegistry loads channels from word_blocks.json."""
    registry = ChannelRegistry(word_blocks_path)
    assert "subject" in registry.channels
    assert "context" in registry.channels
    assert "style" in registry.channels
    assert "engine" in registry.channels


def test_channel_has_options(word_blocks_path):
    """Channel loads options from theme."""
    registry = ChannelRegistry(word_blocks_path)
    subject_ch = registry.channels["subject"]
    # Default theme is "cinematic_noir"
    assert len(subject_ch.options) > 0
    assert "Private Eye" in subject_ch.options or "Detective" in subject_ch.options


def test_channel_next_cycles_forward(word_blocks_path):
    """Calling next_option increments index."""
    registry = ChannelRegistry(word_blocks_path)
    ch = registry.channels["subject"]
    initial_idx = ch.option_index
    ch.next_option()
    assert ch.option_index == (initial_idx + 1) % len(ch.options)


def test_channel_prev_cycles_backward(word_blocks_path):
    """Calling prev_option decrements index."""
    registry = ChannelRegistry(word_blocks_path)
    ch = registry.channels["subject"]
    initial_idx = ch.option_index
    ch.prev_option()
    assert ch.option_index == (initial_idx - 1) % len(ch.options)


def test_channel_commit_toggles_committed(word_blocks_path):
    """Commit toggles the committed flag."""
    registry = ChannelRegistry(word_blocks_path)
    ch = registry.channels["subject"]
    ch.committed = False
    ch.commit()
    assert ch.committed is True


def test_state_snapshot_serializes(word_blocks_path):
    """StateSnapshot can be serialized to dict for JSON."""
    registry = ChannelRegistry(word_blocks_path)
    snapshot = StateSnapshot.from_registry(registry, mode="word")
    as_dict = snapshot.to_dict()
    assert "channel" in as_dict
    assert "option_index" in as_dict
    assert "candidate" in as_dict


def test_render_sentence(word_blocks_path):
    """Render sentence from committed options."""
    registry = ChannelRegistry(word_blocks_path)
    # Commit one of each word channel
    registry.channels["subject"].commit()
    registry.channels["context"].commit()
    registry.channels["style"].commit()

    sentence = registry.render_sentence()
    # Should be "Subject, Context, Style"
    parts = sentence.split(" · ")
    assert len(parts) == 3


def test_change_channel(word_blocks_path):
    """Changing active channel updates registry."""
    registry = ChannelRegistry(word_blocks_path)
    registry.set_active_channel("context")
    assert registry.active_channel == "context"


def test_engine_channel_holds_loop_settings(word_blocks_path):
    """Engine channel has loop, speed, operator settings."""
    registry = ChannelRegistry(word_blocks_path)
    engine_ch = registry.channels["engine"]
    assert hasattr(engine_ch, "loop")
    assert hasattr(engine_ch, "speed_s")
    assert hasattr(engine_ch, "operator")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_state_machine.py -v
```

Expected: `ModuleNotFoundError: No module named 'conductor.state_machine'`

- [ ] **Step 3: Write state_machine.py**

Create `conductor/state_machine.py`:

```python
"""State machine: channels, options, stack."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple


CHANNEL_COLORS = {
    "subject": (0, 200, 80),    # green
    "context": (0, 100, 200),   # blue
    "style": (200, 0, 150),     # magenta
    "engine": (200, 150, 0),    # amber
}


@dataclass
class Channel:
    """A single editable channel (Subject, Context, Style, or Engine)."""

    id: str
    options: List[str]
    option_index: int = 0
    committed: bool = False
    color: Tuple[int, int, int] = field(default_factory=lambda: (255, 255, 255))

    # Engine-specific
    loop: bool = False
    speed_s: int = 8
    operator: str = "swap"
    queue_depth: int = 0

    def next_option(self) -> None:
        """Cycle to next option."""
        if self.options:
            self.option_index = (self.option_index + 1) % len(self.options)

    def prev_option(self) -> None:
        """Cycle to previous option."""
        if self.options:
            self.option_index = (self.option_index - 1) % len(self.options)

    def commit(self) -> None:
        """Toggle committed flag."""
        self.committed = not self.committed

    def get_candidate(self) -> str:
        """Get current option text."""
        if self.options:
            return self.options[self.option_index]
        return ""

    def get_option_count(self) -> int:
        """Count of options in this channel."""
        return len(self.options)


@dataclass
class StateSnapshot:
    """Snapshot of state to send to Controller."""

    channel: str
    channel_color: Tuple[int, int, int]
    option_index: int
    option_count: int
    candidate: str
    committed: bool
    mode: str
    engine: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for JSON."""
        return {
            "type": "state",
            "channel": self.channel,
            "channel_color": self.channel_color,
            "option_index": self.option_index,
            "option_count": self.option_count,
            "candidate": self.candidate,
            "committed": self.committed,
            "mode": self.mode,
            "engine": self.engine,
        }

    @staticmethod
    def from_registry(registry: "ChannelRegistry", mode: str) -> "StateSnapshot":
        """Build snapshot from registry state."""
        active_ch = registry.active_channel
        ch = registry.channels[active_ch]

        engine_dict = None
        if active_ch == "engine":
            engine_dict = {
                "loop": ch.loop,
                "speed_s": ch.speed_s,
                "operator": ch.operator,
                "queue_depth": ch.queue_depth,
            }

        return StateSnapshot(
            channel=active_ch,
            channel_color=ch.color,
            option_index=ch.option_index,
            option_count=ch.get_option_count(),
            candidate=ch.get_candidate(),
            committed=ch.committed,
            mode=mode,
            engine=engine_dict,
        )


class ChannelRegistry:
    """Registry of all channels, loads from word_blocks.json."""

    def __init__(self, word_blocks_path: Path):
        """Load channels from word_blocks.json."""
        self.word_blocks_path = word_blocks_path
        self.channels: Dict[str, Channel] = {}
        self.active_channel = "subject"
        self._load_word_blocks()

    def _load_word_blocks(self) -> None:
        """Load channels from word_blocks.json."""
        with open(self.word_blocks_path, "r") as f:
            data = json.load(f)

        # Default theme
        theme = "cinematic_noir"
        theme_data = data["theme_specific"].get(theme, {})

        # Load word channels
        for channel_id in ["subject", "context", "style"]:
            options = theme_data.get(channel_id.title(), [])
            self.channels[channel_id] = Channel(
                id=channel_id,
                options=options,
                color=CHANNEL_COLORS.get(channel_id, (255, 255, 255)),
            )

        # Engine channel (not from word_blocks, synthetic)
        self.channels["engine"] = Channel(
            id="engine",
            options=[],  # No options; engine uses settings
            color=CHANNEL_COLORS.get("engine", (255, 255, 255)),
        )

    def set_active_channel(self, channel_id: str) -> None:
        """Change active channel."""
        if channel_id in self.channels:
            self.active_channel = channel_id

    def button_next(self) -> None:
        """Handle 'next' button on active channel."""
        self.channels[self.active_channel].next_option()

    def button_prev(self) -> None:
        """Handle 'prev' button on active channel."""
        self.channels[self.active_channel].prev_option()

    def button_commit(self) -> None:
        """Handle 'commit' button on active channel."""
        ch = self.channels[self.active_channel]
        if self.active_channel != "engine":
            ch.commit()

    def button_shift(self) -> None:
        """Handle 'shift/alt' button. For now, cycle engine operator."""
        if self.active_channel == "engine":
            operators = ["swap", "lang", "ltr", "+con", "-con"]
            current_idx = operators.index(self.channels["engine"].operator)
            self.channels["engine"].operator = operators[(current_idx + 1) % len(operators)]

    def render_sentence(self) -> str:
        """Assemble committed options into a sentence."""
        parts = []
        for ch_id in ["subject", "context", "style"]:
            ch = self.channels[ch_id]
            if ch.committed and ch.get_candidate():
                parts.append(ch.get_candidate())
        return " · ".join(parts) if parts else "[empty]"
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_state_machine.py -v
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add conductor/state_machine.py tests/test_state_machine.py
git commit -m "feat: implement state machine with channels, options, stack"
```

---

### Task 4: WebSocket Bus implementation

**Files:**
- Create: `shared/bus_websocket.py` (WebSocket transport)
- Create: `tests/test_bus_integration.py`

#### Steps

- [ ] **Step 1: Write integration test for WebSocket round-trip**

Create `tests/test_bus_integration.py`:

```python
"""Test Bus implementation with WebSocket."""

import asyncio
import json
import pytest
from shared.bus_websocket import WebSocketServer, WebSocketClient
from shared.messages import HelloMessage, StateMessage, ButtonMessage


@pytest.mark.asyncio
async def test_websocket_server_client_hello():
    """Client sends hello, server receives it."""
    server = WebSocketServer()
    client = WebSocketClient()

    received_messages = []

    def on_hello(msg):
        received_messages.append(msg)

    server.on("hello", on_hello)

    # Start server
    await asyncio.gather(
        server.start("localhost", 8765),
        run_client_hello(client, received_messages),
        return_exceptions=True,
    )


async def run_client_hello(client, received):
    """Helper: connect client and send hello."""
    await asyncio.sleep(0.1)  # Let server start
    await client.connect("localhost", 8765)

    hello = HelloMessage(device="spark", fw="0.1.0")
    await client.send(hello.model_dump())

    await asyncio.sleep(0.2)  # Let server receive
    await client.disconnect()

    # Server should have received it
    assert len(received) > 0
    assert received[0]["device"] == "spark"


@pytest.mark.asyncio
async def test_websocket_server_sends_state():
    """Server can send state to client."""
    server = WebSocketServer()
    client = WebSocketClient()

    received_messages = []

    def on_state(msg):
        received_messages.append(msg)

    client.on("state", on_state)

    async def send_state_after_connect():
        await asyncio.sleep(0.2)
        state = StateMessage(
            channel="subject",
            channel_color=(0, 200, 80),
            option_index=1,
            option_count=5,
            candidate="Detective",
            committed=True,
            mode="word",
        )
        await server.send(state.model_dump())

    await asyncio.gather(
        server.start("localhost", 8765),
        client.connect("localhost", 8765),
        send_state_after_connect(),
        return_exceptions=True,
    )

    # Client should have received state
    await asyncio.sleep(0.2)
    assert len(received_messages) > 0
    assert received_messages[0]["candidate"] == "Detective"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_bus_integration.py -v
```

Expected: `ModuleNotFoundError: No module named 'shared.bus_websocket'`

- [ ] **Step 3: Write WebSocket Bus implementation**

Create `shared/bus_websocket.py`:

```python
"""WebSocket transport for Bus."""

import asyncio
import json
import logging
from typing import Any, Callable, Dict, Optional, Set
import websockets
from websockets.server import WebSocketServerProtocol

from shared.interfaces.bus import BusServer, BusClient
from shared.messages import message_from_dict

logger = logging.getLogger(__name__)


class WebSocketServer(BusServer):
    """WebSocket server (Conductor side)."""

    def __init__(self):
        self.handlers: Dict[str, Callable] = {}
        self.clients: Set[WebSocketServerProtocol] = set()
        self.server = None

    def on(self, msg_type: str, handler: Callable[[Dict[str, Any]], None]) -> None:
        """Register handler for message type."""
        self.handlers[msg_type] = handler

    async def send(self, msg: Dict[str, Any]) -> None:
        """Broadcast message to all connected clients."""
        if not self.clients:
            return
        msg_json = json.dumps(msg)
        # Send to all clients
        await asyncio.gather(
            *[client.send(msg_json) for client in self.clients],
            return_exceptions=True,
        )

    async def connect(self) -> None:
        """No-op for server."""
        pass

    async def disconnect(self) -> None:
        """Shut down server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()

    async def start(self, host: str, port: int) -> None:
        """Start WebSocket server."""
        async def handle_client(websocket: WebSocketServerProtocol, path: str):
            self.clients.add(websocket)
            logger.info(f"Client connected: {websocket.remote_address}")
            try:
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        msg_type = data.get("type")
                        if msg_type in self.handlers:
                            self.handlers[msg_type](data)
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON decode error: {e}")
            except websockets.exceptions.ConnectionClosed:
                logger.info(f"Client disconnected: {websocket.remote_address}")
            finally:
                self.clients.discard(websocket)

        self.server = await websockets.serve(
            handle_client, host, port, ping_interval=2, ping_timeout=1
        )
        logger.info(f"WebSocket server listening on ws://{host}:{port}")
        await self.server.wait_closed()


class WebSocketClient(BusClient):
    """WebSocket client (Controller side)."""

    def __init__(self):
        self.handlers: Dict[str, Callable] = {}
        self.websocket: Optional[WebSocketServerProtocol] = None
        self.running = False

    def on(self, msg_type: str, handler: Callable[[Dict[str, Any]], None]) -> None:
        """Register handler for message type."""
        self.handlers[msg_type] = handler

    async def send(self, msg: Dict[str, Any]) -> None:
        """Send message to server."""
        if self.websocket:
            msg_json = json.dumps(msg)
            await self.websocket.send(msg_json)

    async def connect(self, host: str, port: int) -> None:
        """Connect to WebSocket server."""
        try:
            self.websocket = await websockets.connect(f"ws://{host}:{port}")
            self.running = True
            logger.info(f"Connected to ws://{host}:{port}")

            # Listen for messages
            asyncio.create_task(self._listen())
        except Exception as e:
            logger.error(f"Connection failed: {e}")

    async def disconnect(self) -> None:
        """Disconnect from server."""
        self.running = False
        if self.websocket:
            await self.websocket.close()

    async def _listen(self) -> None:
        """Listen for messages from server."""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    msg_type = data.get("type")
                    if msg_type in self.handlers:
                        self.handlers[msg_type](data)
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error: {e}")
        except websockets.exceptions.ConnectionClosed:
            logger.info("Server disconnected")
            self.running = False
        except Exception as e:
            logger.error(f"Listen error: {e}")
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_bus_integration.py -v -s
```

Expected: Tests PASS (or timeout if async timing is tricky; adjust sleep times as needed).

- [ ] **Step 5: Commit**

```bash
git add shared/bus_websocket.py tests/test_bus_integration.py
git commit -m "feat: implement WebSocket Bus with server/client"
```

---

### Task 5: Spark mock display (17×7 ANSI terminal)

**Files:**
- Create: `controller/display.py`
- Create: `tests/test_display_mocks.py`

#### Steps

- [ ] **Step 1: Write test for SparkMock rendering**

Create `tests/test_display_mocks.py`:

```python
"""Test display mocks."""

from shared.interfaces.display import StateSnapshot, Display
from controller.display import SparkMock


def test_spark_mock_renders_without_crash():
    """SparkMock renders state snapshot to terminal."""
    state = StateSnapshot(
        channel="subject",
        channel_color=(0, 200, 80),
        option_index=2,
        option_count=5,
        candidate="Detective",
        committed=True,
        mode="word",
    )

    mock = SparkMock()
    # Should not crash
    mock.render(state)
    mock.close()


def test_spark_mock_renders_engine_channel():
    """SparkMock renders engine settings."""
    state = StateSnapshot(
        channel="engine",
        channel_color=(200, 150, 0),
        option_index=0,
        option_count=1,
        candidate="LOOP",
        committed=False,
        mode="engine",
        engine={"loop": True, "speed_s": 8, "operator": "swap", "queue_depth": 0},
    )

    mock = SparkMock()
    mock.render(state)
    mock.close()


def test_spark_mock_scrolls_long_text():
    """SparkMock scrolls text longer than 17 chars."""
    state = StateSnapshot(
        channel="subject",
        channel_color=(0, 200, 80),
        option_index=0,
        option_count=1,
        candidate="A Very Long Detective Name That Should Scroll",
        committed=False,
        mode="word",
    )

    mock = SparkMock()
    # Render multiple times to show scrolling
    for i in range(5):
        mock.render(state)
    mock.close()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_display_mocks.py::test_spark_mock_renders_without_crash -v
```

Expected: `ModuleNotFoundError: No module named 'controller.display'`

- [ ] **Step 3: Write SparkMock display**

Create `controller/display.py`:

```python
"""Spark display: real Unicorn HAT Mini + mock (ANSI terminal 17×7)."""

import os
import sys
from dataclasses import dataclass
from typing import Optional
import platform

from shared.interfaces.display import Display, StateSnapshot

IS_SIMULATION = platform.system() != "Linux"

# ANSI colour codes
ANSI_BLACK = "\033[40m"
ANSI_RED = "\033[41m"
ANSI_GREEN = "\033[42m"
ANSI_YELLOW = "\033[43m"
ANSI_BLUE = "\033[44m"
ANSI_MAGENTA = "\033[45m"
ANSI_CYAN = "\033[46m"
ANSI_WHITE = "\033[47m"
ANSI_RESET = "\033[0m"
ANSI_BRIGHT = "\033[1m"

# Map RGB to ANSI colour (naive)
def rgb_to_ansi(rgb: tuple) -> str:
    """Convert (r, g, b) to closest ANSI colour."""
    r, g, b = rgb
    if r > 100 and g > 100 and b > 100:
        return ANSI_WHITE
    elif r > 150 and g < 100 and b < 100:
        return ANSI_RED
    elif g > 150 and r < 100 and b < 100:
        return ANSI_GREEN
    elif b > 150 and r < 100 and g < 100:
        return ANSI_BLUE
    elif r > 150 and g > 100 and b < 100:
        return ANSI_YELLOW
    elif r > 150 and b > 100 and g < 100:
        return ANSI_MAGENTA
    elif g > 100 and b > 100 and r < 100:
        return ANSI_CYAN
    else:
        return ANSI_BLACK


@dataclass
class SparkMock(Display):
    """Mock Spark display: renders 17×7 ANSI matrix to terminal."""

    width: int = 17
    height: int = 7
    scroll_pos: int = 0  # For scrolling text

    def render(self, state: StateSnapshot) -> None:
        """Render state to terminal."""
        # Build 17×7 matrix
        matrix = [[" " for _ in range(self.width)] for _ in range(self.height)]

        color = rgb_to_ansi(state.channel_color)

        # Row 0: colour bar (full width, dim)
        for x in range(self.width):
            matrix[0][x] = "▄"  # Half-block

        # Row 1: position pips
        pip_char = "●"  # Bright dot at current index
        dim_pip = "○"   # Dim dots for others
        if state.option_count > 0:
            for i in range(min(state.option_count, self.width)):
                matrix[1][i] = pip_char if i == state.option_index else dim_pip

        # Rows 2–6: text (two-line layout: rows 2–4, gap, rows 6)
        # For now: rows 2–4 = line 1, row 5 = spacer, row 6 = line 2
        text_to_render = state.candidate

        if state.mode == "engine":
            # Engine channel: show operator icon + setting
            text_line_1 = f"[{state.engine['operator'].upper()}]"
            text_line_2 = f"Speed: {state.engine['speed_s']}s"
        else:
            # Word channel: scroll text
            # Simple scrolling: use scroll_pos to advance
            text_with_padding = text_to_render + "  " + text_to_render
            text_line_1 = text_with_padding[self.scroll_pos:self.scroll_pos + 17]
            text_line_2 = ""  # Second line can be empty or show more info
            self.scroll_pos = (self.scroll_pos + 1) % len(text_with_padding)

        # Render lines to matrix
        # Line 1: rows 2–4 (but fit into a 3-row height)
        for i, ch in enumerate(text_line_1[:17]):
            matrix[2][i] = ch

        # Line 2: row 6
        if text_line_2:
            for i, ch in enumerate(text_line_2[:17]):
                matrix[6][i] = ch

        # Render to terminal
        os.system("clear" if os.name == "posix" else "cls")
        print(f"\n{color}Spark 17×7 Mock — Channel: {state.channel.upper()}{ANSI_RESET}\n")

        # Print matrix
        for row in matrix:
            row_str = "".join(row)
            print(f"  {color}█{ANSI_RESET} {row_str} {color}█{ANSI_RESET}")

        print()

    def close(self) -> None:
        """Clean up."""
        pass


class SparkDisplay(Display):
    """Real Spark display (Unicorn HAT Mini on GPIO)."""

    def render(self, state: StateSnapshot) -> None:
        """Render to Unicorn HAT Mini (stub for M1)."""
        if IS_SIMULATION:
            # Fall back to mock
            mock = SparkMock()
            mock.render(state)
        else:
            # TODO: implement real Unicorn HAT rendering
            pass

    def close(self) -> None:
        """Clean up GPIO."""
        pass
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_display_mocks.py -v -s
```

Expected: All tests PASS (will print ANSI matrices to terminal).

- [ ] **Step 5: Commit**

```bash
git add controller/display.py tests/test_display_mocks.py
git commit -m "feat: implement SparkMock ANSI terminal 17×7 display"
```

---

### Task 6: Slate mock display (InkyMock PIL image)

**Files:**
- Modify: `conductor/display.py` (new file, InkyMock)
- Modify: `tests/test_display_mocks.py` (add InkyMock test)

#### Steps

- [ ] **Step 1: Add InkyMock test**

Edit `tests/test_display_mocks.py`, add:

```python
from conductor.display import InkyMock
from PIL import Image


def test_inky_mock_renders_without_crash():
    """InkyMock renders state snapshot to PIL image."""
    state = StateSnapshot(
        channel="subject",
        channel_color=(0, 200, 80),
        option_index=2,
        option_count=5,
        candidate="Detective",
        committed=True,
        mode="word",
    )

    mock = InkyMock(width=640, height=400)
    mock.render(state)
    # InkyMock generates a PIL image; just verify no crash
    mock.close()


def test_inky_mock_renders_sentence():
    """InkyMock includes sentence ribbon."""
    state = StateSnapshot(
        channel="subject",
        channel_color=(0, 200, 80),
        option_index=1,
        option_count=3,
        candidate="Detective",
        committed=True,
        mode="word",
    )

    mock = InkyMock(width=640, height=400)
    mock.render(state)
    # Verify image was created
    assert mock.image is not None
    mock.close()
```

- [ ] **Step 2: Write InkyMock display**

Create `conductor/display.py`:

```python
"""Slate display: real Inky Impression + mock (PIL image)."""

import os
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path
import platform

from PIL import Image, ImageDraw, ImageFont

from shared.interfaces.display import Display, StateSnapshot

IS_SIMULATION = platform.system() != "Linux"


@dataclass
class InkyMock(Display):
    """Mock Slate display: renders to PIL image."""

    width: int = 640
    height: int = 400
    image: Optional[Image.Image] = field(default=None, init=False)

    def render(self, state: StateSnapshot) -> None:
        """Render state to PIL image."""
        # Create new image (white background)
        self.image = Image.new("RGB", (self.width, self.height), (255, 255, 255))
        draw = ImageDraw.Draw(self.image)

        # Try to load a font; fall back to default
        try:
            font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 12)
            font_large = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
        except:
            font_small = ImageFont.load_default()
            font_large = ImageFont.load_default()

        # Left menu strip: channel labels (sideways)
        menu_width = 80
        channels = [
            ("A", "Subject", (0, 200, 80)),
            ("B", "Context", (0, 100, 200)),
            ("C", "Style", (200, 0, 150)),
            ("D", "Engine", (200, 150, 0)),
        ]

        channel_height = self.height // 4
        for i, (btn, label, color) in enumerate(channels):
            y = i * channel_height
            is_active = (state.channel == label.lower())

            if is_active:
                # Highlight active channel
                draw.rectangle((0, y, menu_width, y + channel_height), fill=color)
                draw.text((10, y + 10), f"[{btn}]", fill=(255, 255, 255), font=font_small)
                draw.text((10, y + 30), label, fill=(255, 255, 255), font=font_small)
            else:
                # Inactive
                draw.rectangle((0, y, menu_width, y + channel_height), outline=color)
                draw.text((10, y + 10), f"{btn}", fill=color, font=font_small)
                draw.text((10, y + 30), label, fill=color, font=font_small)

        # Main area: placeholder for generated image
        main_x = menu_width + 10
        main_y = 10
        main_width = self.width - main_x - 10
        main_height = self.height - main_y - 60

        # Draw placeholder rectangle
        draw.rectangle(
            (main_x, main_y, main_x + main_width, main_y + main_height),
            outline=(0, 0, 0),
        )
        draw.text(
            (main_x + 10, main_y + 10),
            "Generated Image",
            fill=(0, 0, 0),
            font=font_large,
        )
        draw.text(
            (main_x + 10, main_y + 50),
            f"Candidate: {state.candidate}",
            fill=(0, 0, 0),
            font=font_small,
        )

        # Bottom ribbon: sentence + queue + loop status
        ribbon_y = self.height - 50
        sentence = state.candidate  # In real impl, would be full sentence
        draw.text(
            (main_x + 10, ribbon_y),
            f"Sentence: {sentence}",
            fill=(0, 0, 0),
            font=font_small,
        )

        if state.engine:
            engine_str = f"Loop: {'ON' if state.engine.get('loop') else 'OFF'} | Op: {state.engine.get('operator', 'swap')} | Speed: {state.engine.get('speed_s', 8)}s"
            draw.text(
                (main_x + 10, ribbon_y + 25),
                engine_str,
                fill=(0, 0, 0),
                font=font_small,
            )

        # Display image
        if IS_SIMULATION:
            self.image.show()

    def close(self) -> None:
        """Clean up."""
        pass


class SlateDisplay(Display):
    """Real Slate display (Inky Impression on e-paper)."""

    def render(self, state: StateSnapshot) -> None:
        """Render to Inky Impression (stub for M1)."""
        if IS_SIMULATION:
            # Fall back to mock
            mock = InkyMock()
            mock.render(state)
        else:
            # TODO: implement real Inky rendering
            pass

    def close(self) -> None:
        """Clean up e-paper."""
        pass
```

- [ ] **Step 3: Run tests to verify they pass**

```bash
pytest tests/test_display_mocks.py -v
```

Expected: All tests PASS (InkyMock will display PIL images).

- [ ] **Step 4: Commit**

```bash
git add conductor/display.py tests/test_display_mocks.py
git commit -m "feat: implement InkyMock PIL image display with menu strip + ribbon"
```

---

### Task 7: Keyboard button listener (sim)

**Files:**
- Create: `controller/buttons.py` (keyboard listener)
- Create: `tests/test_buttons.py`

#### Steps

- [ ] **Step 1: Write test for keyboard listener**

Create `tests/test_buttons.py`:

```python
"""Test button listeners."""

from controller.buttons import KeyboardListener


def test_keyboard_listener_initializes():
    """KeyboardListener can be created."""
    listener = KeyboardListener(device="spark")
    assert listener.device == "spark"


def test_keyboard_listener_registers_handler():
    """Can register button handler."""
    listener = KeyboardListener(device="spark")

    received = []

    def on_button(btn, event):
        received.append((btn, event))

    listener.on(on_button)
    # Handler registered; would need actual keyboard input to test
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_buttons.py -v
```

Expected: `ModuleNotFoundError: No module named 'controller.buttons'`

- [ ] **Step 3: Write keyboard listener**

Create `controller/buttons.py`:

```python
"""Button listeners: GPIO (real) + keyboard sim."""

import sys
import threading
from abc import ABC, abstractmethod
from typing import Callable, Optional
import platform

IS_SIMULATION = platform.system() != "Linux"


class ButtonListener(ABC):
    """Abstract button listener."""

    @abstractmethod
    def on(self, handler: Callable[[str, str], None]) -> None:
        """Register button handler: (btn: str, event: str) -> None."""
        pass

    @abstractmethod
    def start(self) -> None:
        """Start listening."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stop listening."""
        pass


class KeyboardListener(ButtonListener):
    """Keyboard-based button listener (sim only)."""

    def __init__(self, device: str = "spark"):
        """Initialize. device: 'spark' (a/b/x/y) or 'slate' (a/b/c/d)."""
        self.device = device
        self.handler: Optional[Callable] = None
        self.running = False
        self.thread: Optional[threading.Thread] = None

        # Map keyboard keys to buttons
        if device == "spark":
            self.key_map = {"a": "A", "b": "B", "x": "X", "y": "Y"}
        elif device == "slate":
            self.key_map = {"a": "A", "b": "B", "c": "C", "d": "D"}
        else:
            self.key_map = {}

    def on(self, handler: Callable[[str, str], None]) -> None:
        """Register handler."""
        self.handler = handler

    def start(self) -> None:
        """Start listening to keyboard."""
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        """Stop listening."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)

    def _listen_loop(self) -> None:
        """Listen for keyboard input."""
        print(f"KeyboardListener ({self.device}) ready. Press keys: {list(self.key_map.keys())}")

        while self.running:
            try:
                # Read one character (non-blocking is tricky in Python; this is blocking)
                char = sys.stdin.read(1).lower()

                if char in self.key_map:
                    btn = self.key_map[char]
                    if self.handler:
                        self.handler(btn, "press")

                if char == "q":
                    self.running = False
            except Exception as e:
                print(f"Keyboard error: {e}")
                break


class GPIOListener(ButtonListener):
    """GPIO-based button listener (real hardware)."""

    def __init__(self, device: str, pins: dict):
        """Initialize. pins: {"A": 5, "B": 6, "X": 16, "Y": 24}."""
        self.device = device
        self.pins = pins
        self.handler: Optional[Callable] = None
        self.running = False

    def on(self, handler: Callable[[str, str], None]) -> None:
        """Register handler."""
        self.handler = handler

    def start(self) -> None:
        """Start listening on GPIO (stub for M1)."""
        self.running = True
        # TODO: set up gpiozero / gpiod listeners

    def stop(self) -> None:
        """Stop listening."""
        self.running = False
        # TODO: cleanup GPIO
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_buttons.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add controller/buttons.py tests/test_buttons.py
git commit -m "feat: add KeyboardListener for sim, GPIOListener stub for hardware"
```

---

### Task 8: Conductor server + wired state + button handlers

**Files:**
- Create: `conductor/__main__.py` (entry point)
- Modify: `conductor/conductor.py` (main loop)

#### Steps

- [ ] **Step 1: Write Conductor main loop**

Create `conductor/__main__.py`:

```python
"""Conductor (Slate) entry point."""

import asyncio
import logging
import sys
from pathlib import Path

from conductor.conductor import Conductor
from shared.config import get_word_blocks_path, IS_SIMULATION

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Run Conductor server."""
    word_blocks_path = get_word_blocks_path()

    if not word_blocks_path.exists():
        logger.error(f"word_blocks.json not found at {word_blocks_path}")
        sys.exit(1)

    conductor = Conductor(word_blocks_path)

    try:
        logger.info("Starting Conductor server...")
        await conductor.start("localhost", 8765)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        await conductor.shutdown()


if __name__ == "__main__":
    if IS_SIMULATION:
        logger.info("Running in SIMULATION mode")
    asyncio.run(main())
```

- [ ] **Step 2: Write Conductor class**

Create `conductor/conductor.py`:

```python
"""Conductor (Slate authority): state machine + server."""

import asyncio
import logging
from pathlib import Path
from typing import Optional

from conductor.state_machine import ChannelRegistry, StateSnapshot
from conductor.display import InkyMock, SlateDisplay
from shared.bus_websocket import WebSocketServer
from shared.messages import ButtonMessage, StateMessage
from shared.config import IS_SIMULATION

logger = logging.getLogger(__name__)


class Conductor:
    """State authority; runs on Slate."""

    def __init__(self, word_blocks_path: Path):
        """Initialize Conductor."""
        self.registry = ChannelRegistry(word_blocks_path)
        self.bus = WebSocketServer()
        self.display = InkyMock() if IS_SIMULATION else SlateDisplay()

        # Register message handlers
        self.bus.on("hello", self._on_hello)
        self.bus.on("button", self._on_button)
        self.bus.on("ping", self._on_ping)

    async def start(self, host: str, port: int) -> None:
        """Start WebSocket server and display."""
        await self.bus.start(host, port)

    async def shutdown(self) -> None:
        """Shut down server."""
        await self.bus.disconnect()
        self.display.close()

    def _on_hello(self, msg: dict) -> None:
        """Handle hello from Controller."""
        logger.info(f"Controller connected: {msg.get('device')} fw {msg.get('fw')}")
        # Send current state snapshot
        self._broadcast_state()

    def _on_button(self, msg: dict) -> None:
        """Handle button event from Controller."""
        btn = msg.get("btn")
        event = msg.get("event")
        logger.info(f"Button: {btn} {event}")

        # Interpret button
        if event == "press":
            if btn == "A":
                self.registry.button_prev()
            elif btn == "B":
                self.registry.button_next()
            elif btn == "X":
                self.registry.button_commit()
            elif btn == "Y":
                self.registry.button_shift()
            elif btn == "C":  # Slate button (switch channel)
                # For M1, just log; M2 will handle SEND
                pass

        # Broadcast updated state
        self._broadcast_state()

    def _on_ping(self, msg: dict) -> None:
        """Handle ping from Controller."""
        from shared.messages import PongMessage
        pong = PongMessage()
        asyncio.create_task(self.bus.send(pong.model_dump()))

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
        asyncio.create_task(self.bus.send(msg.model_dump()))

        # Also render to Slate display
        self.display.render(snapshot)
```

- [ ] **Step 3: Test Conductor startup**

```bash
python -m conductor &
# Wait a moment, then Ctrl+C to stop
```

Expected: Server starts, logs "WebSocket server listening on ws://localhost:8765"

- [ ] **Step 4: Commit**

```bash
git add conductor/__main__.py conductor/conductor.py
git commit -m "feat: implement Conductor server with state authority + button handlers"
```

---

### Task 9: Controller client + keyboard polling + render loop

**Files:**
- Create: `controller/__main__.py` (entry point)
- Modify: `controller/controller.py` (main loop)

#### Steps

- [ ] **Step 1: Write Controller main loop**

Create `controller/__main__.py`:

```python
"""Controller (Spark) entry point."""

import asyncio
import logging
import sys

from controller.controller import Controller
from shared.config import get_conductor_host, get_conductor_port, IS_SIMULATION

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Run Controller client."""
    host = get_conductor_host()
    port = get_conductor_port()

    controller = Controller()

    try:
        logger.info(f"Connecting to Conductor at {host}:{port}...")
        await controller.connect(host, port)

        # Keep running
        while controller.running:
            await asyncio.sleep(0.1)

    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await controller.shutdown()


if __name__ == "__main__":
    if IS_SIMULATION:
        logger.info("Running in SIMULATION mode")
    asyncio.run(main())
```

- [ ] **Step 2: Write Controller class**

Create `controller/controller.py`:

```python
"""Controller (Spark client): LED UI + button listener."""

import asyncio
import logging
from typing import Optional

from controller.display import SparkMock, SparkDisplay
from controller.buttons import KeyboardListener, ButtonListener
from shared.bus_websocket import WebSocketClient
from shared.messages import HelloMessage, StateMessage, PingMessage
from shared.interfaces.display import StateSnapshot
from shared.config import IS_SIMULATION

logger = logging.getLogger(__name__)


class Controller:
    """UI client; runs on Spark."""

    def __init__(self):
        """Initialize Controller."""
        self.bus = WebSocketClient()
        self.display = SparkMock() if IS_SIMULATION else SparkDisplay()
        self.buttons: Optional[ButtonListener] = None
        self.running = False
        self.current_state: Optional[StateSnapshot] = None

        # Register bus handlers
        self.bus.on("state", self._on_state)
        self.bus.on("patch", self._on_patch)
        self.bus.on("pong", self._on_pong)
        self.bus.on("toast", self._on_toast)

    async def connect(self, host: str, port: int) -> None:
        """Connect to Conductor and start listening."""
        await self.bus.connect(host, port)
        self.running = True

        # Send hello
        hello = HelloMessage(device="spark", fw="0.1.0")
        await self.bus.send(hello.model_dump())

        # Start button listener
        self.buttons = KeyboardListener(device="spark")
        self.buttons.on(self._on_button_event)
        self.buttons.start()

        # Start heartbeat task
        asyncio.create_task(self._heartbeat_loop())

    async def shutdown(self) -> None:
        """Shut down client."""
        self.running = False
        if self.buttons:
            self.buttons.stop()
        await self.bus.disconnect()
        self.display.close()

    def _on_state(self, msg: dict) -> None:
        """Handle state update from Conductor."""
        state = StateSnapshot(
            channel=msg["channel"],
            channel_color=tuple(msg["channel_color"]),
            option_index=msg["option_index"],
            option_count=msg["option_count"],
            candidate=msg["candidate"],
            committed=msg["committed"],
            mode=msg["mode"],
            engine=msg.get("engine"),
        )
        self.current_state = state
        self.display.render(state)

    def _on_patch(self, msg: dict) -> None:
        """Handle incremental state update."""
        if not self.current_state:
            return

        if "candidate" in msg:
            self.current_state.candidate = msg["candidate"]
        if "option_index" in msg:
            self.current_state.option_index = msg["option_index"]
        if "committed" in msg:
            self.current_state.committed = msg["committed"]

        self.display.render(self.current_state)

    def _on_pong(self, msg: dict) -> None:
        """Handle pong from Conductor."""
        logger.debug("Pong received")

    def _on_toast(self, msg: dict) -> None:
        """Handle toast message (brief flash)."""
        logger.info(f"Toast: {msg.get('text')}")
        # Could flash LED here

    def _on_button_event(self, btn: str, event: str) -> None:
        """Handle button press from keyboard."""
        logger.info(f"Button event: {btn} {event}")

        # Send to Conductor
        from shared.messages import ButtonMessage
        button_msg = ButtonMessage(btn=btn, event=event)
        asyncio.create_task(self.bus.send(button_msg.model_dump()))

    async def _heartbeat_loop(self) -> None:
        """Send periodic ping to Conductor."""
        while self.running:
            await asyncio.sleep(2)
            ping = PingMessage()
            await self.bus.send(ping.model_dump())
```

- [ ] **Step 3: Test Controller + Conductor together**

Terminal 1 (Conductor):
```bash
python -m conductor
```

Terminal 2 (Controller):
```bash
python -m controller
```

Expected: Controller connects, shows "Spark 17×7 Mock" in terminal, press `a/b/x/y` to send button events to Conductor.

- [ ] **Step 4: Commit**

```bash
git add controller/__main__.py controller/controller.py
git commit -m "feat: implement Controller client with keyboard polling + render loop"
```

---

### Task 10: Handle Slate (Conductor) button events

**Files:**
- Modify: `conductor/conductor.py`

#### Steps

- [ ] **Step 1: Add Slate button listener to Conductor**

Edit `conductor/conductor.py`, modify `__init__`:

```python
def __init__(self, word_blocks_path: Path):
    """Initialize Conductor."""
    self.registry = ChannelRegistry(word_blocks_path)
    self.bus = WebSocketServer()
    self.display = InkyMock() if IS_SIMULATION else SlateDisplay()

    # Slate button listener (sim)
    self.buttons: Optional[ButtonListener] = None
    if IS_SIMULATION:
        from conductor.buttons import KeyboardListener
        self.buttons = KeyboardListener(device="slate")
        self.buttons.on(self._on_slate_button)

    # Register message handlers
    self.bus.on("hello", self._on_hello)
    self.bus.on("button", self._on_button)
    self.bus.on("ping", self._on_ping)
```

- [ ] **Step 2: Add Slate button handler**

Add method to Conductor:

```python
def _on_slate_button(self, btn: str, event: str) -> None:
    """Handle button press on Slate (change channel)."""
    logger.info(f"Slate button: {btn} {event}")

    if event == "press":
        channel_map = {"A": "subject", "B": "context", "C": "style", "D": "engine"}
        if btn in channel_map:
            self.registry.set_active_channel(channel_map[btn])
            # Broadcast updated state
            self._broadcast_state()
```

- [ ] **Step 3: Create conductor/buttons.py**

Create `conductor/buttons.py` (similar to controller/buttons.py):

```python
"""Button listeners for Conductor."""

import sys
import threading
from typing import Callable, Optional
import platform

IS_SIMULATION = platform.system() != "Linux"


class KeyboardListener:
    """Keyboard-based button listener (Conductor sim)."""

    def __init__(self, device: str = "slate"):
        """Initialize. device: 'slate' (a/b/c/d)."""
        self.device = device
        self.handler: Optional[Callable] = None
        self.running = False
        self.thread: Optional[threading.Thread] = None

        if device == "slate":
            self.key_map = {"a": "A", "b": "B", "c": "C", "d": "D"}
        else:
            self.key_map = {}

    def on(self, handler: Callable[[str, str], None]) -> None:
        """Register handler."""
        self.handler = handler

    def start(self) -> None:
        """Start listening."""
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        """Stop listening."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)

    def _listen_loop(self) -> None:
        """Listen for keyboard input."""
        print(f"KeyboardListener ({self.device}) ready. Press keys: {list(self.key_map.keys())}")

        while self.running:
            try:
                char = sys.stdin.read(1).lower()

                if char in self.key_map:
                    btn = self.key_map[char]
                    if self.handler:
                        self.handler(btn, "press")

                if char == "q":
                    self.running = False
            except Exception as e:
                print(f"Keyboard error: {e}")
                break
```

- [ ] **Step 4: Update conductor/__main__.py to start button listener**

Edit `conductor/__main__.py`:

```python
async def main():
    """Run Conductor server."""
    word_blocks_path = get_word_blocks_path()

    if not word_blocks_path.exists():
        logger.error(f"word_blocks.json not found at {word_blocks_path}")
        sys.exit(1)

    conductor = Conductor(word_blocks_path)

    try:
        logger.info("Starting Conductor server...")

        # Start button listener (if in sim)
        if conductor.buttons:
            conductor.buttons.start()

        await conductor.start("localhost", 8765)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        if conductor.buttons:
            conductor.buttons.stop()
        await conductor.shutdown()
```

- [ ] **Step 5: Test full two-handed flow**

Terminal 1 (Conductor):
```bash
python -m conductor
# Press a/b/c/d to change channels
```

Terminal 2 (Controller):
```bash
python -m controller
# Press a/b/x/y to cycle/commit options
```

Expected:
- Press Conductor `a` → channel changes to Subject, Controller display updates
- Press Controller `b` → cycles to next Subject option
- Press Controller `x` → commits option
- Press Conductor `d` → switches to Engine channel
- Conductor shows InkyMock PIL image with menu + ribbon

- [ ] **Step 6: Commit**

```bash
git add conductor/conductor.py conductor/buttons.py conductor/__main__.py
git commit -m "feat: add Slate button listener + channel switching"
```

---

### Task 11: Wiring + integration tests (end-to-end sim)

**Files:**
- Create: `tests/test_integration_e2e.py` (end-to-end flow)

#### Steps

- [ ] **Step 1: Write integration test for full flow**

Create `tests/test_integration_e2e.py`:

```python
"""End-to-end integration: Conductor server + Controller client + state machine + display."""

import asyncio
import pytest
from pathlib import Path

from conductor.conductor import Conductor
from conductor.state_machine import ChannelRegistry
from controller.controller import Controller
from shared.bus_websocket import WebSocketClient
from shared.messages import HelloMessage, ButtonMessage


@pytest.fixture
def word_blocks_path():
    return Path(__file__).parent.parent / "shared" / "data" / "word_blocks.json"


@pytest.mark.asyncio
async def test_full_two_handed_flow(word_blocks_path):
    """End-to-end: Conductor + Controller + channels + button handling."""

    # Create Conductor
    conductor = Conductor(word_blocks_path)

    # Start Conductor server
    server_task = asyncio.create_task(conductor.start("localhost", 8765))
    await asyncio.sleep(0.2)  # Let server start

    # Create Controller
    controller = Controller()

    # Connect and start
    await controller.connect("localhost", 8765)
    await asyncio.sleep(0.3)  # Let connection settle

    # Verify Controller received initial state
    assert controller.current_state is not None
    assert controller.current_state.channel == "subject"

    # Send button event: next
    button_msg = ButtonMessage(btn="B", event="press")
    await controller.bus.send(button_msg.model_dump())
    await asyncio.sleep(0.2)

    # State should have updated (option_index incremented)
    assert controller.current_state.option_index > 0

    # Send button event: commit
    button_msg = ButtonMessage(btn="X", event="press")
    await controller.bus.send(button_msg.model_dump())
    await asyncio.sleep(0.2)

    # Option should be committed
    assert controller.current_state.committed is True

    # Clean up
    await controller.shutdown()
    await conductor.shutdown()
```

- [ ] **Step 2: Run integration test**

```bash
pytest tests/test_integration_e2e.py -v -s
```

Expected: PASS. Test shows full Conductor + Controller round-trip with state updates.

- [ ] **Step 3: Commit**

```bash
git add tests/test_integration_e2e.py
git commit -m "test: add end-to-end integration test for full two-handed flow"
```

---

### Task 12: Add requirements.txt + cleanup

**Files:**
- Create: `requirements.txt`
- Modify: `.gitignore`

#### Steps

- [ ] **Step 1: Create requirements.txt**

Create `requirements.txt`:

```
websockets==12.0
pydantic==2.5.0
pillow==10.1.0
pytest==7.4.3
pytest-asyncio==0.21.1
```

- [ ] **Step 2: Run sanity check: all tests pass**

```bash
pytest tests/ -v
```

Expected: All tests PASS.

- [ ] **Step 3: Verify both Conductor and Controller can start**

Terminal 1:
```bash
python -m conductor
```

Terminal 2:
```bash
python -m controller
```

Expected: Both start cleanly, Controller connects and gets state snapshot.

- [ ] **Step 4: Final commit**

```bash
git add requirements.txt
git commit -m "feat: add Python dependencies (websockets, pydantic, pillow, pytest)"
```

---

## Summary

M0 + M1 complete:

✅ **M0 — Bus + scaffolding:**
- WebSocket server/client (`shared/bus_websocket.py`)
- Message schema (`shared/messages.py`)
- Swappable interfaces (Bus, Display, Buttons, ImageBackend, Evolver)

✅ **M1 — State machine + mocks:**
- Channels (Subject/Context/Style/Engine) + option lists loaded from `word_blocks.json`
- Button handlers (prev/next/commit/shift) in Conductor
- SparkMock: 17×7 ANSI terminal with colour bar + pips + scrolling text (two-line layout)
- InkyMock: PIL image with sideways menu strip + sentence ribbon
- Keyboard sim (a/b/x/y for Spark, a/b/c/d for Slate)
- Full two-handed flow: pick channel on Slate → cycle + commit on Spark → state broadcasts → both displays update

✅ **Tests:** Message schema, state machine, Bus round-trip, display rendering, end-to-end integration

**Ready for M2:** Image generation API + render queue (stub for now). The plumbing is solid and swappable.
