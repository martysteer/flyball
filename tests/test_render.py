"""Tests for controller/render.py — pure (state, tick) → frame."""

from controller.render import render_frame, WIDTH, HEIGHT
from shared.interfaces.display import StateSnapshot


def make_state(**kw):
    defaults = dict(
        channel="subject",
        channel_color=(0, 200, 80),
        option_index=1,
        option_count=5,
        candidate="HI",
        committed=False,
        mode="word",
        engine=None,
    )
    defaults.update(kw)
    return StateSnapshot(**defaults)


def test_frame_dimensions():
    frame = render_frame(make_state(), tick=0)
    assert len(frame) == HEIGHT
    assert all(len(row) == WIDTH for row in frame)


def test_row0_dim_bar_when_uncommitted():
    frame = render_frame(make_state(committed=False), tick=0)
    assert frame[0][0] == (0, 200 // 4, 80 // 4)


def test_row0_solid_bar_when_committed():
    frame = render_frame(make_state(committed=True), tick=0)
    assert frame[0][0] == (0, 200, 80)


def test_row1_pip_bright_at_index():
    frame = render_frame(make_state(option_index=1, option_count=5), tick=0)
    assert frame[1][1] == (0, 200, 80)
    assert frame[1][0] == (0, 200 // 8, 80 // 8)


def test_text_pixels_short_word_static():
    # padding=2, so 'H' col 0 → frame col 2; H first col has top bit set
    frame = render_frame(make_state(candidate="HI"), tick=0)
    assert frame[2][2] == (0, 200, 80)  # H's first column after padding
    assert frame[2][0] == (0, 0, 0)    # padding column


def test_long_word_scrolls_with_tick():
    state = make_state(candidate="DETECTIVE STORY")
    f0 = render_frame(state, tick=0)  # dwelling
    f1 = render_frame(state, tick=40)  # past dwell, scrolling
    assert f0 != f1


def test_engine_mode_shows_candidate_text():
    state = make_state(mode="engine", channel="engine",
                       channel_color=(200, 150, 0), candidate="SEND",
                       engine={"operator": "swap"})
    frame = render_frame(state, tick=0)
    # padding=2, 'S' first col at frame col 2; 'S' col 0: bit1,bit4 set → rows 3,4
    assert frame[3][2] == (200, 150, 0)
