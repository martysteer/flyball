"""Tests for controller/longpress.py — fake-clock timing."""

from controller.longpress import LongPressDetector


def test_short_press():
    d = LongPressDetector(threshold=0.6)
    d.press("A", now=0.0)
    assert d.poll(now=0.3) == []
    assert d.release("A", now=0.3) == "short"


def test_long_fires_while_held():
    d = LongPressDetector(threshold=0.6)
    d.press("Y", now=0.0)
    assert d.poll(now=0.5) == []
    assert d.poll(now=0.61) == ["Y"]
    assert d.poll(now=0.7) == []          # fires once
    assert d.release("Y", now=1.0) is None  # no short after long


def test_release_without_press_is_noop():
    d = LongPressDetector(threshold=0.6)
    assert d.release("X", now=1.0) is None


def test_hold_fraction():
    d = LongPressDetector(threshold=0.6)
    d.press("B", now=0.0)
    assert d.hold_fraction("B", now=0.3) == 0.5
    assert d.hold_fraction("B", now=0.9) == 1.0
    assert d.hold_fraction("A", now=0.3) == 0.0
