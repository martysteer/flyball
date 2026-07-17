"""State machine: channels, options, stack."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple


CHANNEL_COLORS = {
    "subject": (0, 200, 80),    # green
    "context": (0, 100, 200),   # blue
    "style": (200, 0, 150),     # magenta
    "engine": (200, 150, 0),    # amber
}


@dataclass
class Channel:
    """A single editable channel (Subject, Context, Style, or Engine)."""

    id: str
    options: List[str]
    option_index: int = 0
    committed: bool = False
    color: Tuple[int, int, int] = field(default_factory=lambda: (255, 255, 255))

    # Engine-specific
    loop: bool = False
    speed_s: int = 8
    operator: str = "swap"
    queue_depth: int = 0

    def next_option(self) -> None:
        """Cycle to next option."""
        if self.options:
            self.option_index = (self.option_index + 1) % len(self.options)

    def prev_option(self) -> None:
        """Cycle to previous option."""
        if self.options:
            self.option_index = (self.option_index - 1) % len(self.options)

    def commit(self) -> None:
        """Toggle committed flag."""
        self.committed = not self.committed

    def get_candidate(self) -> str:
        """Get current option text."""
        if self.options:
            return self.options[self.option_index]
        return ""

    def get_option_count(self) -> int:
        """Count of options in this channel."""
        return len(self.options)


@dataclass
class StateSnapshot:
    """Snapshot of state to send to Controller."""

    channel: str
    channel_color: Tuple[int, int, int]
    option_index: int
    option_count: int
    candidate: str
    committed: bool
    mode: str
    engine: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for JSON."""
        return {
            "type": "state",
            "channel": self.channel,
            "channel_color": self.channel_color,
            "option_index": self.option_index,
            "option_count": self.option_count,
            "candidate": self.candidate,
            "committed": self.committed,
            "mode": self.mode,
            "engine": self.engine,
        }

    @staticmethod
    def from_registry(registry: "ChannelRegistry", mode: str) -> "StateSnapshot":
        """Build snapshot from registry state."""
        active_ch = registry.active_channel
        ch = registry.channels[active_ch]

        engine_dict = None
        if active_ch == "engine":
            engine_dict = {
                "loop": ch.loop,
                "speed_s": ch.speed_s,
                "operator": ch.operator,
                "queue_depth": ch.queue_depth,
            }

        return StateSnapshot(
            channel=active_ch,
            channel_color=ch.color,
            option_index=ch.option_index,
            option_count=ch.get_option_count(),
            candidate=ch.get_candidate(),
            committed=ch.committed,
            mode=mode,
            engine=engine_dict,
        )


class ChannelRegistry:
    """Registry of all channels, loads from word_blocks.json."""

    def __init__(self, word_blocks_path: Path):
        """Load channels from word_blocks.json."""
        self.word_blocks_path = word_blocks_path
        self.channels: Dict[str, Channel] = {}
        self.active_channel = "subject"
        self._load_word_blocks()

    def _load_word_blocks(self) -> None:
        """Load channels from word_blocks.json."""
        with open(self.word_blocks_path, "r") as f:
            data = json.load(f)

        # Default theme
        theme = "cinematic_noir"
        theme_data = data["theme_specific"].get(theme, {})

        # Load word channels
        for channel_id in ["subject", "context", "style"]:
            options = theme_data.get(channel_id.title(), [])
            self.channels[channel_id] = Channel(
                id=channel_id,
                options=options,
                color=CHANNEL_COLORS.get(channel_id, (255, 255, 255)),
            )

        # Engine channel (not from word_blocks, synthetic)
        self.channels["engine"] = Channel(
            id="engine",
            options=[],  # No options; engine uses settings
            color=CHANNEL_COLORS.get("engine", (255, 255, 255)),
        )

    def set_active_channel(self, channel_id: str) -> None:
        """Change active channel."""
        if channel_id in self.channels:
            self.active_channel = channel_id

    def button_next(self) -> None:
        """Handle 'next' button on active channel."""
        self.channels[self.active_channel].next_option()

    def button_prev(self) -> None:
        """Handle 'prev' button on active channel."""
        self.channels[self.active_channel].prev_option()

    def button_commit(self) -> None:
        """Handle 'commit' button on active channel."""
        ch = self.channels[self.active_channel]
        if self.active_channel != "engine":
            ch.commit()

    def button_shift(self) -> None:
        """Handle 'shift/alt' button. For now, cycle engine operator."""
        if self.active_channel == "engine":
            operators = ["swap", "lang", "ltr", "+con", "-con"]
            current_idx = operators.index(self.channels["engine"].operator)
            self.channels["engine"].operator = operators[(current_idx + 1) % len(operators)]

    def render_sentence(self) -> str:
        """Assemble committed options into a sentence."""
        parts = []
        for ch_id in ["subject", "context", "style"]:
            ch = self.channels[ch_id]
            if ch.committed and ch.get_candidate():
                parts.append(ch.get_candidate())
        return " · ".join(parts) if parts else "[empty]"
