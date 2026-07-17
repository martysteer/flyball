"""Button listeners: GPIO (real) + keyboard sim."""

import sys
import threading
import tty
import termios
from abc import ABC, abstractmethod
from typing import Callable, Optional
import platform

IS_SIMULATION = platform.system() != "Linux"


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

    def __init__(self, device: str = "spark"):
        """Initialize. device: 'spark' (a/b/x/y) or 'slate' (a/b/c/d)."""
        self.device = device
        self.handler: Optional[Callable] = None
        self.running = False
        self.thread: Optional[threading.Thread] = None

        # Map keyboard keys to buttons
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

        # Set terminal to raw mode (unbuffered, no echo)
        old_settings = None
        try:
            old_settings = termios.tcgetattr(sys.stdin)
            tty.setraw(sys.stdin.fileno())
        except:
            # If not a TTY (e.g. in tests), fall back to buffered
            pass

        try:
            while self.running:
                try:
                    # Read one character (unbuffered)
                    char = sys.stdin.read(1).lower()

                    # Handle Ctrl+C (raw mode captures it as \x03)
                    if char == "\x03":
                        print("\n^C (Ctrl+C caught - exiting)")
                        self.running = False
                        break

                    if char in self.key_map:
                        btn = self.key_map[char]
                        if self.handler:
                            self.handler(btn, "press")

                    if char == "q":
                        self.running = False
                except Exception as e:
                    print(f"\nKeyboard error: {e}")
                    break
        finally:
            # Restore terminal settings
            if old_settings:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                print()  # New line after raw mode


class GPIOListener(ButtonListener):
    """GPIO-based button listener (real hardware)."""

    def __init__(self, device: str, pins: dict):
        """Initialize. pins: {"A": 5, "B": 6, "X": 16, "Y": 24}."""
        self.device = device
        self.pins = pins
        self.handler: Optional[Callable] = None
        self.running = False

    def on(self, handler: Callable[[str, str], None]) -> None:
        """Register handler."""
        self.handler = handler

    def start(self) -> None:
        """Start listening on GPIO (stub for M1)."""
        self.running = True
        # TODO: set up gpiozero / gpiod listeners

    def stop(self) -> None:
        """Stop listening."""
        self.running = False
        # TODO: cleanup GPIO
