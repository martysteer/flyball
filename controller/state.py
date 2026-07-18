"""Spark-local exploration state (spec: local-state inversion).

Spark owns channel/index/committed-word during exploration; Conductor
stays authority for sentence-of-record via the explicit `send` message.
"""

import json
import random

from shared.config import get_word_blocks_path
from shared.interfaces.display import StateSnapshot, CHANNEL_COLORS

CHANNEL_ORDER = ["subject", "context", "style", "engine"]
WORD_CHANNELS = ["subject", "context", "style"]
ENGINE_SETTINGS = ["send", "op"]
OPERATORS = ["swap", "lang", "ltr", "+con", "-con"]


class LocalState:
    """Owns exploration state; every mutation is instant and local."""

    def __init__(self, word_blocks_path=None):
        path = word_blocks_path or get_word_blocks_path()
        with open(path) as f:
            data = json.load(f)
        theme = data["theme_specific"]["cinematic_noir"]
        self.options = {c: theme[c.title()] for c in WORD_CHANNELS}
        self.index = {c: 0 for c in WORD_CHANNELS}
        self.committed_word = {c: None for c in WORD_CHANNELS}
        self.committed_index = {c: None for c in WORD_CHANNELS}
        self.active = "subject"
        self.engine_setting = 0   # index into ENGINE_SETTINGS
        self.operator = 0         # index into OPERATORS

    # --- exploration ---

    def next_option(self) -> None:
        self._shift(1)

    def prev_option(self) -> None:
        self._shift(-1)

    def jump(self, delta: int) -> None:
        self._shift(delta)

    def _shift(self, delta: int) -> None:
        if self.active == "engine":
            if ENGINE_SETTINGS[self.engine_setting] == "op":
                self.operator = (self.operator + delta) % len(OPERATORS)
            return
        opts = self.options[self.active]
        self.index[self.active] = (self.index[self.active] + delta) % len(opts)

    def randomize(self) -> None:
        if self.active in WORD_CHANNELS:
            self.index[self.active] = random.randrange(len(self.options[self.active]))

    # --- commitment ---

    def commit(self) -> None:
        if self.active in WORD_CHANNELS:
            self.committed_word[self.active] = self._candidate()
            self.committed_index[self.active] = self.index[self.active]

    def uncommit(self) -> None:
        if self.active in WORD_CHANNELS:
            self.committed_word[self.active] = None
            self.committed_index[self.active] = None

    def next_channel(self) -> None:
        i = CHANNEL_ORDER.index(self.active)
        self.active = CHANNEL_ORDER[(i + 1) % len(CHANNEL_ORDER)]

    def cycle_engine_setting(self) -> None:
        self.engine_setting = (self.engine_setting + 1) % len(ENGINE_SETTINGS)

    # --- views ---

    def _candidate(self) -> str:
        if self.active == "engine":
            setting = ENGINE_SETTINGS[self.engine_setting]
            return "SEND" if setting == "send" else f"OP {OPERATORS[self.operator]}"
        return self.options[self.active][self.index[self.active]]

    def snapshot(self) -> StateSnapshot:
        if self.active == "engine":
            return StateSnapshot(
                channel="engine",
                channel_color=CHANNEL_COLORS["engine"],
                option_index=self.engine_setting,
                option_count=len(ENGINE_SETTINGS),
                candidate=self._candidate(),
                committed=False,
                mode="engine",
                engine={"operator": OPERATORS[self.operator]},
                committed_index=None,
            )
        word = self._candidate()
        return StateSnapshot(
            channel=self.active,
            channel_color=CHANNEL_COLORS[self.active],
            option_index=self.index[self.active],
            option_count=len(self.options[self.active]),
            candidate=word,
            committed=self.committed_word[self.active] == word,
            mode="word",
            committed_index=self.committed_index[self.active],
        )

    def send_payload(self) -> dict:
        return {
            "channels": dict(self.committed_word),
            "engine": {"operator": OPERATORS[self.operator]},
        }
