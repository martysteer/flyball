"""Slate display: real Inky Impression + pygame mock."""

import platform
from dataclasses import dataclass, field
from typing import Optional

from shared.interfaces.display import Display, StateSnapshot

IS_SIMULATION = platform.system() != "Linux"

if IS_SIMULATION:
    import pygame


@dataclass
class InkyMock(Display):
    """Mock Slate display: pygame window showing Inky Impression layout."""

    width: int = 640
    height: int = 400
    screen: Optional[object] = field(default=None, init=False)
    font_large: Optional[object] = field(default=None, init=False)
    font_small: Optional[object] = field(default=None, init=False)
    font_tiny: Optional[object] = field(default=None, init=False)
    on_key: Optional[object] = None  # Callback: (char: str) -> None

    # Colors
    COLOR_WHITE = (255, 255, 255)
    COLOR_BLACK = (0, 0, 0)
    COLOR_GRAY_LIGHT = (240, 240, 240)
    COLOR_GRAY_DARK = (64, 64, 64)
    COLOR_GRAY_MED = (128, 128, 128)

    # Channel colors
    CHANNEL_COLORS = {
        "subject": (0, 200, 80),    # green
        "context": (0, 100, 200),   # blue
        "style": (200, 0, 150),     # magenta
        "engine": (200, 150, 0),    # amber
    }

    CHANNEL_LABELS = {
        "subject": ("A", "Subject"),
        "context": ("B", "Context"),
        "style": ("C", "Style"),
        "engine": ("D", "Engine"),
    }

    def __post_init__(self):
        """Initialize pygame window."""
        if IS_SIMULATION:
            pygame.init()
            # WINDOWSTAYSONTOP for testing convenience (pygame 2.0+)
            try:
                self.screen = pygame.display.set_mode(
                    (self.width, self.height),
                    pygame.WINDOWSTAYSONTOP
                )
            except:
                # Fallback if flag not supported
                self.screen = pygame.display.set_mode((self.width, self.height))
            pygame.display.set_caption("Flyball Slate Mock (Inky Impression)")

            # Load fonts
            try:
                self.font_large = pygame.font.SysFont("helvetica,arial", 24)
                self.font_small = pygame.font.SysFont("helvetica,arial", 14)
                self.font_tiny = pygame.font.SysFont("helvetica,arial", 10)
            except:
                # Fallback to default pygame font
                self.font_large = pygame.font.Font(None, 28)
                self.font_small = pygame.font.Font(None, 16)
                self.font_tiny = pygame.font.Font(None, 12)

    def render(self, state: StateSnapshot) -> None:
        """Render state to pygame window."""
        if not self.screen:
            return

        try:
            events = pygame.event.get()
        except pygame.error:
            return

        # Process pygame events (prevent window freeze + handle keyboard)
        for event in events:
            if event.type == pygame.QUIT:
                if self.on_key:
                    self.on_key('q')
                return
            elif event.type == pygame.KEYDOWN:
                # Map keys to Slate buttons (a/b/c/d)
                key_map = {
                    pygame.K_a: 'a',
                    pygame.K_b: 'b',
                    pygame.K_c: 'c',
                    pygame.K_d: 'd',
                    pygame.K_q: 'q',  # Quit
                }
                char = key_map.get(event.key)
                if char and self.on_key:
                    self.on_key(char)

        # Clear to white
        self.screen.fill(self.COLOR_WHITE)

        # Draw components
        self._draw_menu_strip(state)
        self._draw_main_area(state)
        self._draw_status_ribbon(state)

        # Update display
        pygame.display.flip()

    def _draw_menu_strip(self, state: StateSnapshot) -> None:
        """Draw left menu strip with channel buttons."""
        menu_width = 80
        channel_height = self.height // 4

        channels = ["subject", "context", "style", "engine"]

        for i, channel_id in enumerate(channels):
            y = i * channel_height
            color = self.CHANNEL_COLORS[channel_id]
            btn_letter, label = self.CHANNEL_LABELS[channel_id]

            is_active = (state.channel == channel_id)

            # Draw background/border
            rect = pygame.Rect(0, y, menu_width, channel_height)
            if is_active:
                # Filled rect for active channel
                pygame.draw.rect(self.screen, color, rect)
                text_color = self.COLOR_WHITE
            else:
                # Outline for inactive channel
                pygame.draw.rect(self.screen, color, rect, 2)
                text_color = color

            # Draw button letter in brackets [A]
            btn_text = f"[{btn_letter}]"
            self._render_text(btn_text, 10, y + 10, self.font_small, text_color)

            # Draw label vertically (char by char)
            char_y = y + 35
            for char in label:
                char_surf = self.font_tiny.render(char, True, text_color)
                char_rect = char_surf.get_rect()
                char_rect.left = 10
                char_rect.top = char_y
                self.screen.blit(char_surf, char_rect)
                char_y += 12

    def _draw_main_area(self, state: StateSnapshot) -> None:
        """Draw main image area (placeholder for M1)."""
        main_x = 90
        main_y = 10
        main_width = 540
        main_height = 320

        # Background
        main_rect = pygame.Rect(main_x, main_y, main_width, main_height)
        pygame.draw.rect(self.screen, self.COLOR_GRAY_LIGHT, main_rect)

        # Border
        pygame.draw.rect(self.screen, self.COLOR_BLACK, main_rect, 2)

        # Placeholder text
        title = "Generated Image"
        self._render_text(title, main_x + main_width//2, main_y + 50,
                         self.font_large, self.COLOR_GRAY_DARK, align='center')

        # Current candidate
        candidate_text = f"Candidate: {state.candidate}"
        self._render_text(candidate_text, main_x + main_width//2, main_y + 100,
                         self.font_small, self.COLOR_GRAY_DARK, align='center')

    def _draw_status_ribbon(self, state: StateSnapshot) -> None:
        """Draw bottom status ribbon with sentence and engine info."""
        ribbon_y = 340
        ribbon_height = 60

        # Top border
        pygame.draw.line(self.screen, self.COLOR_GRAY_MED,
                        (0, ribbon_y), (self.width, ribbon_y), 1)

        # Render sentence from conductor's state machine
        # For M1, just show the candidate; conductor will implement render_sentence()
        sentence = self._build_sentence(state)

        sentence_text = f"Sentence: {sentence}"
        self._render_text(sentence_text, 95, ribbon_y + 15,
                         self.font_small, self.COLOR_BLACK)

        # Engine status (if in engine mode or engine data available)
        if state.engine:
            loop_icon = "▶" if state.engine.get("loop") else "▫"
            speed = state.engine.get("speed_s", 8)
            operator = state.engine.get("operator", "swap").upper()
            queue_depth = state.engine.get("queue_depth", 0)

            engine_text = f"Loop: {loop_icon} {speed}s │ Op: {operator} │ Queue: {queue_depth}"
            self._render_text(engine_text, 95, ribbon_y + 40,
                             self.font_small, self.COLOR_GRAY_DARK)

    def _build_sentence(self, state: StateSnapshot) -> str:
        """Build sentence from state (simplified for M1)."""
        # For now, just show the current candidate
        # In M2, conductor will track committed options per channel
        if state.candidate:
            return state.candidate
        return "[empty]"

    def _render_text(self, text: str, x: int, y: int, font: object,
                    color: tuple, align: str = 'left') -> None:
        """Render text at position with alignment."""
        if not text:
            return

        surface = font.render(text, True, color)
        rect = surface.get_rect()

        if align == 'center':
            rect.centerx = x
            rect.top = y
        elif align == 'right':
            rect.right = x
            rect.top = y
        else:  # left
            rect.left = x
            rect.top = y

        self.screen.blit(surface, rect)

    def close(self) -> None:
        """Clean up display."""
        if self.screen:
            self.screen.fill(self.COLOR_WHITE)
            pygame.display.flip()
            self.screen = None


class SlateDisplay(Display):
    """Real Slate display (Inky Impression on e-paper)."""

    def __init__(self):
        """Initialize display."""
        if IS_SIMULATION:
            # Use pygame mock
            self.impl = InkyMock()
        else:
            # TODO: Use real inky library (M4)
            # from inky.inky_uc8159 import Inky
            # self.impl = ...
            pass

    def render(self, state: StateSnapshot) -> None:
        """Render to display."""
        if hasattr(self, 'impl'):
            self.impl.render(state)

    def close(self) -> None:
        """Clean up."""
        if hasattr(self, 'impl'):
            self.impl.close()
