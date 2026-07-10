"""Conductor (Slate role): state authority. M0: log buttons, answer hello/ping."""
import asyncio
import logging
import os

from shared import messages
from shared.bus import ServerBus

logging.basicConfig(level=logging.INFO, format="%(asctime)s conductor %(message)s")
log = logging.getLogger("conductor")


async def main():
    port = int(os.environ.get("FLYBALL_PORT", "8765"))
    bus = ServerBus(port=port)

    async def on_hello(msg):
        log.info("hello from %s fw=%s", msg.get("device"), msg.get("fw"))
        await bus.send({"type": "state", "channel": "subject",
                        "channel_color": [0, 200, 80], "option_index": 0,
                        "option_count": 1, "candidate": "M0", "committed": False,
                        "engine": {"loop": False, "speed_s": 8, "operator": "swap",
                                   "queue_depth": 0},
                        "mode": "word"})

    async def on_button(msg):
        log.info("button %s %s", msg["btn"], msg["event"])

    async def on_ping(msg):
        await bus.send(messages.PONG)

    bus.on("hello", on_hello)
    bus.on("button", on_button)
    bus.on("ping", on_ping)
    await bus.run()


if __name__ == "__main__":
    asyncio.run(main())
