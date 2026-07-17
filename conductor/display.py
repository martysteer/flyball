"""Slate display: real Inky Impression + mock (PIL image)."""

import os
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path
import platform
import tkinter as tk
from PIL import Image, ImageDraw, ImageFont, ImageTk

from shared.interfaces.display import Display, StateSnapshot

IS_SIMULATION = platform.system() != "Linux"


@dataclass
class InkyMock(Display):
    """Mock Slate display: renders to PIL image in Tkinter window."""

    width: int = 640
    height: int = 400
    image: Optional[Image.Image] = field(default=None, init=False)
    window: Optional[tk.Tk] = field(default=None, init=False)
    photo: Optional[ImageTk.PhotoImage] = field(default=None, init=False)
    label: Optional[tk.Label] = field(default=None, init=False)

    def render(self, state: StateSnapshot) -> None:
        """Render state to PIL image."""
        # Create new image (white background)
        self.image = Image.new("RGB", (self.width, self.height), (255, 255, 255))
        draw = ImageDraw.Draw(self.image)

        # Try to load a font; fall back to default
        try:
            font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 12)
            font_large = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
        except:
            font_small = ImageFont.load_default()
            font_large = ImageFont.load_default()

        # Left menu strip: channel labels (sideways)
        menu_width = 80
        channels = [
            ("A", "Subject", (0, 200, 80)),
            ("B", "Context", (0, 100, 200)),
            ("C", "Style", (200, 0, 150)),
            ("D", "Engine", (200, 150, 0)),
        ]

        channel_height = self.height // 4
        for i, (btn, label, color) in enumerate(channels):
            y = i * channel_height
            is_active = (state.channel == label.lower())

            if is_active:
                # Highlight active channel
                draw.rectangle((0, y, menu_width, y + channel_height), fill=color)
                draw.text((10, y + 10), f"[{btn}]", fill=(255, 255, 255), font=font_small)
                draw.text((10, y + 30), label, fill=(255, 255, 255), font=font_small)
            else:
                # Inactive
                draw.rectangle((0, y, menu_width, y + channel_height), outline=color)
                draw.text((10, y + 10), f"{btn}", fill=color, font=font_small)
                draw.text((10, y + 30), label, fill=color, font=font_small)

        # Main area: placeholder for generated image
        main_x = menu_width + 10
        main_y = 10
        main_width = self.width - main_x - 10
        main_height = self.height - main_y - 60

        # Draw placeholder rectangle
        draw.rectangle(
            (main_x, main_y, main_x + main_width, main_y + main_height),
            outline=(0, 0, 0),
        )
        draw.text(
            (main_x + 10, main_y + 10),
            "Generated Image",
            fill=(0, 0, 0),
            font=font_large,
        )
        draw.text(
            (main_x + 10, main_y + 50),
            f"Candidate: {state.candidate}",
            fill=(0, 0, 0),
            font=font_small,
        )

        # Bottom ribbon: sentence + queue + loop status
        ribbon_y = self.height - 50
        sentence = state.candidate  # In real impl, would be full sentence
        draw.text(
            (main_x + 10, ribbon_y),
            f"Sentence: {sentence}",
            fill=(0, 0, 0),
            font=font_small,
        )

        if state.engine:
            engine_str = f"Loop: {'ON' if state.engine.get('loop') else 'OFF'} | Op: {state.engine.get('operator', 'swap')} | Speed: {state.engine.get('speed_s', 8)}s"
            draw.text(
                (main_x + 10, ribbon_y + 25),
                engine_str,
                fill=(0, 0, 0),
                font=font_small,
            )

        # Display image in Tkinter window
        if IS_SIMULATION:
            if self.window is None:
                # Create window once
                self.window = tk.Tk()
                self.window.title("Flyball Slate Mock (Inky Impression)")
                self.label = tk.Label(self.window)
                self.label.pack()

            # Update image
            self.photo = ImageTk.PhotoImage(self.image)
            self.label.config(image=self.photo)
            self.window.update()

    def close(self) -> None:
        """Clean up."""
        if self.window:
            self.window.destroy()


class SlateDisplay(Display):
    """Real Slate display (Inky Impression on e-paper)."""

    def render(self, state: StateSnapshot) -> None:
        """Render to Inky Impression (stub for M1)."""
        if IS_SIMULATION:
            # Fall back to mock
            mock = InkyMock()
            mock.render(state)
        else:
            # TODO: implement real Inky rendering
            pass

    def close(self) -> None:
        """Clean up e-paper."""
        pass
