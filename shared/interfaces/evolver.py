"""Evolution operator abstraction."""

from abc import ABC, abstractmethod
from typing import List


class Evolver(ABC):
    """Abstract prompt evolver."""

    @abstractmethod
    def evolve(self, prompt: str, lineage: List[str]) -> str:
        """Mutate prompt. Lineage is history of past prompts."""
        pass
