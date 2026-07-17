"""Button listeners: GPIO (real) + keyboard sim."""

import sys
import threading
import tty
import termios
from abc import ABC, abstractmethod
from typing import Callable, Optional

from shared.config import IS_SIMULATION

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
    """GPIO button listener (gpiozero) with keyboard fallback in sim."""

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
            try:
                for name, pin in pins.items():
                    btn = Button(pin, pull_up=True, bounce_time=0.1)
                    btn.when_pressed = lambda n=name: self._on_press(n)
                    self.gpio_buttons[name] = btn
            except (OSError, RuntimeError, ImportError) as e:
                if not IS_SIMULATION:
                    raise RuntimeError(
                        f"GPIO buttons failed: {e}. "
                        "Ensure lgpio is installed: sudo apt install python3-lgpio"
                    ) from e
                self.gpio_buttons.clear()
                self.fallback = KeyboardListener(device=device, on_exit=on_exit)
        else:
            if not IS_SIMULATION:
                raise ImportError("gpiozero not available on Pi hardware")
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
