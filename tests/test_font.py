"""Tests for shared/font.py — variable-width column font."""

from shared.font import FONT, render_columns, text_width


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
