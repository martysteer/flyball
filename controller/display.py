"""Spark display: real Unicorn HAT Mini + pygame mock."""

import platform
from dataclasses import dataclass
from typing import Optional

from shared.interfaces.display import Display, StateSnapshot

IS_SIMULATION = platform.system() != "Linux"


@dataclass
class SparkMock(Display):
    """Mock Spark display: pygame window showing 17×7 LED matrix."""

    width: int = 17
    height: int = 7
    unicorn: Optional[object] = None
    scroll_pos: int = 0
    on_key: Optional[object] = None  # Callback: (char: str) -> None

    def __post_init__(self):
        """Initialize pygame unicorn mock."""
        if IS_SIMULATION:
            from controller.unicorn_mock import UnicornHATMiniBase
            self.unicorn = UnicornHATMiniBase()
            self.unicorn.set_brightness(0.5)
            # Wire button callback
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
                self.unicorn.set_pixel(x, 0, r//4, g//4, b//4)

            # Row 1: position pips
            if state.option_count > 0:
                for i in range(min(state.option_count, self.width)):
                    if i == state.option_index:
                        self.unicorn.set_pixel(i, 1, r, g, b)
                    else:
                        self.unicorn.set_pixel(i, 1, r//8, g//8, b//8)

            # Rows 2-6: scrolling text
            text = state.candidate
            if state.mode == "engine" and state.engine:
                text = f"[{state.engine['operator'].upper()}]"
            self._render_text(text, r, g, b)

            self.unicorn.show()
        except Exception:
            return

    def _render_text(self, text: str, r: int, g: int, b: int) -> None:
        """Render scrolling text on rows 2-6."""
        # 3x5 pixel font (very basic)
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

        # Scroll text
        text_upper = text.upper()
        x_offset = 0

        for char in text_upper[:6]:  # Max ~6 chars visible
            if char in font_3x5:
                glyph = font_3x5[char]
                for dy, row in enumerate(glyph):
                    for dx, pixel in enumerate(row):
                        x = x_offset + dx
                        y = 2 + dy  # Start at row 2
                        if pixel and 0 <= x < self.width and 0 <= y < self.height:
                            self.unicorn.set_pixel(x, y, r, g, b)
                x_offset += 4  # 3px char + 1px space

    def _on_button_pin(self, pin) -> None:
        """Handle button press from unicorn mock."""
        if pin == 'q':
            # Window close event
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
    """Real Spark display (Unicorn HAT Mini on GPIO)."""

    def __init__(self):
        """Initialize display."""
        if IS_SIMULATION:
            # Use pygame mock
            self.impl = SparkMock()
        else:
            # TODO: Use real unicornhatmini library
            # from unicornhatmini import UnicornHATMini
            # self.impl = ...
            pass

    def render(self, state: StateSnapshot) -> None:
        """Render to display."""
        if hasattr(self, 'impl'):
            self.impl.render(state)

    def close(self) -> None:
        """Clean up."""
        if hasattr(self, 'impl'):
            self.impl.close()
