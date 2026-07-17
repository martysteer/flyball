"""Button listeners for Conductor."""

import sys
import threading
import tty
import termios
from typing import Callable, Optional
import platform

IS_SIMULATION = platform.system() != "Linux"


class KeyboardListener:
    """Keyboard-based button listener (Conductor sim)."""

    def __init__(self, device: str = "slate"):
        """Initialize. device: 'slate' (a/b/c/d)."""
        self.device = device
        self.handler: Optional[Callable] = None
        self.running = False
        self.thread: Optional[threading.Thread] = None

        if device == "slate":
            self.key_map = {"a": "A", "b": "B", "c": "C", "d": "D"}
        else:
            self.key_map = {}

    def on(self, handler: Callable[[str, str], None]) -> None:
        """Register handler."""
        self.handler = handler

    def start(self) -> None:
        """Start listening."""
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
