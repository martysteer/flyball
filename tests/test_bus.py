import asyncio

from shared import messages
from shared.bus import ClientBus, ServerBus

PORT = 8901  # ephemeral test port, not 8765


def test_hello_button_ping_roundtrip():
    async def main():
        server = ServerBus(host="127.0.0.1", port=PORT)
        client = ClientBus(f"ws://127.0.0.1:{PORT}")

        got = {"hello": asyncio.Event(), "button": asyncio.Event(),
               "state": asyncio.Event(), "pong": asyncio.Event()}

        async def on_hello(msg):
            assert msg["device"] == "spark"
            got["hello"].set()
            await server.send({"type": "state", "candidate": "M0"})

        async def on_button(msg):
            assert msg["btn"] == "B" and msg["event"] == "press"
            got["button"].set()

        async def on_ping(msg):
            await server.send(messages.PONG)

        server.on("hello", on_hello)
        server.on("button", on_button)
        server.on("ping", on_ping)

        async def on_state(msg):
            assert msg["candidate"] == "M0"
            got["state"].set()
            await client.send(messages.button("B"))
            await client.send(messages.PING)

        async def on_pong(msg):
            got["pong"].set()

        client.on("state", on_state)
        client.on("pong", on_pong)

        async def on_connect():
            await client.send(messages.hello())

        client.on_connect = on_connect

        tasks = [asyncio.create_task(server.run()),
                 asyncio.create_task(client.run())]
        try:
            for ev in got.values():
                await asyncio.wait_for(ev.wait(), 5)
        finally:
            for t in tasks:
                t.cancel()

    asyncio.run(main())
