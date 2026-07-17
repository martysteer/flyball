"""BasicImageBackend: PIL compositing for Slate display (placeholder for M2 image gen)."""

from PIL import Image, ImageDraw, ImageFont

from shared.interfaces.display import StateSnapshot
from shared.interfaces.image_backend import ImageBackend


# Channel display metadata
CHANNEL_COLORS = {
    "subject": (0, 200, 80),
    "context": (0, 100, 200),
    "style": (200, 0, 150),
    "engine": (200, 150, 0),
}

CHANNEL_LABELS = {
    "subject": ("A", "Subject"),
    "context": ("B", "Context"),
    "style": ("C", "Style"),
    "engine": ("D", "Engine"),
}


class BasicImageBackend(ImageBackend):
    """Stub image backend: PIL compositing with placeholder main area."""

    def __init__(self):
        self.width = 640
        self.height = 400
        # Try to load a truetype font, fall back to default
        try:
            self.font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
            self.font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
            self.font_tiny = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
        except (IOError, OSError):
            self.font_large = ImageFont.load_default()
            self.font_small = ImageFont.load_default()
            self.font_tiny = ImageFont.load_default()

    async def generate(self, prompt: str) -> Image.Image:
        """Not used in basic backend. Returns blank image."""
        return Image.new("RGB", (self.width, self.height), (255, 255, 255))

    def render_frame(self, state: StateSnapshot) -> Image.Image:
        """Render full Slate frame: menu strip + main area + status ribbon."""
        img = Image.new("RGB", (self.width, self.height), (255, 255, 255))
        draw = ImageDraw.Draw(img)

        self._draw_menu_strip(draw, state)
        self._draw_main_area(draw, state)
        self._draw_status_ribbon(draw, state)

        return img

    def _draw_menu_strip(self, draw: ImageDraw.Draw, state: StateSnapshot) -> None:
        """Draw left menu strip with channel buttons."""
        menu_width = 80
        channel_height = self.height // 4
        channels = ["subject", "context", "style", "engine"]

        for i, channel_id in enumerate(channels):
            y = i * channel_height
            color = CHANNEL_COLORS[channel_id]
            btn_letter, label = CHANNEL_LABELS[channel_id]
            is_active = (state.channel == channel_id)

            rect = [0, y, menu_width, y + channel_height]
            if is_active:
                draw.rectangle(rect, fill=color)
                text_color = (255, 255, 255)
            else:
                draw.rectangle(rect, outline=color, width=2)
                text_color = color

            # Button letter
            draw.text((10, y + 10), f"[{btn_letter}]", fill=text_color, font=self.font_small)

            # Label (vertical, char by char)
            char_y = y + 35
            for char in label:
                draw.text((10, char_y), char, fill=text_color, font=self.font_tiny)
                char_y += 12

    def _draw_main_area(self, draw: ImageDraw.Draw, state: StateSnapshot) -> None:
        """Draw main image area (placeholder for M2)."""
        main_x = 90
        main_y = 10
        main_w = 540
        main_h = 320

        # Background
        draw.rectangle([main_x, main_y, main_x + main_w, main_y + main_h],
                       fill=(240, 240, 240), outline=(0, 0, 0), width=2)

        # Placeholder text
        draw.text((main_x + main_w // 2, main_y + 50), "Generated Image",
                  fill=(64, 64, 64), font=self.font_large, anchor="mt")

        # Current candidate
        draw.text((main_x + main_w // 2, main_y + 100),
                  f"Candidate: {state.candidate}",
                  fill=(64, 64, 64), font=self.font_small, anchor="mt")

    def _draw_status_ribbon(self, draw: ImageDraw.Draw, state: StateSnapshot) -> None:
        """Draw bottom status ribbon."""
        ribbon_y = 340

        # Top border
        draw.line([(0, ribbon_y), (self.width, ribbon_y)], fill=(128, 128, 128), width=1)

        # Sentence
        sentence = state.candidate if state.candidate else "[empty]"
        draw.text((95, ribbon_y + 15), f"Sentence: {sentence}",
                  fill=(0, 0, 0), font=self.font_small)

        # Engine status
        if state.engine:
            loop_icon = ">" if state.engine.get("loop") else "-"
            speed = state.engine.get("speed_s", 8)
            operator = state.engine.get("operator", "swap").upper()
            queue_depth = state.engine.get("queue_depth", 0)
            engine_text = f"Loop: {loop_icon} {speed}s | Op: {operator} | Queue: {queue_depth}"
            draw.text((95, ribbon_y + 40), engine_text,
                      fill=(64, 64, 64), font=self.font_small)
