"""Controller (Spark client): LED UI + button listener."""

import asyncio
import logging
from typing import Optional

from controller.display import SparkMock, SparkDisplay
from controller.buttons import KeyboardListener, ButtonListener
from shared.bus_websocket import WebSocketClient
from shared.messages import HelloMessage, StateMessage, PingMessage, ButtonMessage
from shared.interfaces.display import StateSnapshot
from shared.config import IS_SIMULATION

logger = logging.getLogger(__name__)


class Controller:
    """UI client; runs on Spark."""

    def __init__(self):
        """Initialize Controller."""
        self.bus = WebSocketClient()
        self.display = SparkMock() if IS_SIMULATION else SparkDisplay()
        self.buttons: Optional[ButtonListener] = None
        self.running = False
        self.current_state: Optional[StateSnapshot] = None
        self.loop = None  # Store event loop for thread-safe scheduling

        # Register bus handlers
        self.bus.on("state", self._on_state)
        self.bus.on("patch", self._on_patch)
        self.bus.on("pong", self._on_pong)
        self.bus.on("toast", self._on_toast)

    async def connect(self, host: str, port: int) -> None:
        """Connect to Conductor and start listening."""
        await self.bus.connect(host, port)
        self.running = True
        self.loop = asyncio.get_running_loop()  # Capture loop for thread-safe calls

        # Send hello
        hello = HelloMessage(device="spark", fw="0.1.0")
        await self.bus.send(hello.model_dump())

        # Start button listener
        self.buttons = KeyboardListener(device="spark")
        self.buttons.on(self._on_button_event)
        self.buttons.start()

        # Start heartbeat task
        asyncio.create_task(self._heartbeat_loop())

    async def shutdown(self) -> None:
        """Shut down client."""
        self.running = False
        if self.buttons:
            self.buttons.stop()
        await self.bus.disconnect()
        self.display.close()

    def _on_state(self, msg: dict) -> None:
        """Handle state update from Conductor."""
        state = StateSnapshot(
            channel=msg["channel"],
            channel_color=tuple(msg["channel_color"]),
            option_index=msg["option_index"],
            option_count=msg["option_count"],
            candidate=msg["candidate"],
            committed=msg["committed"],
            mode=msg["mode"],
            engine=msg.get("engine"),
        )
        self.current_state = state
        self.display.render(state)

    def _on_patch(self, msg: dict) -> None:
        """Handle incremental state update."""
        if not self.current_state:
            return

        if "candidate" in msg:
            self.current_state.candidate = msg["candidate"]
        if "option_index" in msg:
            self.current_state.option_index = msg["option_index"]
        if "committed" in msg:
            self.current_state.committed = msg["committed"]

        self.display.render(self.current_state)

    def _on_pong(self, msg: dict) -> None:
        """Handle pong from Conductor."""
        logger.debug("Pong received")

    def _on_toast(self, msg: dict) -> None:
        """Handle toast message (brief flash)."""
        logger.info(f"Toast: {msg.get('text')}")
        # Could flash LED here

    def _on_button_event(self, btn: str, event: str) -> None:
        """Handle button press from keyboard."""
        logger.info(f"Button event: {btn} {event}")

        # Send to Conductor (thread-safe)
        button_msg = ButtonMessage(btn=btn, event=event)
        if self.loop:
            asyncio.run_coroutine_threadsafe(
                self.bus.send(button_msg.model_dump()),
                self.loop
            )

    async def _heartbeat_loop(self) -> None:
        """Send periodic ping to Conductor."""
        while self.running:
            await asyncio.sleep(2)
            ping = PingMessage()
            await self.bus.send(ping.model_dump())
