"""Controller (Spark) entry point."""

import asyncio
import logging
import sys

from controller.controller import Controller
from shared.config import get_conductor_host, get_conductor_port, IS_SIMULATION

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Run Controller client."""
    host = get_conductor_host()
    port = get_conductor_port()

    controller = Controller()

    try:
        logger.info(f"Connecting to Conductor at {host}:{port}...")
        await controller.connect(host, port)

        # Keep running
        while controller.running:
            await asyncio.sleep(0.1)

    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await controller.shutdown()


if __name__ == "__main__":
    if IS_SIMULATION:
        logger.info("Running in SIMULATION mode")
    asyncio.run(main())
