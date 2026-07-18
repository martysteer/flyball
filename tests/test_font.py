"""Tests for shared/font.py — variable-width column font."""

from shared.font import FONT, render_columns, text_width, bounce_offset


def test_i_is_single_full_column():
    # 'I' = 1 column, all 5 bits set (bit 0 = top)
    assert FONT["I"] == [0b11111]


def test_h_columns():
    # H rows: 101/101/111/101/101 → cols [31, 4, 31]
    assert FONT["H"] == [0b11111, 0b00100, 0b11111]


def test_render_columns_concatenates_with_gap():
    # H (3 cols) + 1 blank + I (1 col) = 5 cols
    assert render_columns("HI") == [0b11111, 0b00100, 0b11111, 0, 0b11111]


def test_text_width():
    assert text_width("HI") == 5
    assert text_width("") == 0


def test_lowercase_maps_to_uppercase():
    assert render_columns("hi") == render_columns("HI")


def test_unknown_char_skipped():
    assert render_columns("H~I") == render_columns("HI")


def test_full_charset_present():
    for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -'[]":
        assert ch in FONT, f"missing glyph: {ch}"


def test_all_glyphs_are_5_rows_max():
    for ch, cols in FONT.items():
        for col in cols:
            assert 0 <= col < 32, f"{ch} column exceeds 5 bits"


def test_bounce_static_when_text_fits():
    assert bounce_offset(17, 17, tick=0) == 0
    assert bounce_offset(10, 17, tick=999) == 0


def test_bounce_scrolls_to_max_then_back():
    # 20 cols in 17 window → max offset 3; ticks_per_col=5, no dwell
    assert bounce_offset(20, 17, tick=0, ticks_per_col=5, dwell_ticks=0) == 0
    assert bounce_offset(20, 17, tick=5, ticks_per_col=5, dwell_ticks=0) == 1
    assert bounce_offset(20, 17, tick=15, ticks_per_col=5, dwell_ticks=0) == 3   # end visible
    assert bounce_offset(20, 17, tick=20, ticks_per_col=5, dwell_ticks=0) == 2   # reversing
    assert bounce_offset(20, 17, tick=30, ticks_per_col=5, dwell_ticks=0) == 0   # back at start


def test_bounce_never_exceeds_bounds():
    for tick in range(200):
        off = bounce_offset(40, 17, tick, dwell_ticks=0)
        assert 0 <= off <= 23


def test_render_columns_with_padding():
    # "HI" = 5 cols; padding=3 → [0,0,0] + cols + [0,0,0] = 11 cols
    cols = render_columns("HI", padding=3)
    assert cols[:3] == [0, 0, 0]
    assert cols[-3:] == [0, 0, 0]
    assert len(cols) == 5 + 3 + 3


def test_bounce_dwells_at_start():
    # Default dwell_ticks=30 → offset stays 0 for first 30 ticks
    assert bounce_offset(30, 17, tick=0) == 0
    assert bounce_offset(30, 17, tick=29) == 0
    # At tick=30, dwell ends; step=0, starts moving
    assert bounce_offset(30, 17, tick=32) == 1  # (32-30)//2 = 1
