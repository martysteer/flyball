"""Conductor (Slate authority): state machine + server."""

import asyncio
import logging
from pathlib import Path
from typing import Optional

from conductor.state_machine import ChannelRegistry, StateSnapshot
from conductor.display import InkyMock, SlateDisplay, HAS_INKY
from conductor.buttons import KeyboardListener, GPIOButtonListener, HAS_GPIO
from shared.bus_websocket import WebSocketServer
from shared.messages import ButtonMessage, StateMessage, PongMessage
from shared.keymap import Keymap, normalize_action
from shared.basic_image_backend import BasicImageBackend

logger = logging.getLogger(__name__)

KEYMAPS_DIR = Path(__file__).parent.parent / "shared" / "keymaps"


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

        # Load keymaps
        self.spark_keymap = Keymap.load(KEYMAPS_DIR / "spark.json")
        self.slate_keymap = Keymap.load(KEYMAPS_DIR / "slate.json")

        # Action handlers
        self.actions = {
            "prev": lambda: self.registry.button_prev(),
            "next": lambda: self.registry.button_next(),
            "commit": lambda: self.registry.button_commit(),
            "shift": lambda: self.registry.button_shift(),
            "cycle_setting": lambda: self.registry.button_shift(),
            "channel": lambda target: self.registry.set_active_channel(target),
        }

        # Register message handlers
        self.bus.on("hello", self._on_hello)
        self.bus.on("button", self._on_button)
        self.bus.on("ping", self._on_ping)

    async def start(self, host: str, port: int) -> None:
        """Start WebSocket server and display."""
        self.loop = asyncio.get_running_loop()
        await self.bus.start(host, port)

        # Wire input: pygame keyboard in sim, GPIO on hardware
        if not HAS_GPIO and hasattr(self.display, 'on_key') and self.display.on_key is not None or not HAS_GPIO:
            # Simulation — try pygame keys first
            if hasattr(self.display, 'on_key'):
                self.display.on_key = self._on_key
            else:
                self.buttons = GPIOButtonListener(device="slate", on_exit=self._on_exit_signal)
                self.buttons.on(self._on_slate_button)
                self.buttons.start()
        else:
            # Hardware GPIO
            self.buttons = GPIOButtonListener(device="slate", on_exit=self._on_exit_signal)
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
        self._broadcast_state()

    def _dispatch(self, keymap: Keymap, btn: str, event: str, label: str) -> None:
        """Resolve button via keymap and dispatch action."""
        if event != "press":
            return
        raw = keymap.resolve(btn, self.registry.active_channel)
        if raw is None:
            return
        action, params = normalize_action(raw)
        handler = self.actions.get(action)
        if handler:
            print(f"[{label}] {btn} -> {action}{(' ' + str(params)) if params else ''}", flush=True)
            handler(**params)
            self._broadcast_state()

    def _on_button(self, msg: dict) -> None:
        """Handle button event from Controller (Spark)."""
        btn = msg.get("btn")
        event = msg.get("event")
        logger.info(f"Button: {btn} {event}")
        self._dispatch(self.spark_keymap, btn, event, "Spark")

    def _on_ping(self, msg: dict) -> None:
        """Handle ping from Controller."""
        pong = PongMessage()
        asyncio.create_task(self.bus.send(pong.model_dump()))

    def _on_key(self, char: str) -> None:
        """Handle key press from pygame display."""
        key_map = {'a': 'A', 'b': 'B', 'c': 'C', 'd': 'D'}
        if char == 'q':
            self._on_exit_signal()
        elif char in key_map:
            self._on_slate_button(key_map[char], "press")

    def _on_slate_button(self, btn: str, event: str) -> None:
        """Handle button press on Slate."""
        self._dispatch(self.slate_keymap, btn, event, "Slate")

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

        # Render to Slate display via BasicImageBackend
        frame = self.image_backend.render_frame(snapshot)
        self.display.render_image(frame)
