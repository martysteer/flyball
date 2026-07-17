"""Test state machine: channels, options, stack."""

import json
from pathlib import Path
import pytest
from conductor.state_machine import (
    Channel,
    ChannelRegistry,
    StateSnapshot,
)


@pytest.fixture
def word_blocks_path():
    """Path to word_blocks.json."""
    return Path(__file__).parent.parent / "shared" / "data" / "word_blocks.json"


def test_channel_registry_loads_from_json(word_blocks_path):
    """ChannelRegistry loads channels from word_blocks.json."""
    registry = ChannelRegistry(word_blocks_path)
    assert "subject" in registry.channels
    assert "context" in registry.channels
    assert "style" in registry.channels
    assert "engine" in registry.channels


def test_channel_has_options(word_blocks_path):
    """Channel loads options from theme."""
    registry = ChannelRegistry(word_blocks_path)
    subject_ch = registry.channels["subject"]
    # Default theme is "cinematic_noir"
    assert len(subject_ch.options) > 0
    assert "Private Eye" in subject_ch.options or "Detective" in subject_ch.options


def test_channel_next_cycles_forward(word_blocks_path):
    """Calling next_option increments index."""
    registry = ChannelRegistry(word_blocks_path)
    ch = registry.channels["subject"]
    initial_idx = ch.option_index
    ch.next_option()
    assert ch.option_index == (initial_idx + 1) % len(ch.options)


def test_channel_prev_cycles_backward(word_blocks_path):
    """Calling prev_option decrements index."""
    registry = ChannelRegistry(word_blocks_path)
    ch = registry.channels["subject"]
    initial_idx = ch.option_index
    ch.prev_option()
    assert ch.option_index == (initial_idx - 1) % len(ch.options)


def test_channel_commit_toggles_committed(word_blocks_path):
    """Commit toggles the committed flag."""
    registry = ChannelRegistry(word_blocks_path)
    ch = registry.channels["subject"]
    ch.committed = False
    ch.commit()
    assert ch.committed is True


def test_state_snapshot_serializes(word_blocks_path):
    """StateSnapshot can be serialized to dict for JSON."""
    registry = ChannelRegistry(word_blocks_path)
    snapshot = StateSnapshot.from_registry(registry, mode="word")
    as_dict = snapshot.to_dict()
    assert "channel" in as_dict
    assert "option_index" in as_dict
    assert "candidate" in as_dict


def test_render_sentence(word_blocks_path):
    """Render sentence from committed options."""
    registry = ChannelRegistry(word_blocks_path)
    # Commit one of each word channel
    registry.channels["subject"].commit()
    registry.channels["context"].commit()
    registry.channels["style"].commit()

    sentence = registry.render_sentence()
    # Should be "Subject, Context, Style"
    parts = sentence.split(" · ")
    assert len(parts) == 3


def test_change_channel(word_blocks_path):
    """Changing active channel updates registry."""
    registry = ChannelRegistry(word_blocks_path)
    registry.set_active_channel("context")
    assert registry.active_channel == "context"


def test_engine_channel_holds_loop_settings(word_blocks_path):
    """Engine channel has loop, speed, operator settings."""
    registry = ChannelRegistry(word_blocks_path)
    engine_ch = registry.channels["engine"]
    assert hasattr(engine_ch, "loop")
    assert hasattr(engine_ch, "speed_s")
    assert hasattr(engine_ch, "operator")
