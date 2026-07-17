"""Slate display: real Inky Impression + pygame mock."""

from PIL import Image

from shared.interfaces.display import Display, StateSnapshot

# Hardware detection
try:
    from inky.auto import auto as InkyAuto
    HAS_INKY = True
except ImportError:
    HAS_INKY = False


class InkyMock(Display):
    """Mock Slate display: pygame window showing Inky Impression layout.

    Receives a PIL Image from BasicImageBackend and blits to pygame.
    Also handles pygame event loop (keyboard, window close).
    """

    def __init__(self):
        self.width = 640
        self.height = 400
        self.screen = None
        self.on_key = None  # Callback: (char: str) -> None
        self._init_pygame()

    def _init_pygame(self):
        """Initialize pygame window."""
        try:
            import pygame
            self._pygame = pygame
            pygame.init()
            try:
                self.screen = pygame.display.set_mode(
                    (self.width, self.height),
                    pygame.WINDOWSTAYSONTOP
                )
            except Exception:
                self.screen = pygame.display.set_mode((self.width, self.height))
            pygame.display.set_caption("Flyball Slate Mock (Inky Impression)")
        except ImportError:
            # No pygame (e.g. headless Pi without dev deps) — skip display
            self._pygame = None

    def render(self, state: StateSnapshot) -> None:
        """Legacy render — kept for backward compat during transition.

        Conductor should call render_image() with a PIL Image from
        BasicImageBackend instead. This method is a no-op placeholder.
        """
        pass

    def render_image(self, img: Image.Image) -> None:
        """Render a PIL Image to pygame window."""
        if not self.screen or not self._pygame:
            return

        pygame = self._pygame

        # Process events (prevent window freeze + handle keyboard)
        try:
            events = pygame.event.get()
        except pygame.error:
            return

        for event in events:
            if event.type == pygame.QUIT:
                if self.on_key:
                    self.on_key('q')
                return
            elif event.type == pygame.KEYDOWN:
                key_map = {
                    pygame.K_a: 'a',
                    pygame.K_b: 'b',
                    pygame.K_c: 'c',
                    pygame.K_d: 'd',
                    pygame.K_q: 'q',
                }
                char = key_map.get(event.key)
                if char and self.on_key:
                    self.on_key(char)

        # Convert PIL Image to pygame surface and blit
        raw = img.tobytes()
        surface = pygame.image.fromstring(raw, img.size, img.mode)
        self.screen.blit(surface, (0, 0))
        pygame.display.flip()

    def close(self) -> None:
        """Clean up display."""
        if self.screen and self._pygame:
            self.screen.fill((255, 255, 255))
            self._pygame.display.flip()
            self.screen = None


class SlateDisplay(Display):
    """Slate display: auto-detects real Inky Impression or falls back to mock."""

    def __init__(self):
        if HAS_INKY:
            self.inky = InkyAuto()
            self.inky.set_border(self.inky.WHITE)
            self.mock = None
        else:
            self.inky = None
            self.mock = InkyMock()

    @property
    def on_key(self):
        """Proxy on_key to mock (only used in sim)."""
        return self.mock.on_key if self.mock else None

    @on_key.setter
    def on_key(self, value):
        if self.mock:
            self.mock.on_key = value

    def render(self, state: StateSnapshot) -> None:
        """Legacy render — no-op. Use render_image()."""
        pass

    def render_image(self, img: Image.Image) -> None:
        """Show a PIL Image on the display."""
        if self.mock:
            self.mock.render_image(img)
            return

        # Real Inky Impression
        self.inky.set_image(img)
        self.inky.show()

    def close(self) -> None:
        """Clean up display."""
        if self.mock:
            self.mock.close()
