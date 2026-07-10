"""Load the seed option space from shared/data/word_blocks.json."""
import json
from pathlib import Path

DATA_PATH = Path(__file__).parent / "data" / "word_blocks.json"
DEFAULT_THEME = "cinematic_noir"


def load_word_channels(theme=DEFAULT_THEME, path=DATA_PATH):
    """Return {"subject": [...], "context": [...], "style": [...]} for one theme."""
    data = json.loads(Path(path).read_text())
    t = data["theme_specific"][theme]
    return {"subject": t["Subject"], "context": t["Context"], "style": t["Style"]}
