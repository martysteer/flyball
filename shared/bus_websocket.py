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
        await self.server.wait_closed()


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

    async def connect(self, host: str, port: int) -> None:
        """Connect to WebSocket server."""
        try:
            self.websocket = await websockets.connect(f"ws://{host}:{port}")
            self.running = True
            logger.info(f"Connected to ws://{host}:{port}")

            # Listen for messages
            asyncio.create_task(self._listen())
        except Exception as e:
            logger.error(f"Connection failed: {e}")

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
