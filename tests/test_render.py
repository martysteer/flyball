"""Tests for controller/render.py — pure (state, tick) → frame."""

from controller.render import render_frame, Effects, WIDTH, HEIGHT
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


def test_three_state_pip_brightness():
    # Committed at index 2, cursor at index 4 → three brightness levels
    state = make_state(option_index=4, option_count=7, committed_index=2)
    frame = render_frame(state, tick=0)
    # Brightest at cursor (index 4)
    assert frame[1][4] == (0, 200, 80)
    # Bright at committed (index 2)
    assert frame[1][2] == (0, 200 // 2, 80 // 2)
    # Dim elsewhere (index 0, 1, 3, 5, 6)
    assert frame[1][0] == (0, 200 // 8, 80 // 8)
    assert frame[1][1] == (0, 200 // 8, 80 // 8)
    assert frame[1][3] == (0, 200 // 8, 80 // 8)


def test_commit_flash_fills_matrix():
    e = Effects(flash_until=2, flash_color=(0, 200, 80))
    frame = render_frame(make_state(), tick=0, effects=e)
    assert frame[3][8] == (0, 200, 80)
    assert frame[0][0] == (0, 200, 80)


def test_flash_expires():
    e = Effects(flash_until=2, flash_color=(0, 200, 80))
    frame = render_frame(make_state(candidate="HI"), tick=2, effects=e)
    assert frame[2][3] == (0, 0, 0)  # normal render resumed
