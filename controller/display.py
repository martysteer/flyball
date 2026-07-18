"""Spark display: real Unicorn HAT Mini + pygame mock."""

from shared.config import IS_SIMULATION, get_spark_brightness

# Hardware detection
try:
    from unicornhatmini import UnicornHATMini
    HAS_UNICORN = True
except ImportError:
    HAS_UNICORN = False


class SparkMock:
    """Mock Spark display: pygame window showing 17x7 LED matrix."""

    width: int = 17
    height: int = 7

    def __init__(self):
        import pygame
        from controller.unicorn_mock import UnicornHATMiniBase
        self.unicorn = UnicornHATMiniBase()
        self.unicorn.set_brightness(get_spark_brightness())
        self.on_key = None  # Callback: (char: str) -> None
        self.unicorn.on_button_pressed(self._on_button_pin)

    def poll_events(self) -> None:
        """Process pygame events (keyboard + window close)."""
        if self.unicorn:
            self.unicorn._process_events()

    def push(self, frame) -> None:
        """Push a rendered 7x17 RGB frame to the window."""
        if not self.unicorn:
            return
        try:
            self.unicorn.clear()
            for y, row in enumerate(frame):
                for x, (r, g, b) in enumerate(row):
                    if r or g or b:
                        self.unicorn.set_pixel(x, y, r, g, b)
            self.unicorn.show()
        except Exception:
            return

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


class SparkDisplay:
    """Spark display: auto-detects real Unicorn HAT Mini or falls back to mock."""

    def __init__(self):
        if HAS_UNICORN:
            try:
                self.hat = UnicornHATMini()
                self.hat.set_brightness(get_spark_brightness())
                self.mock = None
                self.width = 17
                self.height = 7
            except (RuntimeError, OSError) as e:
                # Hardware init failed
                if not IS_SIMULATION:
                    raise RuntimeError(
                        "Unicorn HAT Mini not detected on Pi hardware. "
                        "Check I2C enabled and HAT seated properly."
                    ) from e
                self.hat = None
                self.mock = SparkMock()
        else:
            if not IS_SIMULATION:
                raise ImportError("Unicorn HAT Mini library not available on Pi hardware")
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

    def poll_events(self) -> None:
        """Process pygame events (only in sim)."""
        if self.mock:
            self.mock.poll_events()

    def push(self, frame) -> None:
        """Push a rendered frame to mock or hardware."""
        if self.mock:
            self.mock.push(frame)
            return
        self.hat.clear()
        for y, row in enumerate(frame):
            for x, (r, g, b) in enumerate(row):
                if r or g or b:
                    self.hat.set_pixel(x, y, r, g, b)
        self.hat.show()

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
