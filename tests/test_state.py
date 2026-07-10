from conductor.state import ENGINE_SETTINGS, Flyball
from shared.options import load_word_channels


def make():
    return Flyball(load_word_channels("cinematic_noir"))


def test_initial_state():
    fb = make()
    msg = fb.state_msg()
    assert msg["type"] == "state"
    assert msg["channel"] == "subject"
    assert msg["candidate"] == "Private Eye"
    assert msg["option_index"] == 0
    assert msg["option_count"] == 5
    assert msg["committed"] is False
    assert msg["mode"] == "word"
    assert msg["engine"]["loop"] is False


def test_next_prev_wrap():
    fb = make()
    fb.spark_button("B")
    assert fb.state_msg()["candidate"] == "Silent Dancer"
    fb.spark_button("A")
    fb.spark_button("A")
    assert fb.state_msg()["candidate"] == "Detective"  # wrapped to last
    assert fb.state_msg()["option_index"] == 4


def test_coarse_jump():
    fb = make()
    fb.spark_button("Y")  # +5 over a 5-list wraps to same index
    assert fb.state_msg()["option_index"] == 0


def test_commit_builds_sentence():
    fb = make()
    fb.spark_button("B")          # Silent Dancer
    assert fb.spark_button("X") == "commit"
    assert fb.state_msg()["committed"] is True
    fb.slate_button("B")          # switch to context
    fb.spark_button("X")          # commit Foggy Alley
    assert fb.sentence() == "Silent Dancer · Foggy Alley"


def test_channel_switch_preserves_index():
    fb = make()
    fb.spark_button("B")
    fb.slate_button("C")
    assert fb.state_msg()["channel"] == "style"
    fb.slate_button("A")
    assert fb.state_msg()["option_index"] == 1  # subject index kept


def test_slate_button_returns_changed():
    fb = make()
    assert fb.slate_button("A") is False  # already subject
    assert fb.slate_button("D") is True


def test_engine_mode():
    fb = make()
    fb.slate_button("D")
    msg = fb.state_msg()
    assert msg["mode"] == "engine"
    assert msg["channel"] == "engine"
    assert "SWAP" in msg["candidate"]
    fb.spark_button("B")  # next operator
    assert "LTR" in fb.state_msg()["candidate"]
    fb.spark_button("Y")  # focus -> speed
    assert fb.state_msg()["candidate"] == "SPD 4"


def test_engine_loop_toggle_reflected_in_engine_summary():
    fb = make()
    fb.slate_button("D")
    fb.spark_button("Y")  # speed
    fb.spark_button("Y")  # loop
    fb.spark_button("B")  # off -> on
    assert fb.state_msg()["engine"]["loop"] is True


def test_engine_settings_order():
    assert ENGINE_SETTINGS == ["operator", "speed", "loop", "queue"]
