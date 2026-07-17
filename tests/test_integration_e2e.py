"""End-to-end integration: Conductor server + Controller client + state machine + display."""

import asyncio
import pytest
from pathlib import Path

from conductor.conductor import Conductor
from conductor.state_machine import ChannelRegistry
from controller.controller import Controller
from shared.bus_websocket import WebSocketClient
from shared.messages import HelloMessage, ButtonMessage


@pytest.fixture
def word_blocks_path():
    return Path(__file__).parent.parent / "shared" / "data" / "word_blocks.json"


@pytest.mark.asyncio
async def test_full_two_handed_flow(word_blocks_path):
    """End-to-end: Conductor + Controller + channels + button handling."""

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

    # Verify Controller received initial state
    assert controller.current_state is not None
    assert controller.current_state.channel == "subject"

    # Send button event: next
    button_msg = ButtonMessage(btn="B", event="press")
    await controller.bus.send(button_msg.model_dump())
    await asyncio.sleep(0.2)

    # State should have updated (option_index incremented)
    assert controller.current_state.option_index > 0

    # Send button event: commit
    button_msg = ButtonMessage(btn="X", event="press")
    await controller.bus.send(button_msg.model_dump())
    await asyncio.sleep(0.2)

    # Option should be committed
    assert controller.current_state.committed is True

    # Clean up
    await controller.shutdown()
    await conductor.shutdown()
