import logging
from typing import Dict, Any

from services.message_processor import process_message_received
from utils.idempotency import is_message_processed, mark_message_processed

logger = logging.getLogger(__name__)

async def handle_event(event_data: Dict[str, Any]) -> None:
    """
    Enruta eventos según su tipo.
    
    Args:
        event_data: Datos completos del evento
    """
    event_type = event_data.get("event")
    
    if not event_type:
        logger.warning("Event without type received")
        return
    
    # Verificar idempotencia para message.received
    if event_type == "message.received":
        message_id = event_data.get("data", {}).get("message", {}).get("id")
        
        if message_id and is_message_processed(message_id):
            logger.info(f"Message {message_id} already processed, skipping")
            return
        
        await process_message_received(event_data)
        
        if message_id:
            mark_message_processed(message_id)
    
    elif event_type == "message.sent":
        logger.debug("message.sent event received (no action needed)")
    
    elif event_type == "contact.created":
        logger.info(f"New contact created: {event_data.get('data', {}).get('contact', {}).get('id')}")
    
    elif event_type == "conversation.opened":
        logger.info(f"Conversation opened: {event_data.get('data', {}).get('conversation', {}).get('id')}")
    
    elif event_type == "conversation.closed":
        logger.info(f"Conversation closed: {event_data.get('data', {}).get('conversation', {}).get('id')}")
    
    else:
        logger.warning(f"Unknown event type: {event_type}")