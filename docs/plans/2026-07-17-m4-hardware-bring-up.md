# M4 Hardware Bring-Up Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire real Unicorn HAT Mini, Inky Impression, and GPIO buttons on two Pi Zero 2 W devices. Run M1 functionality on physical hardware.

**Architecture:** Hardware detection via try-import at module load (no env vars). Display classes become thin output devices. PIL compositing extracted from InkyMock into BasicImageBackend. GPIO buttons via gpiozero with transparent fallback to keyboard.

**Tech Stack:** unicornhatmini, inky, gpiozero, PIL/Pillow, systemd

---

### Task 1: Update requirements.txt

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Add hardware dependencies**

```
# Runtime dependencies
websockets==12.0
pydantic==2.5.0
pillow==10.1.0
unicornhatmini>=0.0.4
inky[rpi]>=1.5.0
gpiozero>=2.0
```

These install harmlessly on Mac (no hardware to talk to). Hardware detection handles fallback.

- [ ] **Step 2: Verify install**

Run: `make setup`
Expected: All packages install. On Mac, unicornhatmini/inky/gpiozero install without errors (they just can't talk to hardware).

- [ ] **Step 3: Commit**

```bash
git add requirements.txt
git commit -m "deps: add unicornhatmini, inky, gpiozero for M4 hardware"
```

---

### Task 2: BasicImageBackend — PIL compositing extracted from InkyMock

**Files:**
- Modify: `shared/interfaces/image_backend.py` (add render_frame to ABC)
- Create: `shared/basic_image_backend.py`
- Create: `tests/test_basic_image_backend.py`

- [ ] **Step 1: Write failing test for BasicImageBackend**

Create `tests/test_basic_image_backend.py`:

```python
"""Test BasicImageBackend PIL compositing."""

from PIL import Image
from shared.basic_image_backend import BasicImageBackend
from shared.interfaces.display import StateSnapshot


def _make_state(**overrides) -> StateSnapshot:
    defaults = dict(
        channel="subject",
        channel_color=(0, 200, 80),
        option_index=0,
        option_count=5,
        candidate="hello",
        committed=False,
        mode="word",
        engine=None,
    )
    defaults.update(overrides)
    return StateSnapshot(**defaults)


def test_render_frame_returns_pil_image():
    backend = BasicImageBackend()
    img = backend.render_frame(_make_state())
    assert isinstance(img, Image.Image)
    assert img.size == (640, 400)


def test_render_frame_not_all_white():
    """Composited image should have some non-white pixels (menu strip, text)."""
    backend = BasicImageBackend()
    img = backend.render_frame(_make_state())
    pixels = list(img.getdata())
    white_count = sum(1 for p in pixels if p == (255, 255, 255))
    assert white_count < len(pixels), "Image is all white — compositing did nothing"


def test_active_channel_changes_output():
    """Different active channels should produce different images."""
    backend = BasicImageBackend()
    img_subject = backend.render_frame(_make_state(channel="subject"))
    img_engine = backend.render_frame(_make_state(channel="engine"))
    assert img_subject.tobytes() != img_engine.tobytes()


def test_engine_state_renders():
    """Engine state with metadata should render without error."""
    backend = BasicImageBackend()
    img = backend.render_frame(_make_state(
        channel="engine",
        mode="engine",
        engine={"loop": True, "speed_s": 8, "operator": "swap", "queue_depth": 2},
    ))
    assert isinstance(img, Image.Image)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/bin/python -m pytest tests/test_basic_image_backend.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'shared.basic_image_backend'`

- [ ] **Step 3: Add render_frame to ImageBackend ABC**

Modify `shared/interfaces/image_backend.py`:

```python
"""Image generation backend abstraction."""

from abc import ABC, abstractmethod
from PIL import Image

from shared.interfaces.display import StateSnapshot


class ImageBackend(ABC):
    """Abstract image generator."""

    @abstractmethod
    async def generate(self, prompt: str) -> Image.Image:
        """Generate image from prompt."""
        pass

    def render_frame(self, state: StateSnapshot) -> Image.Image:
        """Render full Slate frame. Default: raise NotImplementedError.

        Subclasses that support frame rendering (BasicImageBackend)
        override this. AI backends (M2) use generate() instead.
        """
        raise NotImplementedError
```

- [ ] **Step 4: Create BasicImageBackend with PIL compositing**

Create `shared/basic_image_backend.py`:

```python
"""BasicImageBackend: PIL compositing for Slate display (placeholder for M2 image gen)."""

from PIL import Image, ImageDraw, ImageFont

from shared.interfaces.display import StateSnapshot
from shared.interfaces.image_backend import ImageBackend


# Channel display metadata
CHANNEL_COLORS = {
    "subject": (0, 200, 80),
    "context": (0, 100, 200),
    "style": (200, 0, 150),
    "engine": (200, 150, 0),
}

CHANNEL_LABELS = {
    "subject": ("A", "Subject"),
    "context": ("B", "Context"),
    "style": ("C", "Style"),
    "engine": ("D", "Engine"),
}


class BasicImageBackend(ImageBackend):
    """Stub image backend: PIL compositing with placeholder main area."""

    def __init__(self):
        self.width = 640
        self.height = 400
        # Try to load a truetype font, fall back to default
        try:
            self.font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
            self.font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
            self.font_tiny = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
        except (IOError, OSError):
            self.font_large = ImageFont.load_default()
            self.font_small = ImageFont.load_default()
            self.font_tiny = ImageFont.load_default()

    async def generate(self, prompt: str) -> Image.Image:
        """Not used in basic backend. Returns blank image."""
        return Image.new("RGB", (self.width, self.height), (255, 255, 255))

    def render_frame(self, state: StateSnapshot) -> Image.Image:
        """Render full Slate frame: menu strip + main area + status ribbon."""
        img = Image.new("RGB", (self.width, self.height), (255, 255, 255))
        draw = ImageDraw.Draw(img)

        self._draw_menu_strip(draw, state)
        self._draw_main_area(draw, state)
        self._draw_status_ribbon(draw, state)

        return img

    def _draw_menu_strip(self, draw: ImageDraw.Draw, state: StateSnapshot) -> None:
        """Draw left menu strip with channel buttons."""
        menu_width = 80
        channel_height = self.height // 4
        channels = ["subject", "context", "style", "engine"]

        for i, channel_id in enumerate(channels):
            y = i * channel_height
            color = CHANNEL_COLORS[channel_id]
            btn_letter, label = CHANNEL_LABELS[channel_id]
            is_active = (state.channel == channel_id)

            rect = [0, y, menu_width, y + channel_height]
            if is_active:
                draw.rectangle(rect, fill=color)
                text_color = (255, 255, 255)
            else:
                draw.rectangle(rect, outline=color, width=2)
                text_color = color

            # Button letter
            draw.text((10, y + 10), f"[{btn_letter}]", fill=text_color, font=self.font_small)

            # Label (vertical, char by char)
            char_y = y + 35
            for char in label:
                draw.text((10, char_y), char, fill=text_color, font=self.font_tiny)
                char_y += 12

    def _draw_main_area(self, draw: ImageDraw.Draw, state: StateSnapshot) -> None:
        """Draw main image area (placeholder for M2)."""
        main_x = 90
        main_y = 10
        main_w = 540
        main_h = 320

        # Background
        draw.rectangle([main_x, main_y, main_x + main_w, main_y + main_h],
                       fill=(240, 240, 240), outline=(0, 0, 0), width=2)

        # Placeholder text
        draw.text((main_x + main_w // 2, main_y + 50), "Generated Image",
                  fill=(64, 64, 64), font=self.font_large, anchor="mt")

        # Current candidate
        draw.text((main_x + main_w // 2, main_y + 100),
                  f"Candidate: {state.candidate}",
                  fill=(64, 64, 64), font=self.font_small, anchor="mt")

    def _draw_status_ribbon(self, draw: ImageDraw.Draw, state: StateSnapshot) -> None:
        """Draw bottom status ribbon."""
        ribbon_y = 340

        # Top border
        draw.line([(0, ribbon_y), (self.width, ribbon_y)], fill=(128, 128, 128), width=1)

        # Sentence
        sentence = state.candidate if state.candidate else "[empty]"
        draw.text((95, ribbon_y + 15), f"Sentence: {sentence}",
                  fill=(0, 0, 0), font=self.font_small)

        # Engine status
        if state.engine:
            loop_icon = ">" if state.engine.get("loop") else "-"
            speed = state.engine.get("speed_s", 8)
            operator = state.engine.get("operator", "swap").upper()
            queue_depth = state.engine.get("queue_depth", 0)
            engine_text = f"Loop: {loop_icon} {speed}s | Op: {operator} | Queue: {queue_depth}"
            draw.text((95, ribbon_y + 40), engine_text,
                      fill=(64, 64, 64), font=self.font_small)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `venv/bin/python -m pytest tests/test_basic_image_backend.py -v`
Expected: 4 tests PASS

- [ ] **Step 6: Commit**

```bash
git add shared/interfaces/image_backend.py shared/basic_image_backend.py tests/test_basic_image_backend.py
git commit -m "feat: BasicImageBackend — PIL compositing for Slate display"
```

---

### Task 3: SparkDisplay — hardware detection + real Unicorn HAT Mini

**Files:**
- Modify: `controller/display.py`
- Create: `tests/test_spark_display.py`

- [ ] **Step 1: Write failing test for hardware detection**

Create `tests/test_spark_display.py`:

```python
"""Test SparkDisplay hardware detection and fallback."""

from unittest.mock import patch
from shared.interfaces.display import StateSnapshot


def _make_state(**overrides) -> StateSnapshot:
    defaults = dict(
        channel="subject",
        channel_color=(0, 200, 80),
        option_index=0,
        option_count=5,
        candidate="hello",
        committed=False,
        mode="word",
        engine=None,
    )
    defaults.update(overrides)
    return StateSnapshot(**defaults)


def test_has_unicorn_flag_exists():
    """Module exposes HAS_UNICORN flag."""
    from controller import display
    assert hasattr(display, "HAS_UNICORN")
    assert isinstance(display.HAS_UNICORN, bool)


def test_spark_display_falls_back_to_mock():
    """On Mac (no unicornhatmini lib), SparkDisplay uses SparkMock."""
    from controller.display import SparkDisplay, SparkMock, HAS_UNICORN
    if not HAS_UNICORN:
        d = SparkDisplay()
        assert isinstance(d.mock, SparkMock)


def test_spark_mock_render_no_crash():
    """SparkMock.render() doesn't crash."""
    from controller.display import SparkMock
    mock = SparkMock()
    mock.render(_make_state())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/bin/python -m pytest tests/test_spark_display.py -v`
Expected: FAIL — `HAS_UNICORN` not found, `d.mock` attribute doesn't exist

- [ ] **Step 3: Rewrite controller/display.py with hardware detection**

Replace `controller/display.py`:

```python
"""Spark display: real Unicorn HAT Mini + pygame mock."""

from shared.interfaces.display import Display, StateSnapshot

# Hardware detection
try:
    from unicornhatmini import UnicornHATMini
    HAS_UNICORN = True
except ImportError:
    HAS_UNICORN = False


class SparkMock(Display):
    """Mock Spark display: pygame window showing 17x7 LED matrix."""

    width: int = 17
    height: int = 7

    def __init__(self):
        import pygame
        from controller.unicorn_mock import UnicornHATMiniBase
        self.unicorn = UnicornHATMiniBase()
        self.unicorn.set_brightness(0.5)
        self.on_key = None  # Callback: (char: str) -> None
        self.unicorn.on_button_pressed(self._on_button_pin)

    def render(self, state: StateSnapshot) -> None:
        """Render state to pygame window."""
        if not self.unicorn:
            return
        try:
            self.unicorn.clear()
            r, g, b = state.channel_color

            # Row 0: color bar (full width)
            for x in range(self.width):
                self.unicorn.set_pixel(x, 0, r // 4, g // 4, b // 4)

            # Row 1: position pips
            if state.option_count > 0:
                for i in range(min(state.option_count, self.width)):
                    if i == state.option_index:
                        self.unicorn.set_pixel(i, 1, r, g, b)
                    else:
                        self.unicorn.set_pixel(i, 1, r // 8, g // 8, b // 8)

            # Rows 2-6: scrolling text
            text = state.candidate
            if state.mode == "engine" and state.engine:
                text = f"[{state.engine['operator'].upper()}]"
            self._render_text(text, r, g, b)

            self.unicorn.show()
        except Exception:
            return

    def _render_text(self, text: str, r: int, g: int, b: int) -> None:
        """Render scrolling text on rows 2-6 using 3x5 font."""
        font_3x5 = {
            'A': [[0,1,0],[1,0,1],[1,1,1],[1,0,1],[1,0,1]],
            'B': [[1,1,0],[1,0,1],[1,1,0],[1,0,1],[1,1,0]],
            'C': [[0,1,1],[1,0,0],[1,0,0],[1,0,0],[0,1,1]],
            'D': [[1,1,0],[1,0,1],[1,0,1],[1,0,1],[1,1,0]],
            'E': [[1,1,1],[1,0,0],[1,1,0],[1,0,0],[1,1,1]],
            'F': [[1,1,1],[1,0,0],[1,1,0],[1,0,0],[1,0,0]],
            'G': [[0,1,1],[1,0,0],[1,0,1],[1,0,1],[0,1,1]],
            'H': [[1,0,1],[1,0,1],[1,1,1],[1,0,1],[1,0,1]],
            'I': [[1,1,1],[0,1,0],[0,1,0],[0,1,0],[1,1,1]],
            'J': [[0,0,1],[0,0,1],[0,0,1],[1,0,1],[0,1,0]],
            'K': [[1,0,1],[1,0,1],[1,1,0],[1,0,1],[1,0,1]],
            'L': [[1,0,0],[1,0,0],[1,0,0],[1,0,0],[1,1,1]],
            'M': [[1,0,1],[1,1,1],[1,0,1],[1,0,1],[1,0,1]],
            'N': [[1,0,1],[1,1,1],[1,0,1],[1,0,1],[1,0,1]],
            'O': [[0,1,0],[1,0,1],[1,0,1],[1,0,1],[0,1,0]],
            'P': [[1,1,0],[1,0,1],[1,1,0],[1,0,0],[1,0,0]],
            'R': [[1,1,0],[1,0,1],[1,1,0],[1,0,1],[1,0,1]],
            'S': [[0,1,1],[1,0,0],[0,1,0],[0,0,1],[1,1,0]],
            'T': [[1,1,1],[0,1,0],[0,1,0],[0,1,0],[0,1,0]],
            'U': [[1,0,1],[1,0,1],[1,0,1],[1,0,1],[0,1,0]],
            'V': [[1,0,1],[1,0,1],[1,0,1],[1,0,1],[0,1,0]],
            'W': [[1,0,1],[1,0,1],[1,0,1],[1,1,1],[1,0,1]],
            'X': [[1,0,1],[1,0,1],[0,1,0],[1,0,1],[1,0,1]],
            'Y': [[1,0,1],[1,0,1],[0,1,0],[0,1,0],[0,1,0]],
            ' ': [[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0]],
            '[': [[1,1,0],[1,0,0],[1,0,0],[1,0,0],[1,1,0]],
            ']': [[0,1,1],[0,0,1],[0,0,1],[0,0,1],[0,1,1]],
        }

        text_upper = text.upper()
        x_offset = 0

        for char in text_upper[:6]:
            if char in font_3x5:
                glyph = font_3x5[char]
                for dy, row in enumerate(glyph):
                    for dx, pixel in enumerate(row):
                        x = x_offset + dx
                        y = 2 + dy
                        if pixel and 0 <= x < self.width and 0 <= y < self.height:
                            self.unicorn.set_pixel(x, y, r, g, b)
                x_offset += 4

    def _on_button_pin(self, pin) -> None:
        """Handle button press from unicorn mock."""
        if pin == 'q':
            if self.on_key:
                self.on_key('q')
            return
        pin_map = {5: 'a', 6: 'b', 16: 'x', 24: 'y'}
        char = pin_map.get(pin)
        if char and self.on_key:
            self.on_key(char)

    def close(self) -> None:
        """Clean up display."""
        if self.unicorn:
            try:
                self.unicorn.clear()
                self.unicorn.show()
            except Exception:
                pass
            self.unicorn = None


class SparkDisplay(Display):
    """Spark display: auto-detects real Unicorn HAT Mini or falls back to mock."""

    def __init__(self):
        if HAS_UNICORN:
            self.hat = UnicornHATMini()
            self.hat.set_brightness(0.5)
            self.mock = None
            self.width = 17
            self.height = 7
        else:
            self.hat = None
            self.mock = SparkMock()

    @property
    def on_key(self):
        """Proxy on_key to mock (only used in sim)."""
        return self.mock.on_key if self.mock else None

    @on_key.setter
    def on_key(self, value):
        if self.mock:
            self.mock.on_key = value

    def render(self, state: StateSnapshot) -> None:
        """Render to display."""
        if self.mock:
            self.mock.render(state)
            return

        # Real hardware: same rendering as SparkMock but on real HAT
        r, g, b = state.channel_color

        # Row 0: color bar
        for x in range(self.width):
            self.hat.set_pixel(x, 0, r // 4, g // 4, b // 4)

        # Row 1: position pips
        if state.option_count > 0:
            for i in range(min(state.option_count, self.width)):
                if i == state.option_index:
                    self.hat.set_pixel(i, 1, r, g, b)
                else:
                    self.hat.set_pixel(i, 1, r // 8, g // 8, b // 8)

        # Rows 2-6: scrolling text
        text = state.candidate
        if state.mode == "engine" and state.engine:
            text = f"[{state.engine['operator'].upper()}]"
        self._render_text_hw(text, r, g, b)

        self.hat.show()

    def _render_text_hw(self, text: str, r: int, g: int, b: int) -> None:
        """Render text on real hardware (same 3x5 font)."""
        # ponytail: duplicated font dict from SparkMock — extract if a 3rd consumer appears
        font_3x5 = {
            'A': [[0,1,0],[1,0,1],[1,1,1],[1,0,1],[1,0,1]],
            'B': [[1,1,0],[1,0,1],[1,1,0],[1,0,1],[1,1,0]],
            'C': [[0,1,1],[1,0,0],[1,0,0],[1,0,0],[0,1,1]],
            'D': [[1,1,0],[1,0,1],[1,0,1],[1,0,1],[1,1,0]],
            'E': [[1,1,1],[1,0,0],[1,1,0],[1,0,0],[1,1,1]],
            'F': [[1,1,1],[1,0,0],[1,1,0],[1,0,0],[1,0,0]],
            'G': [[0,1,1],[1,0,0],[1,0,1],[1,0,1],[0,1,1]],
            'H': [[1,0,1],[1,0,1],[1,1,1],[1,0,1],[1,0,1]],
            'I': [[1,1,1],[0,1,0],[0,1,0],[0,1,0],[1,1,1]],
            'J': [[0,0,1],[0,0,1],[0,0,1],[1,0,1],[0,1,0]],
            'K': [[1,0,1],[1,0,1],[1,1,0],[1,0,1],[1,0,1]],
            'L': [[1,0,0],[1,0,0],[1,0,0],[1,0,0],[1,1,1]],
            'M': [[1,0,1],[1,1,1],[1,0,1],[1,0,1],[1,0,1]],
            'N': [[1,0,1],[1,1,1],[1,0,1],[1,0,1],[1,0,1]],
            'O': [[0,1,0],[1,0,1],[1,0,1],[1,0,1],[0,1,0]],
            'P': [[1,1,0],[1,0,1],[1,1,0],[1,0,0],[1,0,0]],
            'R': [[1,1,0],[1,0,1],[1,1,0],[1,0,1],[1,0,1]],
            'S': [[0,1,1],[1,0,0],[0,1,0],[0,0,1],[1,1,0]],
            'T': [[1,1,1],[0,1,0],[0,1,0],[0,1,0],[0,1,0]],
            'U': [[1,0,1],[1,0,1],[1,0,1],[1,0,1],[0,1,0]],
            'V': [[1,0,1],[1,0,1],[1,0,1],[1,0,1],[0,1,0]],
            'W': [[1,0,1],[1,0,1],[1,0,1],[1,1,1],[1,0,1]],
            'X': [[1,0,1],[1,0,1],[0,1,0],[1,0,1],[1,0,1]],
            'Y': [[1,0,1],[1,0,1],[0,1,0],[0,1,0],[0,1,0]],
            ' ': [[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0]],
            '[': [[1,1,0],[1,0,0],[1,0,0],[1,0,0],[1,1,0]],
            ']': [[0,1,1],[0,0,1],[0,0,1],[0,0,1],[0,1,1]],
        }

        text_upper = text.upper()
        x_offset = 0
        for char in text_upper[:6]:
            if char in font_3x5:
                glyph = font_3x5[char]
                for dy, row in enumerate(glyph):
                    for dx, pixel in enumerate(row):
                        x = x_offset + dx
                        y = 2 + dy
                        if pixel and 0 <= x < self.width and 0 <= y < self.height:
                            self.hat.set_pixel(x, y, r, g, b)
                x_offset += 4

    def close(self) -> None:
        """Clean up display."""
        if self.mock:
            self.mock.close()
        if self.hat:
            try:
                # Clear LEDs on shutdown
                for x in range(self.width):
                    for y in range(self.height):
                        self.hat.set_pixel(x, y, 0, 0, 0)
                self.hat.show()
            except Exception:
                pass
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `venv/bin/python -m pytest tests/test_spark_display.py -v`
Expected: 3 tests PASS

- [ ] **Step 5: Run full suite**

Run: `venv/bin/python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add controller/display.py tests/test_spark_display.py
git commit -m "feat: SparkDisplay hardware detection + real Unicorn HAT Mini"
```

---

### Task 4: SlateDisplay — hardware detection + InkyMock receives PIL Image

**Files:**
- Modify: `conductor/display.py`
- Create: `tests/test_slate_display.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_slate_display.py`:

```python
"""Test SlateDisplay hardware detection and InkyMock PIL Image flow."""

from PIL import Image
from shared.interfaces.display import StateSnapshot


def _make_state(**overrides) -> StateSnapshot:
    defaults = dict(
        channel="subject",
        channel_color=(0, 200, 80),
        option_index=0,
        option_count=5,
        candidate="hello",
        committed=False,
        mode="word",
        engine=None,
    )
    defaults.update(overrides)
    return StateSnapshot(**defaults)


def test_has_inky_flag_exists():
    """Module exposes HAS_INKY flag."""
    from conductor import display
    assert hasattr(display, "HAS_INKY")
    assert isinstance(display.HAS_INKY, bool)


def test_inky_mock_render_image():
    """InkyMock.render_image accepts PIL Image without crash."""
    from conductor.display import InkyMock
    mock = InkyMock()
    img = Image.new("RGB", (640, 400), (128, 128, 128))
    mock.render_image(img)
    mock.close()


def test_slate_display_render_image():
    """SlateDisplay.render_image forwards to implementation."""
    from conductor.display import SlateDisplay, HAS_INKY
    if not HAS_INKY:
        d = SlateDisplay()
        img = Image.new("RGB", (640, 400), (200, 200, 200))
        d.render_image(img)
        d.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/bin/python -m pytest tests/test_slate_display.py -v`
Expected: FAIL — `HAS_INKY` not found, `render_image` method doesn't exist

- [ ] **Step 3: Rewrite conductor/display.py**

Replace `conductor/display.py`:

```python
"""Slate display: real Inky Impression + pygame mock."""

from PIL import Image

from shared.interfaces.display import Display, StateSnapshot

# Hardware detection
try:
    from inky.auto import auto as InkyAuto
    HAS_INKY = True
except ImportError:
    HAS_INKY = False


class InkyMock(Display):
    """Mock Slate display: pygame window showing Inky Impression layout.

    Receives a PIL Image from BasicImageBackend and blits to pygame.
    Also handles pygame event loop (keyboard, window close).
    """

    def __init__(self):
        self.width = 640
        self.height = 400
        self.screen = None
        self.on_key = None  # Callback: (char: str) -> None
        self._init_pygame()

    def _init_pygame(self):
        """Initialize pygame window."""
        try:
            import pygame
            self._pygame = pygame
            pygame.init()
            try:
                self.screen = pygame.display.set_mode(
                    (self.width, self.height),
                    pygame.WINDOWSTAYSONTOP
                )
            except Exception:
                self.screen = pygame.display.set_mode((self.width, self.height))
            pygame.display.set_caption("Flyball Slate Mock (Inky Impression)")
        except ImportError:
            # No pygame (e.g. headless Pi without dev deps) — skip display
            self._pygame = None

    def render(self, state: StateSnapshot) -> None:
        """Legacy render — kept for backward compat during transition.

        Conductor should call render_image() with a PIL Image from
        BasicImageBackend instead. This method is a no-op placeholder.
        """
        pass

    def render_image(self, img: Image.Image) -> None:
        """Render a PIL Image to pygame window."""
        if not self.screen or not self._pygame:
            return

        pygame = self._pygame

        # Process events (prevent window freeze + handle keyboard)
        try:
            events = pygame.event.get()
        except pygame.error:
            return

        for event in events:
            if event.type == pygame.QUIT:
                if self.on_key:
                    self.on_key('q')
                return
            elif event.type == pygame.KEYDOWN:
                key_map = {
                    pygame.K_a: 'a',
                    pygame.K_b: 'b',
                    pygame.K_c: 'c',
                    pygame.K_d: 'd',
                    pygame.K_q: 'q',
                }
                char = key_map.get(event.key)
                if char and self.on_key:
                    self.on_key(char)

        # Convert PIL Image to pygame surface and blit
        raw = img.tobytes()
        surface = pygame.image.fromstring(raw, img.size, img.mode)
        self.screen.blit(surface, (0, 0))
        pygame.display.flip()

    def close(self) -> None:
        """Clean up display."""
        if self.screen and self._pygame:
            self.screen.fill((255, 255, 255))
            self._pygame.display.flip()
            self.screen = None


class SlateDisplay(Display):
    """Slate display: auto-detects real Inky Impression or falls back to mock."""

    def __init__(self):
        if HAS_INKY:
            self.inky = InkyAuto()
            self.inky.set_border(self.inky.WHITE)
            self.mock = None
        else:
            self.inky = None
            self.mock = InkyMock()

    @property
    def on_key(self):
        """Proxy on_key to mock (only used in sim)."""
        return self.mock.on_key if self.mock else None

    @on_key.setter
    def on_key(self, value):
        if self.mock:
            self.mock.on_key = value

    def render(self, state: StateSnapshot) -> None:
        """Legacy render — no-op. Use render_image()."""
        pass

    def render_image(self, img: Image.Image) -> None:
        """Show a PIL Image on the display."""
        if self.mock:
            self.mock.render_image(img)
            return

        # Real Inky Impression
        self.inky.set_image(img)
        self.inky.show()

    def close(self) -> None:
        """Clean up display."""
        if self.mock:
            self.mock.close()
```

- [ ] **Step 4: Run tests**

Run: `venv/bin/python -m pytest tests/test_slate_display.py -v`
Expected: 3 tests PASS

- [ ] **Step 5: Run full suite**

Run: `venv/bin/python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add conductor/display.py tests/test_slate_display.py
git commit -m "feat: SlateDisplay hardware detection + InkyMock receives PIL Image"
```

---

### Task 5: GPIO Button Listeners

**Files:**
- Modify: `controller/buttons.py`
- Modify: `conductor/buttons.py`
- Create: `tests/test_gpio_buttons.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_gpio_buttons.py`:

```python
"""Test GPIO button listener hardware detection and fallback."""


def test_controller_has_gpio_flag():
    """controller.buttons exposes HAS_GPIO flag."""
    from controller import buttons
    assert hasattr(buttons, "HAS_GPIO")
    assert isinstance(buttons.HAS_GPIO, bool)


def test_conductor_has_gpio_flag():
    """conductor.buttons exposes HAS_GPIO flag."""
    from conductor import buttons
    assert hasattr(buttons, "HAS_GPIO")
    assert isinstance(buttons.HAS_GPIO, bool)


def test_gpio_listener_fallback_to_keyboard():
    """GPIOButtonListener without GPIO falls back to KeyboardListener."""
    from controller.buttons import GPIOButtonListener, HAS_GPIO
    if not HAS_GPIO:
        listener = GPIOButtonListener(device="spark")
        assert listener.fallback is not None


def test_gpio_listener_has_button_interface():
    """GPIOButtonListener has on/start/stop methods."""
    from controller.buttons import GPIOButtonListener
    listener = GPIOButtonListener(device="spark")
    assert callable(getattr(listener, "on", None))
    assert callable(getattr(listener, "start", None))
    assert callable(getattr(listener, "stop", None))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/bin/python -m pytest tests/test_gpio_buttons.py -v`
Expected: FAIL — `HAS_GPIO` and `GPIOButtonListener` not found

- [ ] **Step 3: Rewrite controller/buttons.py with GPIOButtonListener**

Replace `controller/buttons.py`:

```python
"""Button listeners: GPIO (real) + keyboard sim."""

import sys
import threading
import tty
import termios
from abc import ABC, abstractmethod
from typing import Callable, Optional

# Hardware detection
try:
    from gpiozero import Button
    HAS_GPIO = True
except ImportError:
    HAS_GPIO = False


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

    def __init__(self, device: str = "spark", on_exit: Optional[Callable] = None):
        """Initialize. device: 'spark' (a/b/x/y) or 'slate' (a/b/c/d)."""
        self.device = device
        self.handler: Optional[Callable] = None
        self.on_exit = on_exit
        self.running = False
        self.thread: Optional[threading.Thread] = None

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

        old_settings = None
        try:
            old_settings = termios.tcgetattr(sys.stdin)
            tty.setcbreak(sys.stdin.fileno())
        except Exception:
            pass

        try:
            while self.running:
                try:
                    char = sys.stdin.read(1).lower()

                    if char == "\x03" or char == "q":
                        if char == "\x03":
                            print("\n^C")
                        self.running = False
                        if self.on_exit:
                            self.on_exit()
                        break

                    if char in self.key_map:
                        btn = self.key_map[char]
                        if self.handler:
                            self.handler(btn, "press")
                except Exception as e:
                    print(f"\nKeyboard error: {e}")
                    break
        finally:
            if old_settings:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                print()


class GPIOButtonListener(ButtonListener):
    """GPIO button listener with transparent fallback to keyboard."""

    # BCM pins: same physical pins on both devices, different button names
    SPARK_PINS = {"A": 5, "B": 6, "X": 16, "Y": 24}
    SLATE_PINS = {"A": 5, "B": 6, "C": 16, "D": 24}

    def __init__(self, device: str = "spark", on_exit: Optional[Callable] = None):
        self.device = device
        self.on_exit = on_exit
        self.handler: Optional[Callable] = None
        self.fallback: Optional[KeyboardListener] = None
        self.gpio_buttons = {}

        pins = self.SPARK_PINS if device == "spark" else self.SLATE_PINS

        if HAS_GPIO:
            for name, pin in pins.items():
                btn = Button(pin, pull_up=True, bounce_time=0.1)
                btn.when_pressed = lambda n=name: self._on_press(n)
                self.gpio_buttons[name] = btn
        else:
            self.fallback = KeyboardListener(device=device, on_exit=on_exit)

    def _on_press(self, btn_name: str) -> None:
        """Handle GPIO button press."""
        if self.handler:
            self.handler(btn_name, "press")

    def on(self, handler: Callable[[str, str], None]) -> None:
        """Register handler."""
        self.handler = handler
        if self.fallback:
            self.fallback.on(handler)

    def start(self) -> None:
        """Start listening."""
        if self.fallback:
            self.fallback.start()
        # GPIO buttons fire via callbacks — no thread needed

    def stop(self) -> None:
        """Stop listening."""
        if self.fallback:
            self.fallback.stop()
        for btn in self.gpio_buttons.values():
            btn.close()
```

- [ ] **Step 4: Rewrite conductor/buttons.py**

Replace `conductor/buttons.py`:

```python
"""Button listeners for Conductor — reuses controller's implementations."""

# ponytail: conductor had its own KeyboardListener copy. Reuse controller's.
from controller.buttons import (
    ButtonListener,
    KeyboardListener,
    GPIOButtonListener,
    HAS_GPIO,
)
```

- [ ] **Step 5: Run tests**

Run: `venv/bin/python -m pytest tests/test_gpio_buttons.py -v`
Expected: 4 tests PASS

- [ ] **Step 6: Run full suite**

Run: `venv/bin/python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 7: Commit**

```bash
git add controller/buttons.py conductor/buttons.py tests/test_gpio_buttons.py
git commit -m "feat: GPIOButtonListener with gpiozero + keyboard fallback"
```

---

### Task 6: Wire Conductor to use BasicImageBackend + GPIOButtonListener

**Files:**
- Modify: `conductor/conductor.py`

- [ ] **Step 1: Update conductor/conductor.py**

Replace `conductor/conductor.py`:

```python
"""Conductor (Slate authority): state machine + server."""

import asyncio
import logging
from pathlib import Path
from typing import Optional

from conductor.state_machine import ChannelRegistry, StateSnapshot
from conductor.display import InkyMock, SlateDisplay, HAS_INKY
from conductor.buttons import KeyboardListener, GPIOButtonListener, HAS_GPIO
from shared.bus_websocket import WebSocketServer
from shared.messages import ButtonMessage, StateMessage, PongMessage
from shared.keymap import Keymap, normalize_action
from shared.basic_image_backend import BasicImageBackend

logger = logging.getLogger(__name__)

KEYMAPS_DIR = Path(__file__).parent.parent / "shared" / "keymaps"


class Conductor:
    """State authority; runs on Slate."""

    def __init__(self, word_blocks_path: Path):
        """Initialize Conductor."""
        self.registry = ChannelRegistry(word_blocks_path)
        self.bus = WebSocketServer()
        self.display = SlateDisplay()
        self.image_backend = BasicImageBackend()
        self.loop = None
        self.buttons: Optional[GPIOButtonListener] = None
        self.server_running = True

        # Load keymaps
        self.spark_keymap = Keymap.load(KEYMAPS_DIR / "spark.json")
        self.slate_keymap = Keymap.load(KEYMAPS_DIR / "slate.json")

        # Action handlers
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
        self.loop = asyncio.get_running_loop()
        await self.bus.start(host, port)

        # Wire input: pygame keyboard in sim, GPIO on hardware
        if not HAS_GPIO and hasattr(self.display, 'on_key') and self.display.on_key is not None or not HAS_GPIO:
            # Simulation — try pygame keys first
            if hasattr(self.display, 'on_key'):
                self.display.on_key = self._on_key
            else:
                self.buttons = GPIOButtonListener(device="slate", on_exit=self._on_exit_signal)
                self.buttons.on(self._on_slate_button)
                self.buttons.start()
        else:
            # Hardware GPIO
            self.buttons = GPIOButtonListener(device="slate", on_exit=self._on_exit_signal)
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
            print(f"[{label}] {btn} -> {action}{(' ' + str(params)) if params else ''}", flush=True)
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

        # Render to Slate display via BasicImageBackend
        frame = self.image_backend.render_frame(snapshot)
        self.display.render_image(frame)
```

- [ ] **Step 2: Run full test suite**

Run: `venv/bin/python -m pytest tests/ -v`
Expected: All tests PASS. Existing `test_keymap.py::test_all_keymap_actions_have_handlers` still passes (Conductor constructor unchanged in action dict).

- [ ] **Step 3: Commit**

```bash
git add conductor/conductor.py
git commit -m "feat: conductor uses BasicImageBackend + GPIOButtonListener"
```

---

### Task 7: Wire Controller to use GPIOButtonListener

**Files:**
- Modify: `controller/controller.py`

- [ ] **Step 1: Update controller/controller.py**

Replace `controller/controller.py`:

```python
"""Controller (Spark client): LED UI + button listener."""

import asyncio
import logging
from typing import Optional

from controller.display import SparkDisplay, HAS_UNICORN
from controller.buttons import GPIOButtonListener, HAS_GPIO
from shared.bus_websocket import WebSocketClient
from shared.messages import HelloMessage, StateMessage, PingMessage, ButtonMessage
from shared.interfaces.display import StateSnapshot

logger = logging.getLogger(__name__)


class Controller:
    """UI client; runs on Spark."""

    def __init__(self):
        """Initialize Controller."""
        self.bus = WebSocketClient()
        self.display = SparkDisplay()
        self.buttons: Optional[GPIOButtonListener] = None
        self.running = False
        self.current_state: Optional[StateSnapshot] = None
        self.loop = None
        self.heartbeat_task = None

        # Register bus handlers
        self.bus.on("state", self._on_state)
        self.bus.on("patch", self._on_patch)
        self.bus.on("pong", self._on_pong)
        self.bus.on("toast", self._on_toast)

    async def connect(self, host: str, port: int) -> None:
        """Connect to Conductor and start listening."""
        await self.bus.connect(host, port)
        self.running = True
        self.loop = asyncio.get_running_loop()

        # Send hello
        hello = HelloMessage(device="spark", fw="0.1.0")
        await self.bus.send(hello.model_dump())

        # Wire input: pygame keyboard in sim, GPIO on hardware
        if not HAS_GPIO and hasattr(self.display, 'on_key'):
            self.display.on_key = self._on_key
        else:
            self.buttons = GPIOButtonListener(device="spark", on_exit=self._on_exit_signal)
            self.buttons.on(self._on_button_event)
            self.buttons.start()

        # Start heartbeat
        self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def shutdown(self) -> None:
        """Shut down client."""
        self.running = False
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass
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
        """Handle toast message."""
        logger.info(f"Toast: {msg.get('text')}")

    def _on_key(self, char: str) -> None:
        """Handle key press from pygame display."""
        key_map = {'a': 'A', 'b': 'B', 'x': 'X', 'y': 'Y'}
        if char == 'q':
            self._on_exit_signal()
        elif char in key_map:
            self._on_button_event(key_map[char], "press")

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

    def _on_button_event(self, btn: str, event: str) -> None:
        """Handle button press."""
        print(f"[Spark] {btn} {event}", flush=True)
        button_msg = ButtonMessage(btn=btn, event=event)
        self._schedule(self.bus.send(button_msg.model_dump()))

    def _on_exit_signal(self) -> None:
        """Handle exit signal."""
        self.running = False

    async def _heartbeat_loop(self) -> None:
        """Send periodic ping to Conductor."""
        while self.running:
            await asyncio.sleep(2)
            ping = PingMessage()
            await self.bus.send(ping.model_dump())
```

- [ ] **Step 2: Run full test suite**

Run: `venv/bin/python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add controller/controller.py
git commit -m "feat: controller uses GPIOButtonListener + SparkDisplay hardware detection"
```

---

### Task 8: Systemd units + Makefile install target

**Files:**
- Create: `deploy/flyball-slate.service`
- Create: `deploy/flyball-spark.service`
- Modify: `Makefile`

- [ ] **Step 1: Create deploy directory**

Run: `mkdir -p deploy`

- [ ] **Step 2: Create flyball-slate.service**

Create `deploy/flyball-slate.service`:

```ini
[Unit]
Description=Flyball Slate Conductor
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/flyball
ExecStart=/home/pi/flyball/venv/bin/python -m conductor
Restart=always
RestartSec=10
Environment="FLYBALL_CONDUCTOR_HOST=0.0.0.0"

[Install]
WantedBy=multi-user.target
```

- [ ] **Step 3: Create flyball-spark.service**

Create `deploy/flyball-spark.service`:

```ini
[Unit]
Description=Flyball Spark Controller
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/flyball
ExecStart=/home/pi/flyball/venv/bin/python -m controller
Restart=always
RestartSec=10
Environment="FLYBALL_CONDUCTOR_HOST=flyball-slate.local"

[Install]
WantedBy=multi-user.target
```

- [ ] **Step 4: Update Makefile install target**

Replace the `install` target in `Makefile`:

```makefile
# Pi deployment: install systemd services (code stays in ~/flyball via git)
install:
	@echo "Installing systemd services..."
	sudo cp deploy/flyball-slate.service /etc/systemd/system/ 2>/dev/null || true
	sudo cp deploy/flyball-spark.service /etc/systemd/system/ 2>/dev/null || true
	sudo systemctl daemon-reload
	@echo ""
	@echo "Services installed. Enable the appropriate one:"
	@echo "  sudo systemctl enable --now flyball-slate   # on Slate Pi"
	@echo "  sudo systemctl enable --now flyball-spark   # on Spark Pi"
```

- [ ] **Step 5: Commit**

```bash
git add deploy/flyball-slate.service deploy/flyball-spark.service Makefile
git commit -m "feat: systemd units + revised make install for Pi deployment"
```

---

### Task 9: Remove IS_SIMULATION from display and button modules

**Files:**
- Modify: `controller/display.py` (already done in Task 3)
- Modify: `conductor/display.py` (already done in Task 4)
- Modify: `controller/buttons.py` (already done in Task 5)
- Modify: `conductor/buttons.py` (already done in Task 5)
- Verify: `shared/config.py` keeps IS_SIMULATION (still used elsewhere)

- [ ] **Step 1: Verify IS_SIMULATION removed from display/button modules**

Run: `grep -rn "IS_SIMULATION" controller/display.py conductor/display.py controller/buttons.py conductor/buttons.py`
Expected: No matches. All four files now use hardware detection (`HAS_UNICORN`, `HAS_INKY`, `HAS_GPIO`).

Run: `grep -rn "IS_SIMULATION" shared/config.py`
Expected: One match — `shared/config.py:8:IS_SIMULATION = platform.system() != "Linux"` — kept for other uses.

- [ ] **Step 2: Run full test suite**

Run: `venv/bin/python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 3: Commit (only if any cleanup needed)**

If any IS_SIMULATION references remain in display/button files, remove them and commit:

```bash
git add -u
git commit -m "refactor: remove IS_SIMULATION from display and button modules"
```

---

### Task 10: Integration smoke test

- [ ] **Step 1: Run full test suite**

Run: `venv/bin/python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 2: Manual sim test on Mac**

Run in terminal 1: `make conductor`
Run in terminal 2: `make controller`

Verify:
- Both windows appear (Slate pygame + Spark pygame)
- A/B/C/D keys on Slate window switch channels
- A/B/X/Y keys on Spark window cycle options + commit
- Slate display shows PIL-composited image (menu strip, main area, status ribbon)
- No errors in terminal output

- [ ] **Step 3: Commit any fixes**

If smoke test reveals issues, fix and commit.

```bash
git add -u
git commit -m "fix: integration fixes from M4 smoke test"
```
