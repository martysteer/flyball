from shared.options import load_word_channels


def test_default_theme_loads_three_channels():
    opts = load_word_channels()
    assert set(opts) == {"subject", "context", "style"}
    assert opts["subject"][0] == "Private Eye"
    assert len(opts["subject"]) == 5


def test_other_theme():
    opts = load_word_channels("retro_nostalgic")
    assert opts["context"][0] == "1950s Suburb"
