"""SparkDisplay seam + terminal ANSI mock. Real Unicorn HAT Mini lands in M4."""
import sys

W, H = 17, 7

# 3x5 pixel font, rows 2-6. '#'=lit. Unknown chars render as space.
FONT = {
    "A": [".#.", "#.#", "###", "#.#", "#.#"],
    "B": ["##.", "#.#", "##.", "#.#", "##."],
    "C": [".##", "#..", "#..", "#..", ".##"],
    "D": ["##.", "#.#", "#.#", "#.#", "##."],
    "E": ["###", "#..", "##.", "#..", "###"],
    "F": ["###", "#..", "##.", "#..", "#.."],
    "G": [".##", "#..", "#.#", "#.#", ".##"],
    "H": ["#.#", "#.#", "###", "#.#", "#.#"],
    "I": ["###", ".#.", ".#.", ".#.", "###"],
    "J": ["..#", "..#", "..#", "#.#", ".#."],
    "K": ["#.#", "#.#", "##.", "#.#", "#.#"],
    "L": ["#..", "#..", "#..", "#..", "###"],
    "M": ["#.#", "###", "###", "#.#", "#.#"],
    "N": ["#.#", "###", "###", "###", "#.#"],
    "O": [".#.", "#.#", "#.#", "#.#", ".#."],
    "P": ["##.", "#.#", "##.", "#..", "#.."],
    "Q": [".#.", "#.#", "#.#", ".#.", "..#"],
    "R": ["##.", "#.#", "##.", "#.#", "#.#"],
    "S": [".##", "#..", ".#.", "..#", "##."],
    "T": ["###", ".#.", ".#.", ".#.", ".#."],
    "U": ["#.#", "#.#", "#.#", "#.#", "###"],
    "V": ["#.#", "#.#", "#.#", "#.#", ".#."],
    "W": ["#.#", "#.#", "###", "###", "#.#"],
    "X": ["#.#", "#.#", ".#.", "#.#", "#.#"],
    "Y": ["#.#", "#.#", ".#.", ".#.", ".#."],
    "Z": ["###", "..#", ".#.", "#..", "###"],
    "0": [".#.", "#.#", "#.#", "#.#", ".#."],
    "1": [".#.", "##.", ".#.", ".#.", "###"],
    "2": ["##.", "..#", ".#.", "#..", "###"],
    "3": ["###", "..#", ".#.", "..#", "##."],
    "4": ["#.#", "#.#", "###", "..#", "..#"],
    "5": ["###", "#..", "##.", "..#", "##."],
    "6": [".##", "#..", "##.", "#.#", ".#."],
    "7": ["###", "..#", ".#.", ".#.", ".#."],
    "8": [".#.", "#.#", ".#.", "#.#", ".#."],
    "9": [".#.", "#.#", ".##", "..#", "##."],
    "-": ["...", "...", "###", "...", "..."],
    "+": ["...", ".#.", "###", ".#.", "..."],
    "'": [".#.", ".#.", "...", "...", "..."],
    ".": ["...", "...", "...", "...", ".#."],
    " ": ["...", "...", "...", "...", "..."],
}


def text_columns(text):
    """Render text to a list of 5-bit columns (list of 5-char strings)."""
    cols = []
    for ch in text.upper():
        glyph = FONT.get(ch, FONT[" "])
        for x in range(3):
            cols.append("".join(glyph[y][x] for y in range(5)))
        cols.append(".....")  # 1-col letter gap
    return cols


class SparkDisplay:
    """Display seam for the fast controller."""

    def set_state(self, msg):
        raise NotImplementedError

    def tick(self):
        raise NotImplementedError


class SparkMock(SparkDisplay):
    """17x7 terminal matrix: colour bar, pips, scrolling candidate."""

    FLASH_TICKS = 4

    def __init__(self, out=sys.stdout):
        self.out = out
        self.state = None
        self.offset = -W  # scroll start: text enters from the right
        self.flash = 0
        out.write("\x1b[2J\x1b[?25l")  # clear screen, hide cursor

    def set_state(self, msg):
        prev = self.state
        if prev is None or msg["candidate"] != prev["candidate"]:
            self.offset = -W
        if msg.get("committed") and not (prev and prev.get("committed")) \
                and prev and msg["candidate"] == prev["candidate"]:
            self.flash = self.FLASH_TICKS  # commit felt, not just seen
        self.state = msg

    def _grid(self):
        """Build H rows x W cols of (r,g,b)."""
        s = self.state
        grid = [[(0, 0, 0)] * W for _ in range(H)]
        if s is None:
            return grid
        r, g, b = s["channel_color"]
        if self.flash > 0:
            self.flash -= 1
            return [[(r, g, b)] * W for _ in range(H)]
        dim = (r // 5, g // 5, b // 5)
        grid[0] = [dim] * W                                   # row 0: colour bar
        n, idx = s["option_count"], s["option_index"]
        for i in range(min(n, W)):                            # row 1: pips
            grid[1][i] = (r, g, b) if i == idx else (r // 8, g // 8, b // 8)
        cols = text_columns(s["candidate"])                   # rows 2-6: scroll
        for x in range(W):
            src = x + self.offset
            if 0 <= src < len(cols):
                for y in range(5):
                    if cols[src][y] == "#":
                        grid[2 + y][x] = (r, g, b)
        self.offset += 1
        if self.offset > len(cols):
            self.offset = -W
        return grid

    def tick(self):
        grid = self._grid()
        lines = ["\x1b[H"]  # cursor home
        for row in grid:
            lines.append("".join(f"\x1b[48;2;{r};{g};{b}m  " for r, g, b in row)
                         + "\x1b[0m")
        s = self.state or {}
        lines.append(f"\x1b[0m\x1b[K{s.get('channel', '?'):>8} "
                     f"{s.get('candidate', '')!r} "
                     f"[{s.get('option_index', 0) + 1}/{s.get('option_count', 0)}]"
                     f"{' committed' if s.get('committed') else ''}")
        lines.append("\x1b[Ka=prev b=next x=commit y=shift q=quit")
        self.out.write("\r\n".join(lines) + "\r\n")
        self.out.flush()
