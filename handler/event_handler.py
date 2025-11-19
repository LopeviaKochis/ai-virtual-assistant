import logging
from typing import Dict, Any

from services.message_processor import process_message_for_webhook
from utils.idempotency import is_message_processed, mark_message_processed

logger = logging.getLogger(__name__)

async def handle_event(event_data: Dict[str, Any]) -> None:
    """
    Enruta eventos según su tipo.
    
    Args:
        event_data: Datos completos del evento
    """
    event_type = event_data.get("event") or event_data.get("event_type")
    
    if not event_type:
        logger.warning("Event without type received")
        return
    
    logger.info(f"Processing event: {event_type}")
    
    # Verificar idempotencia para message.received
    if event_type == "message.received":
        message_id = _extract_message_id(event_data)
        
        if message_id and is_message_processed(str(message_id)):
            logger.info(f"Message {message_id} already processed, skipping")
            return
        
        # Procesar el mensaje usando el message_processor unificado
        await process_message_for_webhook(event_data)
        
        if message_id:
            mark_message_processed(str(message_id))
    
    elif event_type == "message.sent":
        logger.debug("message.sent event received (no action needed)")
    
    elif event_type == "contact.created":
        contact_id = _extract_contact_id(event_data)
        logger.info(f"New contact created: {contact_id}")
    
    elif event_type == "conversation.opened":
        conv_id = _extract_conversation_id(event_data)
        logger.info(f"Conversation opened: {conv_id}")
    
    elif event_type == "conversation.closed":
        conv_id = _extract_conversation_id(event_data)
        logger.info(f"Conversation closed: {conv_id}")
    
    else:
        logger.warning(f"Unknown event type: {event_type}")

def _extract_message_id(event_data: Dict[str, Any]) -> Any:
    """Extrae message ID de diferentes estructuras posibles."""
    if "data" in event_data and isinstance(event_data["data"], dict):
        message_data = event_data["data"].get("message", {})
        if isinstance(message_data, dict):
            return message_data.get("id")
    
    if "message" in event_data:
        message_data = event_data["message"]
        if isinstance(message_data, dict):
            return message_data.get("id")
    
    return None

def _extract_contact_id(event_data: Dict[str, Any]) -> Any:
    """Extrae contact ID de diferentes estructuras posibles."""
    if "data" in event_data and isinstance(event_data["data"], dict):
        contact_data = event_data["data"].get("contact", {})
        if isinstance(contact_data, dict):
            return contact_data.get("id")
    
    if "contact" in event_data:
        contact_data = event_data["contact"]
        if isinstance(contact_data, dict):
            return contact_data.get("id")
    
    return None

def _extract_conversation_id(event_data: Dict[str, Any]) -> Any:
    """Extrae conversation ID de diferentes estructuras posibles."""
    if "data" in event_data and isinstance(event_data["data"], dict):
        conv_data = event_data["data"].get("conversation", {})
        if isinstance(conv_data, dict):
            return conv_data.get("id")
    
    if "conversation" in event_data:
        conv_data = event_data["conversation"]
        if isinstance(conv_data, dict):
            return conv_data.get("id")
    
    return None
