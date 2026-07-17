"""Conductor (Slate) entry point."""

import asyncio
import logging
import sys
from pathlib import Path

from conductor.conductor import Conductor
from conductor.state_machine import StateSnapshot
from shared.config import get_word_blocks_path, IS_SIMULATION

# In simulation, reduce logging noise
logging.basicConfig(level=logging.WARNING if IS_SIMULATION else logging.INFO)
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
        await conductor.start("localhost", 8765)

        # Keep running and process events
        while conductor.server_running:
            # Re-render to process pygame events (keyboard, window close)
            snapshot = StateSnapshot.from_registry(conductor.registry, mode="word")
            frame = conductor.image_backend.render_frame(snapshot)
            conductor.display.render_image(frame)
            await asyncio.sleep(0.05)  # ~20 FPS event processing

    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        if conductor.buttons:
            conductor.buttons.stop()
        await conductor.shutdown()


if __name__ == "__main__":
    if IS_SIMULATION:
        logger.info("Running in SIMULATION mode")
    asyncio.run(main())
