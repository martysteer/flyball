"""Bus abstraction for transport (WebSocket now, MQTT later)."""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional


class Bus(ABC):
    """Abstract message bus."""

    @abstractmethod
    async def send(self, msg: Dict[str, Any]) -> None:
        """Send a message."""
        pass

    @abstractmethod
    def on(self, msg_type: str, handler: Callable[[Dict[str, Any]], None]) -> None:
        """Register handler for message type."""
        pass

    @abstractmethod
    async def connect(self) -> None:
        """Connect to the bus."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the bus."""
        pass


class BusServer(Bus):
    """Server-side bus (Conductor listens)."""

    @abstractmethod
    async def start(self, host: str, port: int) -> None:
        """Start listening."""
        pass


class BusClient(Bus):
    """Client-side bus (Controller connects)."""

    @abstractmethod
    async def connect(self, host: str, port: int) -> None:
        """Connect to a server."""
        pass
