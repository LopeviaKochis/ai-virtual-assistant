import asyncio
import logging
from utils.logging import setup_logging
from clients.queue_client import dequeue_event
from handler.event_handler import handle_event

setup_logging()
logger = logging.getLogger(__name__)

async def worker_loop():
    """Loop principal del worker que procesa eventos de la cola."""
    logger.info("Worker started, waiting for events...")
    
    while True:
        try:
            # Desencolar evento (blocking con timeout)
            event_data = dequeue_event(timeout=5)
            
            if event_data:
                logger.info(f"Processing event: {event_data.get('event')}")
                await handle_event(event_data)
            
        except KeyboardInterrupt:
            logger.info("Worker stopped by user")
            break
        except Exception:
            logger.exception("Error processing event")
            await asyncio.sleep(1)  # Evitar loops intensos en caso de error

if __name__ == "__main__":
    asyncio.run(worker_loop())