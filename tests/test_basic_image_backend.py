"""Test BasicImageBackend PIL compositing."""

from PIL import Image
from shared.basic_image_backend import BasicImageBackend
from shared.interfaces.display import StateSnapshot


def _make_state(**overrides) -> StateSnapshot:
    defaults = dict(
        channel="subject",
        channel_color=(0, 200, 80),
        option_index=0,
        option_count=5,
        candidate="hello",
        committed=False,
        mode="word",
        engine=None,
    )
    defaults.update(overrides)
    return StateSnapshot(**defaults)


def test_render_frame_returns_pil_image():
    backend = BasicImageBackend()
    img = backend.render_frame(_make_state())
    assert isinstance(img, Image.Image)
    assert img.size == (640, 400)


def test_render_frame_not_all_white():
    """Composited image should have some non-white pixels (menu strip, text)."""
    backend = BasicImageBackend()
    img = backend.render_frame(_make_state())
    pixels = list(img.getdata())
    white_count = sum(1 for p in pixels if p == (255, 255, 255))
    assert white_count < len(pixels), "Image is all white — compositing did nothing"


def test_active_channel_changes_output():
    """Different active channels should produce different images."""
    backend = BasicImageBackend()
    img_subject = backend.render_frame(_make_state(channel="subject"))
    img_engine = backend.render_frame(_make_state(channel="engine"))
    assert img_subject.tobytes() != img_engine.tobytes()


def test_engine_state_renders():
    """Engine state with metadata should render without error."""
    backend = BasicImageBackend()
    img = backend.render_frame(_make_state(
        channel="engine",
        mode="engine",
        engine={"loop": True, "speed_s": 8, "operator": "swap", "queue_depth": 2},
    ))
    assert isinstance(img, Image.Image)
