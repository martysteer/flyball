"""Controller (Spark) entry point."""

import asyncio
import logging
import sys

from controller.controller import Controller
from shared.config import get_conductor_host, get_conductor_port, IS_SIMULATION

# In simulation, reduce logging noise (display uses stdout)
logging.basicConfig(level=logging.WARNING if IS_SIMULATION else logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Run Controller client."""
    host = get_conductor_host()
    port = get_conductor_port()

    controller = Controller()

    try:
        logger.info(f"Connecting to Conductor at {host}:{port}...")
        await controller.connect(host, port)

        # Keep running and process events
        while controller.running:
            # Re-render to process pygame events (keyboard, window close)
            if controller.current_state:
                controller.display.render(controller.current_state)
            elif hasattr(controller.display, 'mock') and controller.display.mock:
                controller.display.mock.unicorn.show()  # pump events before first state
            await asyncio.sleep(0.05)  # ~20 FPS event processing

    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await controller.shutdown()


if __name__ == "__main__":
    if IS_SIMULATION:
        logger.info("Running in SIMULATION mode")
    asyncio.run(main())
