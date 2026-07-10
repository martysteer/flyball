"""Channel constants + message builders (protocol v1, see docs/03)."""

CHANNELS = [
    {"id": "subject", "label": "Subject", "color": (0, 200, 80), "slate_btn": "A"},
    {"id": "context", "label": "Context", "color": (40, 120, 255), "slate_btn": "B"},
    {"id": "style", "label": "Style", "color": (255, 0, 200), "slate_btn": "C"},
    {"id": "engine", "label": "Engine", "color": (255, 180, 0), "slate_btn": "D"},
]

CHANNEL_BY_SLATE_BTN = {c["slate_btn"]: c["id"] for c in CHANNELS}
CHANNEL_BY_ID = {c["id"]: c for c in CHANNELS}

PING = {"type": "ping"}
PONG = {"type": "pong"}


def hello(device="spark"):
    return {"type": "hello", "device": device, "fw": "0.1.0"}


def button(btn, event="press", ms=None):
    msg = {"type": "button", "btn": btn, "event": event}
    if ms is not None:
        msg["ms"] = ms
    return msg
