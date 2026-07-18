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
