"""Conductor (Slate authority): state machine + server."""

import asyncio
import logging
from pathlib import Path
from typing import Optional

from conductor.state_machine import ChannelRegistry, StateSnapshot
from conductor.display import SlateDisplay, HAS_INKY
from conductor.buttons import KeyboardListener, GPIOButtonListener, HAS_GPIO
from shared.bus_websocket import WebSocketServer
from shared.messages import PongMessage
from shared.basic_image_backend import BasicImageBackend

logger = logging.getLogger(__name__)


class Conductor:
    """State authority; runs on Slate."""

    def __init__(self, word_blocks_path: Path):
        """Initialize Conductor."""
        self.registry = ChannelRegistry(word_blocks_path)
        self.bus = WebSocketServer()
        self.display = SlateDisplay()
        self.image_backend = BasicImageBackend()
        self.loop = None
        self.buttons: Optional[GPIOButtonListener] = None
        self.server_running = True
        self.render_queue: asyncio.Queue = asyncio.Queue(maxsize=1)
        self.render_task: Optional[asyncio.Task] = None

        # Register message handlers
        self.bus.on("hello", self._on_hello)
        self.bus.on("button", self._on_button)
        self.bus.on("send", self._on_send)
        self.bus.on("ping", self._on_ping)

    async def start(self, host: str, port: int) -> None:
        """Start WebSocket server and display."""
        self.loop = asyncio.get_running_loop()
        await self.bus.start(host, port)

        # Launch background render task
        self.render_task = asyncio.create_task(self._render_loop())

        # Wire input: pygame keyboard in sim, GPIO on hardware
        if not HAS_GPIO and hasattr(self.display, 'on_key') and self.display.on_key is not None or not HAS_GPIO:
            if hasattr(self.display, 'on_key'):
                self.display.on_key = self._on_key
            else:
                self.buttons = GPIOButtonListener(device="slate", on_exit=self._on_exit_signal)
                self.buttons.on(self._on_slate_button)
                self.buttons.start()
        else:
            self.buttons = GPIOButtonListener(device="slate", on_exit=self._on_exit_signal)
            self.buttons.on(self._on_slate_button)
            self.buttons.start()

        # Boot render so e-ink isn't blank
        self._render_current()

    async def shutdown(self) -> None:
        """Shut down server."""
        if self.render_task:
            self.render_task.cancel()
            try:
                await self.render_task
            except asyncio.CancelledError:
                pass
        await self.bus.disconnect()
        self.display.close()

    async def _render_loop(self) -> None:
        """Background task: consume render queue and update display.

        render_image blocks ~30s on real e-ink, so run it in an executor
        thread — a sync call inside a coroutine would freeze the whole
        event loop (handshakes, pings, messages).
        """
        while self.server_running:
            try:
                frame = await self.render_queue.get()
                logger.debug("Rendering queued frame")
                await asyncio.get_running_loop().run_in_executor(
                    None, self.display.render_image, frame
                )
                logger.debug("Render complete")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Render error: {e}")

    def _render_current(self) -> None:
        """Queue an e-ink render of current registry state (latest-only)."""
        snapshot = StateSnapshot.from_registry(self.registry, mode="word")
        frame = self.image_backend.render_frame(snapshot)
        try:
            self.render_queue.put_nowait(frame)
            logger.debug("Queued render")
        except asyncio.QueueFull:
            self.render_queue.get_nowait()
            self.render_queue.put_nowait(frame)
            logger.debug("Replaced queued render with latest")

    def _on_hello(self, msg: dict) -> None:
        """Handle hello from Controller."""
        logger.info(f"Controller connected: {msg.get('device')} fw {msg.get('fw')}")

    def _on_button(self, msg: dict) -> None:
        """Legacy button events — ignored (Spark owns exploration now)."""
        logger.debug(f"Ignoring button message: {msg}")

    def _on_send(self, msg: dict) -> None:
        """Explicit send: adopt committed words, queue one e-ink render."""
        for ch_id, word in msg.get("channels", {}).items():
            ch = self.registry.channels.get(ch_id)
            if ch is None or ch_id == "engine":
                continue
            if word and word in ch.options:
                ch.option_index = ch.options.index(word)
                ch.committed = True
            else:
                ch.committed = False  # None or unknown word → cleared
        op = msg.get("engine", {}).get("operator")
        if op:
            self.registry.channels["engine"].operator = op
        logger.info(f"Send: {self.registry.render_sentence()}")
        self._render_current()

    def _on_ping(self, msg: dict) -> None:
        """Handle ping from Controller."""
        pong = PongMessage()
        asyncio.create_task(self.bus.send(pong.model_dump()))

    def _on_key(self, char: str) -> None:
        """Handle key press from pygame display (sim only)."""
        if char == 'q':
            self._on_exit_signal()
        else:
            self._on_slate_button(char.upper(), "press")

    def _on_slate_button(self, btn: str, event: str) -> None:
        """Slate buttons unwired per spark-centric-ui spec."""
        logger.debug(f"Slate button ignored: {btn} {event}")

    def _schedule(self, coro) -> None:
        """Schedule a coroutine from either the event loop or a thread."""
        if not self.loop:
            logger.warning("Schedule called before event loop initialized")
            return
        try:
            if asyncio.get_running_loop() == self.loop:
                asyncio.create_task(coro)
            else:
                asyncio.run_coroutine_threadsafe(coro, self.loop)
        except RuntimeError:
            asyncio.run_coroutine_threadsafe(coro, self.loop)

    def _on_exit_signal(self) -> None:
        """Handle exit signal from button listener (Ctrl+C or q)."""
        self.server_running = False
        self._schedule(self.shutdown())
