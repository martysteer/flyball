"""SlateDisplay seam + InkyMock. Real Inky Impression driver lands in M4."""
from PIL import Image, ImageDraw, ImageFont

from shared.messages import CHANNELS

WIDTH, HEIGHT = 640, 400
STRIP_W = 72          # sideways left menu strip
RIBBON_H = 72         # bottom status ribbon


class SlateDisplay:
    """Display seam for the slow canvas."""

    def show(self, img):
        raise NotImplementedError


class InkyMock(SlateDisplay):
    """Sim: pop the PIL image in the OS viewer (Story Builder pattern)."""

    def show(self, img):
        img.show(title="Flyball Slate")


def _font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # older Pillow
        return ImageFont.load_default()


def render_slate(state):
    """state: conductor.state.Flyball. Returns 640x400 PIL image."""
    img = Image.new("RGB", (WIDTH, HEIGHT), "white")
    d = ImageDraw.Draw(img)

    # Left menu strip: 4 sideways labels next to the physical buttons
    block_h = HEIGHT // len(CHANNELS)
    for i, ch in enumerate(CHANNELS):
        y0 = i * block_h
        active = ch["id"] == state.active
        bg = tuple(ch["color"]) if active else "white"
        fg = "white" if active else "black"
        label = Image.new("RGB", (block_h, STRIP_W), bg)
        ld = ImageDraw.Draw(label)
        ld.text((8, STRIP_W // 2 - 10), f"[{ch['slate_btn']}] {ch['label']}",
                fill=fg, font=_font(18))
        img.paste(label.rotate(90, expand=True), (0, y0))
        d.rectangle([0, y0, STRIP_W, y0 + block_h - 1], outline="black")

    # Main area: placeholder until M2 brings generated images
    d.text((STRIP_W + 24, 140), "( no image yet - M2 )", fill="gray", font=_font(20))

    # Status ribbon: sentence + engine line
    ry = HEIGHT - RIBBON_H
    d.rectangle([STRIP_W, ry, WIDTH, HEIGHT], fill="black")
    sentence = state.sentence() or "(nothing committed)"
    d.text((STRIP_W + 12, ry + 10), sentence, fill="white", font=_font(20))
    e = state.engine_summary()
    loop = ">" if e["loop"] else "||"
    d.text((STRIP_W + 12, ry + 42),
           f"queue {e['queue_depth']}   loop {loop} {e['speed_s']}s   op {e['operator'].upper()}",
           fill="yellow", font=_font(16))
    return img
