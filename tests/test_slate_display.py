"""Test SlateDisplay hardware detection and InkyMock PIL Image flow."""

from PIL import Image
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


def test_has_inky_flag_exists():
    """Module exposes HAS_INKY flag."""
    from conductor import display
    assert hasattr(display, "HAS_INKY")
    assert isinstance(display.HAS_INKY, bool)


def test_inky_mock_render_image():
    """InkyMock.render_image accepts PIL Image without crash."""
    from conductor.display import InkyMock
    mock = InkyMock()
    img = Image.new("RGB", (640, 400), (128, 128, 128))
    mock.render_image(img)
    mock.close()


def test_slate_display_render_image():
    """SlateDisplay.render_image forwards to implementation."""
    from conductor.display import SlateDisplay, HAS_INKY
    if not HAS_INKY:
        d = SlateDisplay()
        img = Image.new("RGB", (640, 400), (200, 200, 200))
        d.render_image(img)
        d.close()
