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
        # Bind to 0.0.0.0 on hardware so Spark can connect over network
        bind_host = "localhost" if IS_SIMULATION else "0.0.0.0"
        await conductor.start(bind_host, 8765)

        # Keep running and process events
        if IS_SIMULATION:
            # Simulation: constantly re-render to process pygame keyboard events
            while conductor.server_running:
                snapshot = StateSnapshot.from_registry(conductor.registry, mode="word")
                frame = conductor.image_backend.render_frame(snapshot)
                conductor.display.render_image(frame)
                await asyncio.sleep(0.05)  # ~20 FPS
        else:
            # Hardware: just wait for GPIO button events (no constant re-render needed)
            # Display updates happen in _broadcast_state() when state changes
            while conductor.server_running:
                await asyncio.sleep(1)

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
