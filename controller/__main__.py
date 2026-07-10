"""Controller (Spark role): thin client. M0: keys a/b/x/y -> button msgs, log state."""
import asyncio
import logging
import os

from shared import messages
from shared.bus import ClientBus
from shared.buttons import KeyboardButtons

logging.basicConfig(level=logging.INFO, format="%(asctime)s controller %(message)s")
log = logging.getLogger("controller")

KEYMAP = {"a": "A", "b": "B", "x": "X", "y": "Y"}


async def main():
    host = os.environ.get("FLYBALL_CONDUCTOR_HOST", "localhost")
    port = os.environ.get("FLYBALL_PORT", "8765")
    bus = ClientBus(f"ws://{host}:{port}")

    async def on_connect():
        await bus.send(messages.hello())
        await bus.send(messages.PING)

    async def on_state(msg):
        log.info("state: channel=%s candidate=%r", msg.get("channel"), msg.get("candidate"))

    async def on_pong(msg):
        log.info("pong")

    bus.on_connect = on_connect
    bus.on("state", on_state)
    bus.on("pong", on_pong)

    async def on_button(btn):
        log.info("-> button %s", btn)
        await bus.send(messages.button(btn))

    kb = KeyboardButtons(KEYMAP, on_button)
    print("Spark sim. Keys: a=prev b=next x=commit y=shift, q=quit")
    await asyncio.gather(bus.run(), kb.run())


if __name__ == "__main__":
    asyncio.run(main())
