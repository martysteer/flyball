"""Config loader from environment / config.toml."""

import os
import platform
from pathlib import Path
from typing import Optional

IS_SIMULATION = platform.system() != "Linux"

def get_conductor_host() -> str:
    """Resolve Conductor hostname: env → localhost (sim) → slate.local (hardware)."""
    if os.getenv("FLYBALL_CONDUCTOR_HOST"):
        return os.getenv("FLYBALL_CONDUCTOR_HOST")
    return "localhost" if IS_SIMULATION else "slate.local"

def get_conductor_port() -> int:
    """WebSocket port."""
    return int(os.getenv("FLYBALL_CONDUCTOR_PORT", "8765"))

def get_config_path() -> Optional[Path]:
    """Path to config.toml if it exists."""
    config_path = Path.home() / ".flyball" / "config.toml"
    return config_path if config_path.exists() else None

def get_word_blocks_path() -> Path:
    """Path to word_blocks.json data file."""
    return Path(__file__).parent / "data" / "word_blocks.json"
