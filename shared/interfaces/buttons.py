"""Button listener abstraction (GPIO / keyboard sim)."""

from abc import ABC, abstractmethod
from typing import Callable


class ButtonListener(ABC):
    """Abstract button listener."""

    @abstractmethod
    def on(self, handler: Callable[[str, str], None]) -> None:
        """Register handler: (btn: str, event: str) -> None. Events: press, release, hold."""
        pass

    @abstractmethod
    def start(self) -> None:
        """Start listening."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stop listening."""
        pass
