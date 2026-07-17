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

        # Render to terminal (use ANSI codes, not os.system which breaks in raw mode)
        print(f"\033[2J\033[H", end="")  # Clear screen + cursor home
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
