"""Test SparkDisplay hardware detection and fallback."""

from unittest.mock import patch
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


def test_has_unicorn_flag_exists():
    """Module exposes HAS_UNICORN flag."""
    from controller import display
    assert hasattr(display, "HAS_UNICORN")
    assert isinstance(display.HAS_UNICORN, bool)


def test_spark_display_falls_back_to_mock():
    """On Mac (no unicornhatmini lib), SparkDisplay uses SparkMock."""
    from controller.display import SparkDisplay, SparkMock, HAS_UNICORN
    if not HAS_UNICORN:
        d = SparkDisplay()
        assert isinstance(d.mock, SparkMock)


def test_spark_mock_render_no_crash():
    """SparkMock.push() doesn't crash."""
    from controller.display import SparkMock
    from controller.render import render_frame
    mock = SparkMock()
    frame = render_frame(_make_state(), tick=0)
    mock.push(frame)
