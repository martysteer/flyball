"""Image generation backend abstraction."""

from abc import ABC, abstractmethod
from PIL import Image

from shared.interfaces.display import StateSnapshot


class ImageBackend(ABC):
    """Abstract image generator."""

    @abstractmethod
    async def generate(self, prompt: str) -> Image.Image:
        """Generate image from prompt."""
        pass

    def render_frame(self, state: StateSnapshot) -> Image.Image:
        """Render full Slate frame. Default: raise NotImplementedError.

        Subclasses that support frame rendering (BasicImageBackend)
        override this. AI backends (M2) use generate() instead.
        """
        raise NotImplementedError
