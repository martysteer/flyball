"""Display abstraction (Inky / Unicorn + mocks)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Tuple


@dataclass
class StateSnapshot:
    """Current state snapshot sent by Conductor to Controller."""
    channel: str  # "subject" | "context" | "style" | "engine"
    channel_color: Tuple[int, int, int]  # (r, g, b)
    option_index: int
    option_count: int
    candidate: str  # text to display
    committed: bool
    mode: str  # "word" | "engine"
    engine: Optional[dict] = None  # {"loop": bool, "speed_s": int, "operator": str, "queue_depth": int}


class Display(ABC):
    """Abstract display."""

    @abstractmethod
    def render(self, state: StateSnapshot) -> None:
        """Render state to display."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Clean up display."""
        pass
