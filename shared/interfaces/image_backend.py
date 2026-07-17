"""Image generation backend abstraction."""

from abc import ABC, abstractmethod
from PIL import Image


class ImageBackend(ABC):
    """Abstract image generator."""

    @abstractmethod
    async def generate(self, prompt: str) -> Image.Image:
        """Generate image from prompt."""
        pass
