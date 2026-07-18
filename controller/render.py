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

    # Rows 2-6: candidate text with bounce scroll + padding
    cols = render_columns(state.candidate, padding=5)
    off = bounce_offset(len(cols), WIDTH, tick)
    for x in range(WIDTH):
        i = x + off
        if 0 <= i < len(cols):
            col = cols[i]
            for y in range(5):
                if col >> y & 1:
                    frame[2 + y][x] = (r, g, b)

    return frame
