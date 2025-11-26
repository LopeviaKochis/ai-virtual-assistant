import asyncio
import json
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
                logger.info("="*60)
                logger.info(" WORKER: EVENTO DEENCOLADO")
                logger.info(f"Event type: {type(event_data)}")
                logger.info(f"Event keys: {list(event_data.keys()) if isinstance(event_data, dict) else 'Not a dict!'}")
                logger.info(f"Event content: {json.dumps(event_data, indent=2, default=str)}")
                logger.info(f"Event type field: {event_data.get('event_type') if isinstance(event_data, dict) else 'N/A'}")
                logger.info("="*60)
                await handle_event(event_data)
            
        except KeyboardInterrupt:
            logger.info("Worker stopped by user")
            break
        except Exception as e:
            logger.exception(f"Error processing event: {e}")
            await asyncio.sleep(1)  # Evitar loops intensos en caso de error

if __name__ == "__main__":
    asyncio.run(worker_loop())