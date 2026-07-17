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
            try:
                self.hat = UnicornHATMini()
                self.hat.set_brightness(0.5)
                self.mock = None
                self.width = 17
                self.height = 7
            except (RuntimeError, OSError):
                # Hardware init failed, fall back to mock
                self.hat = None
                self.mock = SparkMock()
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
