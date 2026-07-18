"""Pure Spark frame renderer: (state, tick) → 7×17 RGB grid."""

from dataclasses import dataclass

from shared.font import render_columns, bounce_offset
from shared.interfaces.display import StateSnapshot

WIDTH = 17
HEIGHT = 7

Frame = list  # list[HEIGHT] of list[WIDTH] of (r, g, b)


@dataclass
class Effects:
    """Transient overlay state owned by the ticker."""
    flash_until: int = 0                      # tick before which full-matrix flash shows
    flash_color: tuple = (255, 255, 255)
    glint_until: int = 0                      # tick before which press glint shows
    glint_btn: str = ""                       # "A" | "B" | "X" | "Y"
    hold_btn: str = ""                        # button currently held
    hold_frac: float = 0.0                    # 0..1 growing glint


def blank_frame() -> Frame:
    return [[(0, 0, 0) for _ in range(WIDTH)] for _ in range(HEIGHT)]


def render_frame(state: StateSnapshot, tick: int, effects: Effects = None) -> Frame:
    """Pure render. No I/O, no side effects."""
    if effects and tick < effects.flash_until:
        return [[effects.flash_color for _ in range(WIDTH)] for _ in range(HEIGHT)]

    frame = blank_frame()
    r, g, b = state.channel_color

    # Row 0: channel bar — solid if committed, dim otherwise
    bar = (r, g, b) if state.committed else (r // 4, g // 4, b // 4)
    for x in range(WIDTH):
        frame[0][x] = bar

    # Row 1: option pips — three-state brightness
    for i in range(min(state.option_count, WIDTH)):
        if i == state.option_index:
            frame[1][i] = (r, g, b)  # brightest: current cursor
        elif state.committed_index is not None and i == state.committed_index:
            frame[1][i] = (r // 2, g // 2, b // 2)  # bright: committed index
        else:
            frame[1][i] = (r // 8, g // 8, b // 8)  # dim: others

    # Rows 2-6: candidate text with bounce scroll + padding
    cols = render_columns(state.candidate, padding=2)
    off = bounce_offset(len(cols), WIDTH, tick)
    for x in range(WIDTH):
        i = x + off
        if 0 <= i < len(cols):
            col = cols[i]
            for y in range(5):
                if col >> y & 1:
                    frame[2 + y][x] = (r, g, b)

    return frame
