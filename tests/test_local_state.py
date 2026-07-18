"""Tests for controller/state.py — Spark local exploration state."""

from controller.state import LocalState, CHANNEL_ORDER


def make_state():
    return LocalState()  # loads shared/data/word_blocks.json


def test_starts_on_subject_uncommitted():
    s = make_state()
    assert s.active == "subject"
    snap = s.snapshot()
    assert snap.channel == "subject"
    assert snap.committed is False
    assert snap.option_count > 0


def test_next_prev_wrap():
    s = make_state()
    n = len(s.options["subject"])
    for _ in range(n):
        s.next_option()
    assert s.index["subject"] == 0
    s.prev_option()
    assert s.index["subject"] == n - 1


def test_jump_wraps():
    s = make_state()
    n = len(s.options["subject"])
    s.jump(-5)
    assert s.index["subject"] == (n - 5) % n


def test_commit_and_uncommit():
    s = make_state()
    word = s.snapshot().candidate
    s.commit()
    assert s.committed_word["subject"] == word
    assert s.snapshot().committed is True
    s.uncommit()
    assert s.committed_word["subject"] is None
    assert s.snapshot().committed is False


def test_channel_cycle_wraps():
    s = make_state()
    for expected in ["context", "style", "engine", "subject"]:
        s.next_channel()
        assert s.active == expected


def test_engine_snapshot():
    s = make_state()
    while s.active != "engine":
        s.next_channel()
    snap = s.snapshot()
    assert snap.mode == "engine"
    assert snap.candidate == "SEND"
    assert snap.channel_color == (200, 150, 0)


def test_randomize_stays_in_range():
    s = make_state()
    for _ in range(20):
        s.randomize()
        assert 0 <= s.index["subject"] < len(s.options["subject"])


def test_send_payload_shape():
    s = make_state()
    s.commit()
    payload = s.send_payload()
    assert payload["channels"]["subject"] == s.committed_word["subject"]
    assert payload["channels"]["context"] is None
    assert payload["engine"]["operator"] == "swap"


def test_engine_op_setting_cycles_operator():
    s = make_state()
    while s.active != "engine":
        s.next_channel()
    s.cycle_engine_setting()           # setting: send -> op
    assert s.snapshot().candidate == "OP SWAP"
    s.next_option()                    # cycles operator value
    assert s.snapshot().candidate == "OP LANG"
    assert s.send_payload()["engine"]["operator"] == "lang"
