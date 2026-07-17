"""Message schema for bus transport."""

from pydantic import BaseModel, Field
from typing import Optional, Tuple, Dict, Any


class BaseMessage(BaseModel):
    """Base message with type field."""
    type: str


class HelloMessage(BaseMessage):
    """Controller introduction."""
    type: str = Field(default="hello", frozen=True)
    device: str  # "spark" or "slate"
    fw: str  # firmware version


class StateMessage(BaseMessage):
    """Full state snapshot from Conductor to Controller."""
    type: str = Field(default="state", frozen=True)
    channel: str
    channel_color: Tuple[int, int, int]
    option_index: int
    option_count: int
    candidate: str
    committed: bool
    mode: str  # "word" | "engine"
    engine: Optional[Dict[str, Any]] = None


class ButtonMessage(BaseMessage):
    """Button event from Controller to Conductor."""
    type: str = Field(default="button", frozen=True)
    btn: str  # "A", "B", "X", "Y" (Spark) or "A", "B", "C", "D" (Slate)
    event: str  # "press", "release", "hold"
    ms: Optional[int] = None  # hold duration


class PingMessage(BaseMessage):
    """Heartbeat from either side."""
    type: str = Field(default="ping", frozen=True)


class PongMessage(BaseMessage):
    """Heartbeat response."""
    type: str = Field(default="pong", frozen=True)


class ToastMessage(BaseMessage):
    """Brief toast message for Spark (e.g. flash on commit)."""
    type: str = Field(default="toast", frozen=True)
    text: str
    color: Tuple[int, int, int]


class PatchMessage(BaseMessage):
    """Incremental state update (optimization; optional for M0)."""
    type: str = Field(default="patch", frozen=True)
    candidate: Optional[str] = None
    option_index: Optional[int] = None
    committed: Optional[bool] = None


# Helper: create message from dict
def message_from_dict(data: Dict[str, Any]) -> BaseMessage:
    """Deserialize message dict to appropriate type."""
    msg_type = data.get("type")
    if msg_type == "hello":
        return HelloMessage(**data)
    elif msg_type == "state":
        return StateMessage(**data)
    elif msg_type == "button":
        return ButtonMessage(**data)
    elif msg_type == "ping":
        return PingMessage(**data)
    elif msg_type == "pong":
        return PongMessage(**data)
    elif msg_type == "toast":
        return ToastMessage(**data)
    elif msg_type == "patch":
        return PatchMessage(**data)
    else:
        raise ValueError(f"Unknown message type: {msg_type}")
