"""Test Bus implementation with WebSocket."""

import asyncio
import json
import pytest
from shared.bus_websocket import WebSocketServer, WebSocketClient
from shared.messages import HelloMessage, StateMessage, ButtonMessage


@pytest.mark.asyncio
async def test_websocket_server_client_hello():
    """Client sends hello, server receives it."""
    server = WebSocketServer()
    client = WebSocketClient()

    received_messages = []

    def on_hello(msg):
        received_messages.append(msg)

    server.on("hello", on_hello)

    # Start server, connect client, send message
    async def run_test():
        server_task = asyncio.create_task(server.start("localhost", 18765))
        await asyncio.sleep(0.2)

        await client.connect("localhost", 18765)
        await asyncio.sleep(0.1)

        hello = HelloMessage(device="spark", fw="0.1.0")
        await client.send(hello.model_dump())
        await asyncio.sleep(0.2)

        await client.disconnect()
        await server.disconnect()

        return received_messages

    result = await run_test()
    assert len(result) > 0
    assert result[0]["device"] == "spark"


@pytest.mark.asyncio
async def test_websocket_server_sends_state():
    """Server can send state to client."""
    server = WebSocketServer()
    client = WebSocketClient()

    received_messages = []

    def on_state(msg):
        received_messages.append(msg)

    client.on("state", on_state)

    async def run_test():
        server_task = asyncio.create_task(server.start("localhost", 18766))
        await asyncio.sleep(0.2)

        await client.connect("localhost", 18766)
        await asyncio.sleep(0.1)

        state = StateMessage(
            channel="subject",
            channel_color=(0, 200, 80),
            option_index=1,
            option_count=5,
            candidate="Detective",
            committed=True,
            mode="word",
        )
        await server.send(state.model_dump())
        await asyncio.sleep(0.2)

        await client.disconnect()
        await server.disconnect()

        return received_messages

    result = await run_test()
    assert len(result) > 0
    assert result[0]["candidate"] == "Detective"
