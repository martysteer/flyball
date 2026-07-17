"""Conductor (Slate authority): state machine + server."""

import asyncio
import logging
from pathlib import Path
from typing import Optional

from conductor.state_machine import ChannelRegistry, StateSnapshot
from conductor.display import InkyMock, SlateDisplay
from conductor.buttons import KeyboardListener
from shared.bus_websocket import WebSocketServer
from shared.messages import ButtonMessage, StateMessage, PongMessage
from shared.config import IS_SIMULATION

logger = logging.getLogger(__name__)


class Conductor:
    """State authority; runs on Slate."""

    def __init__(self, word_blocks_path: Path):
        """Initialize Conductor."""
        self.registry = ChannelRegistry(word_blocks_path)
        self.bus = WebSocketServer()
        self.display = InkyMock() if IS_SIMULATION else SlateDisplay()
        self.loop = None  # Store event loop for thread-safe scheduling
        self.buttons: Optional[KeyboardListener] = None
        self.server_running = True  # Track server state for exit

        # Register message handlers
        self.bus.on("hello", self._on_hello)
        self.bus.on("button", self._on_button)
        self.bus.on("ping", self._on_ping)

    async def start(self, host: str, port: int) -> None:
        """Start WebSocket server and display."""
        self.loop = asyncio.get_running_loop()  # Capture loop for thread-safe calls
        await self.bus.start(host, port)

        # Wire keyboard input
        if IS_SIMULATION and hasattr(self.display, 'on_key'):
            # Pygame displays handle keyboard directly
            self.display.on_key = self._on_key
        else:
            # Hardware: use GPIO button listener
            self.buttons = KeyboardListener(device="slate", on_exit=self._on_exit_signal)
            self.buttons.on(self._on_slate_button)
            self.buttons.start()

        # Render initial state
        self._broadcast_state()

    async def shutdown(self) -> None:
        """Shut down server."""
        await self.bus.disconnect()
        self.display.close()

    def _on_hello(self, msg: dict) -> None:
        """Handle hello from Controller."""
        logger.info(f"Controller connected: {msg.get('device')} fw {msg.get('fw')}")
        # Send current state snapshot
        self._broadcast_state()

    def _on_button(self, msg: dict) -> None:
        """Handle button event from Controller."""
        btn = msg.get("btn")
        event = msg.get("event")
        logger.info(f"Button: {btn} {event}")
        print(f"[Spark] {btn} {event}", flush=True)

        # Interpret button
        if event == "press":
            if btn == "A":
                self.registry.button_prev()
            elif btn == "B":
                self.registry.button_next()
            elif btn == "X":
                self.registry.button_commit()
            elif btn == "Y":
                self.registry.button_shift()
            elif btn == "C":  # Slate button (switch channel)
                # For M1, just log; M2 will handle SEND
                pass

        # Broadcast updated state
        self._broadcast_state()

    def _on_ping(self, msg: dict) -> None:
        """Handle ping from Controller."""
        pong = PongMessage()
        asyncio.create_task(self.bus.send(pong.model_dump()))

    def _on_key(self, char: str) -> None:
        """Handle key press from pygame display."""
        # Map char to button name
        key_map = {'a': 'A', 'b': 'B', 'c': 'C', 'd': 'D'}
        if char == 'q':
            self._on_exit_signal()
        elif char in key_map:
            self._on_slate_button(key_map[char], "press")

    def _on_slate_button(self, btn: str, event: str) -> None:
        """Handle button press on Slate (change channel)."""
        channel_map = {"A": "subject", "B": "context", "C": "style", "D": "engine"}
        if event == "press" and btn in channel_map:
            print(f"[Slate] {btn} → channel: {channel_map[btn]}", flush=True)
            self.registry.set_active_channel(channel_map[btn])
            self._broadcast_state()

    def _schedule(self, coro) -> None:
        """Schedule a coroutine from either the event loop or a thread."""
        if not self.loop:
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

    def _broadcast_state(self) -> None:
        """Send current state to all connected Controllers."""
        snapshot = StateSnapshot.from_registry(self.registry, mode="word")
        msg = StateMessage(
            channel=snapshot.channel,
            channel_color=snapshot.channel_color,
            option_index=snapshot.option_index,
            option_count=snapshot.option_count,
            candidate=snapshot.candidate,
            committed=snapshot.committed,
            mode=snapshot.mode,
            engine=snapshot.engine,
        )
        self._schedule(self.bus.send(msg.model_dump()))

        # Also render to Slate display
        self.display.render(snapshot)
