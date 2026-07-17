"""WebSocket transport for Bus."""

import asyncio
import json
import logging
from typing import Any, Callable, Dict, Optional, Set
import websockets
from websockets.server import WebSocketServerProtocol

from shared.interfaces.bus import BusServer, BusClient

logger = logging.getLogger(__name__)


class WebSocketServer(BusServer):
    """WebSocket server (Conductor side)."""

    def __init__(self):
        self.handlers: Dict[str, Callable] = {}
        self.clients: Set[WebSocketServerProtocol] = set()
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
        async def handle_client(websocket: WebSocketServerProtocol, path: str):
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

        self.server = await websockets.serve(
            handle_client, host, port, ping_interval=2, ping_timeout=1
        )
        logger.info(f"WebSocket server listening on ws://{host}:{port}")
        # Don't await wait_closed() — let caller control the event loop


class WebSocketClient(BusClient):
    """WebSocket client (Controller side)."""

    def __init__(self):
        self.handlers: Dict[str, Callable] = {}
        self.websocket: Optional[WebSocketServerProtocol] = None
        self.running = False

    def on(self, msg_type: str, handler: Callable[[Dict[str, Any]], None]) -> None:
        """Register handler for message type."""
        self.handlers[msg_type] = handler

    async def send(self, msg: Dict[str, Any]) -> None:
        """Send message to server."""
        if self.websocket:
            msg_json = json.dumps(msg)
            await self.websocket.send(msg_json)

    async def connect(self, host: str, port: int, max_retries: int = 60) -> None:
        """Connect to WebSocket server with retry + exponential backoff.

        Args:
            host: Server hostname
            port: Server port
            max_retries: Max connection attempts (default 60 = ~10 min with backoff)
        """
        attempt = 0
        while attempt < max_retries:
            try:
                self.websocket = await websockets.connect(f"ws://{host}:{port}")
                self.running = True
                logger.info(f"Connected to ws://{host}:{port}")
                asyncio.create_task(self._listen())
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
        """Listen for messages from server."""
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
            self.running = False
        except Exception as e:
            logger.error(f"Listen error: {e}")
