"""Bus seam: transport abstraction. WebSocket now, MQTT later (docs/03)."""
import asyncio
import json
import logging

import websockets

log = logging.getLogger("bus")


class Bus:
    """send(msg) / on(type, handler) / run(). Handlers are async def(msg)."""

    def __init__(self):
        self._handlers = {}
        self.on_connect = None  # optional async def()

    def on(self, msg_type, handler):
        self._handlers[msg_type] = handler

    async def _dispatch(self, raw):
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            log.warning("bad json: %r", raw)
            return
        handler = self._handlers.get(msg.get("type"))
        if handler:
            await handler(msg)
        else:
            log.debug("unhandled message: %s", msg)

    async def send(self, msg):
        raise NotImplementedError

    async def run(self):
        raise NotImplementedError


class ServerBus(Bus):
    """Conductor side. Accepts any number of controllers; send() broadcasts."""

    def __init__(self, host="0.0.0.0", port=8765):
        super().__init__()
        self.host = host
        self.port = port
        self._clients = set()

    async def _handler(self, ws):
        self._clients.add(ws)
        log.info("client connected (%d total)", len(self._clients))
        try:
            if self.on_connect:
                await self.on_connect()
            async for raw in ws:
                await self._dispatch(raw)
        except websockets.ConnectionClosed:
            pass
        finally:
            self._clients.discard(ws)
            log.info("client disconnected (%d total)", len(self._clients))

    async def send(self, msg):
        raw = json.dumps(msg)
        for ws in list(self._clients):
            try:
                await ws.send(raw)
            except websockets.ConnectionClosed:
                self._clients.discard(ws)

    async def run(self):
        async with websockets.serve(self._handler, self.host, self.port):
            log.info("listening on ws://%s:%d", self.host, self.port)
            await asyncio.Future()  # run forever


class ClientBus(Bus):
    """Controller side. Auto-reconnect with backoff; send() drops if offline."""

    def __init__(self, url="ws://localhost:8765"):
        super().__init__()
        self.url = url
        self._ws = None

    @property
    def connected(self):
        return self._ws is not None

    async def send(self, msg):
        if self._ws is None:
            return
        try:
            await self._ws.send(json.dumps(msg))
        except websockets.ConnectionClosed:
            pass

    async def run(self):
        delay = 0.5
        while True:
            try:
                async with websockets.connect(self.url) as ws:
                    self._ws = ws
                    delay = 0.5
                    log.info("connected to %s", self.url)
                    if self.on_connect:
                        await self.on_connect()
                    async for raw in ws:
                        await self._dispatch(raw)
            except (OSError, websockets.WebSocketException):
                pass
            self._ws = None
            log.info("disconnected; retrying in %.1fs", delay)
            await asyncio.sleep(delay)
            delay = min(delay * 2, 10)
