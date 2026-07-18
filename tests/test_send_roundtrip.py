"""Send round-trip: SendMessage over bus updates Conductor registry."""

import asyncio
import pytest
from pathlib import Path

from conductor.conductor import Conductor
from shared.bus_websocket import WebSocketClient
from shared.messages import SendMessage
from shared.config import get_word_blocks_path


@pytest.mark.asyncio
async def test_send_updates_registry_and_queues_render():
    conductor = Conductor(get_word_blocks_path())
    client = WebSocketClient()

    await conductor.start("localhost", 18768)
    await client.connect("localhost", 18768)
    await asyncio.sleep(0.1)

    word = conductor.registry.channels["subject"].options[2]
    msg = SendMessage(
        channels={"subject": word, "context": None, "style": None},
        engine={"operator": "lang"},
    )
    await client.send(msg.model_dump())
    await asyncio.sleep(0.2)

    subject = conductor.registry.channels["subject"]
    assert subject.committed is True
    assert subject.get_candidate() == word
    assert conductor.registry.channels["context"].committed is False
    assert conductor.registry.channels["engine"].operator == "lang"

    await client.disconnect()
    conductor.server_running = False
    await conductor.shutdown()
