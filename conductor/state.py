"""Flyball state machine — the Conductor's single source of truth.

Pure logic, no I/O. Slate buttons pick the channel; Spark buttons act in it.
"""
from dataclasses import dataclass

from shared.messages import CHANNEL_BY_ID, CHANNEL_BY_SLATE_BTN

WORD_CHANNEL_IDS = ["subject", "context", "style"]

ENGINE_SETTINGS = ["operator", "speed", "loop", "queue"]
ENGINE_VALUES = {
    "operator": ["SWAP", "LTR", "LANG", "+CON", "-CON", "STY"],
    "speed": [4, 8, 12, 30],
    "loop": ["OFF", "ON"],
    "queue": ["SEND", "CLEAR"],
}
ENGINE_LABELS = {"operator": "OP", "speed": "SPD", "loop": "LOOP", "queue": "Q"}


@dataclass
class WordChannel:
    id: str
    options: list
    index: int = 0
    committed: str | None = None

    @property
    def candidate(self):
        return self.options[self.index]


class Flyball:
    """State authority: channels, option indices, sentence stack, engine settings."""

    def __init__(self, word_options):
        self.channels = {cid: WordChannel(cid, word_options[cid])
                         for cid in WORD_CHANNEL_IDS}
        self.active = "subject"
        self.engine_focus = 0                          # index into ENGINE_SETTINGS
        self.engine = {k: 0 for k in ENGINE_SETTINGS}  # value indices

    # --- Slate buttons (channel select) -------------------------------------

    def slate_button(self, btn):
        """btn in 'ABCD'. Returns True if the active channel changed."""
        channel_id = CHANNEL_BY_SLATE_BTN[btn]
        if channel_id == self.active:
            return False
        self.active = channel_id
        return True

    # --- Spark buttons (act within active channel) --------------------------

    def spark_button(self, btn):
        """btn in 'ABXY'. Returns 'commit' | 'cycle' | None."""
        if self.active == "engine":
            return self._engine_button(btn)
        ch = self.channels[self.active]
        n = len(ch.options)
        if btn == "A":
            ch.index = (ch.index - 1) % n
            return "cycle"
        if btn == "B":
            ch.index = (ch.index + 1) % n
            return "cycle"
        if btn == "X":
            ch.committed = ch.candidate
            return "commit"
        if btn == "Y":
            # ponytail: coarse jump only; tap/hold split needs real GPIO (M4)
            ch.index = (ch.index + 5) % n
            return "cycle"
        return None

    def _engine_button(self, btn):
        setting = ENGINE_SETTINGS[self.engine_focus]
        values = ENGINE_VALUES[setting]
        if btn == "A":
            self.engine[setting] = (self.engine[setting] - 1) % len(values)
            return "cycle"
        if btn == "B":
            self.engine[setting] = (self.engine[setting] + 1) % len(values)
            return "cycle"
        if btn == "Y":
            self.engine_focus = (self.engine_focus + 1) % len(ENGINE_SETTINGS)
            return "cycle"
        if btn == "X":
            # ponytail: apply is a no-op until M3 (queue/loop actions)
            return "cycle"
        return None

    # --- Derived views -------------------------------------------------------

    def sentence(self):
        parts = [self.channels[cid].committed for cid in WORD_CHANNEL_IDS
                 if self.channels[cid].committed]
        return " · ".join(parts)

    def engine_summary(self):
        return {
            "loop": ENGINE_VALUES["loop"][self.engine["loop"]] == "ON",
            "speed_s": ENGINE_VALUES["speed"][self.engine["speed"]],
            "operator": ENGINE_VALUES["operator"][self.engine["operator"]].lower(),
            "queue_depth": 0,  # real queue arrives in M2
        }

    def state_msg(self):
        """Full snapshot per docs/03."""
        color = list(CHANNEL_BY_ID[self.active]["color"])
        if self.active == "engine":
            setting = ENGINE_SETTINGS[self.engine_focus]
            values = ENGINE_VALUES[setting]
            value = values[self.engine[setting]]
            return {
                "type": "state", "channel": "engine", "channel_color": color,
                "option_index": self.engine[setting], "option_count": len(values),
                "candidate": f"{ENGINE_LABELS[setting]} {value}",
                "committed": False, "engine": self.engine_summary(),
                "mode": "engine",
            }
        ch = self.channels[self.active]
        return {
            "type": "state", "channel": ch.id, "channel_color": color,
            "option_index": ch.index, "option_count": len(ch.options),
            "candidate": ch.candidate,
            "committed": ch.committed == ch.candidate,
            "engine": self.engine_summary(),
            "mode": "word",
        }
