"""Test display mocks."""

from shared.interfaces.display import StateSnapshot, Display
from controller.display import SparkMock


def test_spark_mock_renders_without_crash():
    """SparkMock renders state snapshot to terminal."""
    state = StateSnapshot(
        channel="subject",
        channel_color=(0, 200, 80),
        option_index=2,
        option_count=5,
        candidate="Detective",
        committed=True,
        mode="word",
    )

    mock = SparkMock()
    # Should not crash
    mock.render(state)
    mock.close()


def test_spark_mock_renders_engine_channel():
    """SparkMock renders engine settings."""
    state = StateSnapshot(
        channel="engine",
        channel_color=(200, 150, 0),
        option_index=0,
        option_count=1,
        candidate="LOOP",
        committed=False,
        mode="engine",
        engine={"loop": True, "speed_s": 8, "operator": "swap", "queue_depth": 0},
    )

    mock = SparkMock()
    mock.render(state)
    mock.close()


def test_spark_mock_scrolls_long_text():
    """SparkMock scrolls text longer than 17 chars."""
    state = StateSnapshot(
        channel="subject",
        channel_color=(0, 200, 80),
        option_index=0,
        option_count=1,
        candidate="A Very Long Detective Name That Should Scroll",
        committed=False,
        mode="word",
    )

    mock = SparkMock()
    # Render multiple times to show scrolling
    for i in range(5):
        mock.render(state)
    mock.close()
