"""Controller (Spark role): thin client. Renders state, emits buttons.

Holds no authoritative state — only scroll/flash animation (docs/03).
"""
import asyncio
import logging
import os

from controller.display import SparkMock
from shared import messages
from shared.bus import ClientBus
from shared.buttons import KeyboardButtons

logging.basicConfig(level=logging.WARNING)  # keep the matrix clean
log = logging.getLogger("controller")

KEYMAP = {"a": "A", "b": "B", "x": "X", "y": "Y"}
FPS = 12


async def main():
    host = os.environ.get("FLYBALL_CONDUCTOR_HOST", "localhost")
    port = os.environ.get("FLYBALL_PORT", "8765")
    bus = ClientBus(f"ws://{host}:{port}")
    spark = SparkMock()

    async def on_connect():
        await bus.send(messages.hello())

    async def on_state(msg):
        spark.set_state(msg)

    async def on_pong(msg):
        pass

    bus.on_connect = on_connect
    bus.on("state", on_state)
    bus.on("pong", on_pong)

    async def on_button(btn):
        await bus.send(messages.button(btn))

    kb = KeyboardButtons(KEYMAP, on_button)

    async def render():
        while True:
            spark.tick()
            await asyncio.sleep(1 / FPS)

    try:
        await asyncio.gather(bus.run(), kb.run(), render())
    finally:
        print("\x1b[?25h\x1b[0m")  # restore cursor


if __name__ == "__main__":
    asyncio.run(main())
