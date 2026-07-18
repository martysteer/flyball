"""Controller (Spark client): LED UI + button listener."""

import asyncio
import logging
import time
from typing import Optional

from controller.display import SparkDisplay, HAS_UNICORN
from controller.buttons import GPIOButtonListener, HAS_GPIO
from controller.render import render_frame, Effects
from controller.state import LocalState
from controller.longpress import LongPressDetector
from shared.bus_websocket import WebSocketClient
from shared.messages import HelloMessage, PingMessage, SendMessage

logger = logging.getLogger(__name__)


class Controller:
    """UI client; runs on Spark."""

    def __init__(self):
        """Initialize Controller."""
        self.bus = WebSocketClient()
        self.display = SparkDisplay()
        self.buttons: Optional[GPIOButtonListener] = None
        self.running = False
        self.local = LocalState()
        self.detector = LongPressDetector()
        self.effects = Effects()
        self.loop = None
        self.heartbeat_task = None
        self.tick = 0
        self.last_candidate = ""
        self.ticker_task: Optional[asyncio.Task] = None

        # Register bus handlers
        self.bus.on("pong", self._on_pong)
        self.bus.on("toast", self._on_toast)

    async def connect(self, host: str, port: int) -> None:
        """Connect to Conductor and start listening."""
        self.bus.on_connect = self._send_hello  # re-hello on reconnect
        await self.bus.connect(host, port)
        self.running = True
        self.loop = asyncio.get_running_loop()

        await self._send_hello()

    async def _send_hello(self) -> None:
        """Send hello — Conductor logs connection."""
        hello = HelloMessage(device="spark", fw="0.1.0")
        await self.bus.send(hello.model_dump())

        # Wire input: pygame keyboard in sim, GPIO on hardware
        if not HAS_GPIO and hasattr(self.display, 'on_key'):
            self.display.on_key = self._on_key
        else:
            self.buttons = GPIOButtonListener(device="spark", on_exit=self._on_exit_signal)
            self.buttons.on(self._on_button_event)
            self.buttons.start()

        # Start heartbeat + ticker
        if not self.heartbeat_task:
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        if not self.ticker_task:
            self.ticker_task = asyncio.create_task(self._ticker_loop())

    async def shutdown(self) -> None:
        """Shut down client."""
        self.running = False
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass
        if self.ticker_task:
            self.ticker_task.cancel()
            try:
                await self.ticker_task
            except asyncio.CancelledError:
                pass
        if self.buttons:
            self.buttons.stop()
        await self.bus.disconnect()
        self.display.close()

    async def _ticker_loop(self) -> None:
        """30fps animation ticker: long-press poll + render."""
        while self.running:
            now = time.monotonic()
            # Poll long-press detector
            for btn in self.detector.poll(now):
                self._on_gesture(btn, "long")
            # Growing glint tracks longest-held button
            held = min(self.detector.down, key=self.detector.down.get, default="")
            self.effects.hold_btn = held
            self.effects.hold_frac = self.detector.hold_fraction(held, now) if held else 0.0
            snap = self.local.snapshot()
            # Reset tick when text changes (dwell at start of each new text)
            if snap.candidate != self.last_candidate:
                self.tick = 0
                self.last_candidate = snap.candidate
            self.display.push(render_frame(snap, self.tick, self.effects))
            self.tick += 1
            await asyncio.sleep(1 / 30)

    def _on_pong(self, msg: dict) -> None:
        """Handle pong from Conductor."""
        logger.debug("Pong received")

    def _on_toast(self, msg: dict) -> None:
        """Handle toast message."""
        logger.info(f"Toast: {msg.get('text')}")

    def _on_key(self, char: str, event: str = "press") -> None:
        """Handle key event from pygame display."""
        key_map = {'a': 'A', 'b': 'B', 'x': 'X', 'y': 'Y'}
        if char == 'q':
            self._on_exit_signal()
        elif char in key_map:
            self._on_button_event(key_map[char], event)

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

    def _on_button_event(self, btn: str, event: str) -> None:
        """Feed press/release into long-press detector."""
        now = time.monotonic()
        if event == "press":
            self.detector.press(btn, now)
            self.effects.glint_until = self.tick + 1
            self.effects.glint_btn = btn
        elif event == "release":
            if self.detector.release(btn, now) == "short":
                self._on_gesture(btn, "short")

    def _on_gesture(self, btn: str, kind: str) -> None:
        """Dispatch button grammar (spec §2, spatial mapping)."""
        print(f"[Spark] {btn} {kind}", flush=True)
        s = self.local
        if btn == "A":
            s.jump(-5) if kind == "long" else s.prev_option()
        elif btn == "X":
            if s.active == "engine":
                s.cycle_engine_setting()
            elif kind == "long":
                s.jump(5)
            else:
                s.next_option()
        elif btn == "B":
            if kind == "long":
                s.uncommit()
            else:
                s.commit()
                snap = s.snapshot()
                self.effects.flash_until = self.tick + 2
                self.effects.flash_color = snap.channel_color
        elif btn == "Y":
            if kind == "long":
                if s.active == "engine":
                    self._schedule(self._send())
                else:
                    s.randomize()
            else:
                s.next_channel()

    async def _send(self) -> None:
        """Explicit send → Conductor renders e-ink once."""
        msg = SendMessage(**self.local.send_payload())
        if await self.bus.send(msg.model_dump()):
            logger.info("Sent to Slate")
        else:
            self.effects.flash_until = self.tick + 3
            self.effects.flash_color = (255, 0, 0)  # red flash when disconnected

    def _on_exit_signal(self) -> None:
        """Handle exit signal."""
        self.running = False

    async def _heartbeat_loop(self) -> None:
        """Send periodic ping to Conductor."""
        while self.running:
            await asyncio.sleep(2)
            ping = PingMessage()
            await self.bus.send(ping.model_dump())
