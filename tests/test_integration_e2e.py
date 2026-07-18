"""End-to-end integration: Conductor server + Controller client + local state."""

import asyncio
import pytest
from pathlib import Path

from conductor.conductor import Conductor
from controller.controller import Controller


@pytest.fixture
def word_blocks_path():
    return Path(__file__).parent.parent / "shared" / "data" / "word_blocks.json"


def short_press(controller, btn):
    """Simulate a short press (press + release)."""
    controller._on_button_event(btn, "press")
    controller._on_button_event(btn, "release")


@pytest.mark.asyncio
async def test_full_two_handed_flow(word_blocks_path):
    """End-to-end: Conductor + Controller + local exploration state."""

    # Create Conductor
    conductor = Conductor(word_blocks_path)

    # Start Conductor server
    server_task = asyncio.create_task(conductor.start("localhost", 19765))
    await asyncio.sleep(0.2)  # Let server start

    # Create Controller
    controller = Controller()

    # Connect and start
    await controller.connect("localhost", 19765)
    await asyncio.sleep(0.3)  # Let connection settle

    # Controller owns local state — starts on subject, uncommitted
    assert controller.local.active == "subject"
    snap = controller.local.snapshot()
    assert snap.channel == "subject"
    assert snap.committed is False

    # Short press: next option (no network traffic)
    short_press(controller, "X")
    assert controller.local.index["subject"] == 1

    # Short press: commit
    short_press(controller, "B")
    assert controller.local.snapshot().committed is True

    # Channel cycle
    short_press(controller, "Y")
    assert controller.local.active == "context"

    # Clean up
    await controller.shutdown()
    await conductor.shutdown()
