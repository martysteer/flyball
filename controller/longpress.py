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
