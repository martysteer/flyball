"""Test message schema."""

import json
import pytest
from shared.messages import (
    HelloMessage,
    StateMessage,
    ButtonMessage,
    PingMessage,
    PongMessage,
    ToastMessage,
    PatchMessage,
)


def test_hello_message():
    """HelloMessage serializes to dict."""
    msg = HelloMessage(device="spark", fw="0.1.0")
    as_dict = msg.model_dump()
    assert as_dict["type"] == "hello"
    assert as_dict["device"] == "spark"
    assert as_dict["fw"] == "0.1.0"


def test_hello_message_from_json():
    """HelloMessage deserializes from dict."""
    data = {"type": "hello", "device": "spark", "fw": "0.1.0"}
    msg = HelloMessage(**data)
    assert msg.device == "spark"


def test_state_message():
    """StateMessage includes all state fields."""
    msg = StateMessage(
        channel="subject",
        channel_color=(0, 200, 80),
        option_index=2,
        option_count=5,
        candidate="Detective",
        committed=True,
        mode="word",
    )
    as_dict = msg.model_dump()
    assert as_dict["type"] == "state"
    assert as_dict["channel"] == "subject"
    assert as_dict["option_index"] == 2


def test_button_message():
    """ButtonMessage captures press/release/hold."""
    msg = ButtonMessage(btn="A", event="press")
    as_dict = msg.model_dump()
    assert as_dict["type"] == "button"
    assert as_dict["btn"] == "A"
    assert as_dict["event"] == "press"


def test_button_message_hold_with_ms():
    """ButtonMessage hold includes duration."""
    msg = ButtonMessage(btn="Y", event="hold", ms=800)
    as_dict = msg.model_dump(exclude_none=True)
    assert as_dict["ms"] == 800


def test_ping_pong():
    """Ping and Pong messages."""
    ping = PingMessage()
    assert ping.model_dump()["type"] == "ping"

    pong = PongMessage()
    assert pong.model_dump()["type"] == "pong"


def test_toast_message():
    """Toast message for brief Spark flash."""
    msg = ToastMessage(text="SENT", color=(255, 180, 0))
    as_dict = msg.model_dump()
    assert as_dict["type"] == "toast"
    assert as_dict["text"] == "SENT"


def test_patch_message():
    """Patch message for incremental updates."""
    msg = PatchMessage(candidate="Silent Dancer", option_index=3)
    as_dict = msg.model_dump(exclude_none=True)
    assert as_dict["type"] == "patch"
    assert "candidate" in as_dict
