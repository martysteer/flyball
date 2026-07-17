"""Conductor (Slate) entry point."""

import asyncio
import logging
import sys
from pathlib import Path

from conductor.conductor import Conductor
from shared.config import get_word_blocks_path, IS_SIMULATION

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Run Conductor server."""
    word_blocks_path = get_word_blocks_path()

    if not word_blocks_path.exists():
        logger.error(f"word_blocks.json not found at {word_blocks_path}")
        sys.exit(1)

    conductor = Conductor(word_blocks_path)

    try:
        logger.info("Starting Conductor server...")

        # Start button listener (if in sim)
        if conductor.buttons:
            conductor.buttons.start()

        await conductor.start("localhost", 8765)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        if conductor.buttons:
            conductor.buttons.stop()
        await conductor.shutdown()


if __name__ == "__main__":
    if IS_SIMULATION:
        logger.info("Running in SIMULATION mode")
    asyncio.run(main())
