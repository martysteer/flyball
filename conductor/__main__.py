"""Conductor (Slate role): state authority + slow canvas.

Keys a/b/c/d = Slate channel buttons. Slate redraws only on channel change
or commit — never on a Spark cycle (docs/02 fast/slow contract).
"""
import asyncio
import logging
import os

from conductor.display import InkyMock, render_slate
from conductor.state import Flyball
from shared import messages
from shared.bus import ServerBus
from shared.buttons import KeyboardButtons
from shared.options import load_word_channels

logging.basicConfig(level=logging.INFO, format="%(asctime)s conductor %(message)s")
log = logging.getLogger("conductor")

KEYMAP = {"a": "A", "b": "B", "c": "C", "d": "D"}


async def main():
    theme = os.environ.get("FLYBALL_THEME", "cinematic_noir")
    port = int(os.environ.get("FLYBALL_PORT", "8765"))
    state = Flyball(load_word_channels(theme))
    bus = ServerBus(port=port)
    slate = InkyMock()

    async def broadcast():
        await bus.send(state.state_msg())

    def redraw_slate():
        slate.show(render_slate(state))

    async def on_hello(msg):
        log.info("hello from %s fw=%s", msg.get("device"), msg.get("fw"))
        await broadcast()

    async def on_button(msg):
        if msg.get("event") != "press":
            return  # hold semantics arrive in M4
        effect = state.spark_button(msg["btn"])
        log.info("spark %s -> %s | %r", msg["btn"], effect, state.state_msg()["candidate"])
        await broadcast()
        if effect == "commit":
            log.info("sentence: %s", state.sentence())
            redraw_slate()

    async def on_ping(msg):
        await bus.send(messages.PONG)

    bus.on("hello", on_hello)
    bus.on("button", on_button)
    bus.on("ping", on_ping)

    async def on_slate_key(btn):
        if state.slate_button(btn):
            log.info("channel -> %s", state.active)
            await broadcast()
            redraw_slate()

    kb = KeyboardButtons(KEYMAP, on_slate_key)
    print(f"Slate sim (theme={theme}). Keys: a=Subject b=Context c=Style d=Engine, q=quit")
    redraw_slate()
    await asyncio.gather(bus.run(), kb.run())


if __name__ == "__main__":
    asyncio.run(main())
