"""WebSocket transport for Bus."""

import asyncio
import json
import logging
from typing import Any, Callable, Dict, Optional, Set
import websockets

from shared.interfaces.bus import BusServer, BusClient

logger = logging.getLogger(__name__)


class WebSocketServer(BusServer):
    """WebSocket server (Conductor side)."""

    def __init__(self):
        self.handlers: Dict[str, Callable] = {}
        self.clients: Set[Any] = set()
        self.server = None

    def on(self, msg_type: str, handler: Callable[[Dict[str, Any]], None]) -> None:
        """Register handler for message type."""
        self.handlers[msg_type] = handler

    async def send(self, msg: Dict[str, Any]) -> None:
        """Broadcast message to all connected clients."""
        if not self.clients:
            return
        msg_json = json.dumps(msg)
        # Send to all clients
        await asyncio.gather(
            *[client.send(msg_json) for client in self.clients],
            return_exceptions=True,
        )

    async def connect(self) -> None:
        """No-op for server."""
        pass

    async def disconnect(self) -> None:
        """Shut down server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()

    async def start(self, host: str, port: int) -> None:
        """Start WebSocket server."""
        async def handle_client(websocket):
            self.clients.add(websocket)
            logger.info(f"Client connected: {websocket.remote_address}")
            try:
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        msg_type = data.get("type")
                        if msg_type in self.handlers:
                            self.handlers[msg_type](data)
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON decode error: {e}")
            except websockets.exceptions.ConnectionClosed:
                logger.info(f"Client disconnected: {websocket.remote_address}")
            finally:
                self.clients.discard(websocket)

        # ponytail: 10s ping tolerates Pi Zero wifi jitter; 2s/1s caused spurious drops
        self.server = await websockets.serve(
            handle_client, host, port, ping_interval=10, ping_timeout=10
        )
        logger.info(f"WebSocket server listening on ws://{host}:{port}")
        # Don't await wait_closed() — let caller control the event loop


class WebSocketClient(BusClient):
    """WebSocket client (Controller side)."""

    def __init__(self):
        self.handlers: Dict[str, Callable] = {}
        self.websocket: Optional[Any] = None
        self.running = False
        self.host: Optional[str] = None
        self.port: Optional[int] = None
        self.on_connect: Optional[Callable] = None  # async callback after (re)connect

    def on(self, msg_type: str, handler: Callable[[Dict[str, Any]], None]) -> None:
        """Register handler for message type."""
        self.handlers[msg_type] = handler

    async def send(self, msg: Dict[str, Any]) -> None:
        """Send message to server. Drops message if disconnected."""
        if not self.websocket:
            return
        try:
            await self.websocket.send(json.dumps(msg))
        except websockets.exceptions.ConnectionClosed:
            logger.warning(f"Send dropped (disconnected): {msg.get('type')}")

    async def connect(self, host: str, port: int, max_retries: int = 60) -> None:
        """Connect to WebSocket server with retry + exponential backoff."""
        self.host = host
        self.port = port
        self.running = True
        await self._connect_once(max_retries)
        asyncio.create_task(self._listen())

    async def _connect_once(self, max_retries: int = 60) -> None:
        """Single connect attempt with retry + exponential backoff."""
        attempt = 0
        while attempt < max_retries:
            try:
                self.websocket = await websockets.connect(f"ws://{self.host}:{self.port}")
                logger.info(f"Connected to ws://{self.host}:{self.port}")
                return
            except Exception as e:
                attempt += 1
                if attempt >= max_retries:
                    logger.error(f"Failed to connect after {max_retries} attempts: {e}")
                    raise
                # Exponential backoff: 1s, 2s, 4s, 8s, 16s, 30s (capped)
                wait = min(2 ** (attempt - 1), 30)
                logger.warning(f"Connection attempt {attempt} failed: {e}. Retrying in {wait}s...")
                await asyncio.sleep(wait)

    async def disconnect(self) -> None:
        """Disconnect from server."""
        self.running = False
        if self.websocket:
            await self.websocket.close()

    async def _listen(self) -> None:
        """Listen for messages; auto-reconnect on connection loss."""
        while self.running:
            try:
                async for message in self.websocket:
                    try:
                        data = json.loads(message)
                        msg_type = data.get("type")
                        if msg_type in self.handlers:
                            self.handlers[msg_type](data)
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON decode error: {e}")
            except websockets.exceptions.ConnectionClosed:
                logger.info("Server disconnected")
            except Exception as e:
                logger.error(f"Listen error: {e}")

            if not self.running:
                break

            logger.info("Reconnecting...")
            try:
                await self._connect_once()
            except Exception:
                logger.error("Reconnect failed permanently, giving up")
                self.running = False
                break
            if self.on_connect:
                await self.on_connect()
