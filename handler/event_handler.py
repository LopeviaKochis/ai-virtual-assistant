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
    # Normalizar el campo event (puede venir como 'event' o 'event_type')
    event_type = event_data.get("event") or event_data.get("event_type")
    
    if not event_type:
        logger.warning("Event without type received")
        return
    
    logger.info(f"Processing event: {event_type}")
    
    # Verificar idempotencia para message.received
    if event_type == "message.received":
        # Intentar obtener el message ID de diferentes estructuras posibles
        message_id = None
        
        # Formato 1: data.message.id (producción)
        if "data" in event_data and isinstance(event_data["data"], dict):
            message_data = event_data["data"].get("message", {})
            if isinstance(message_data, dict):
                message_id = message_data.get("id")
        
        # Formato 2: message.id (directo en root - formato de prueba)
        if not message_id and "message" in event_data:
            message_data = event_data["message"]
            if isinstance(message_data, dict):
                message_id = message_data.get("id")
        
        # Verificar si ya fue procesado
        if message_id and is_message_processed(str(message_id)):
            logger.info(f"Message {message_id} already processed, skipping")
            return
        
        # Procesar el mensaje
        await process_message_received(event_data)
        
        # Marcar como procesado
        if message_id:
            mark_message_processed(str(message_id))
    
    elif event_type == "message.sent":
        logger.debug("message.sent event received (no action needed)")
    
    elif event_type == "contact.created":
        # Intentar obtener contact_id de diferentes estructuras
        contact_id = None
        if "data" in event_data and isinstance(event_data["data"], dict):
            contact_data = event_data["data"].get("contact", {})
            if isinstance(contact_data, dict):
                contact_id = contact_data.get("id")
        if not contact_id and "contact" in event_data:
            contact_data = event_data["contact"]
            if isinstance(contact_data, dict):
                contact_id = contact_data.get("id")
        
        logger.info(f"New contact created: {contact_id}")
    
    elif event_type == "conversation.opened":
        # Intentar obtener conversation_id de diferentes estructuras
        conv_id = None
        if "data" in event_data and isinstance(event_data["data"], dict):
            conv_data = event_data["data"].get("conversation", {})
            if isinstance(conv_data, dict):
                conv_id = conv_data.get("id")
        if not conv_id and "conversation" in event_data:
            conv_data = event_data["conversation"]
            if isinstance(conv_data, dict):
                conv_id = conv_data.get("id")
        
        logger.info(f"Conversation opened: {conv_id}")
    
    elif event_type == "conversation.closed":
        # Intentar obtener conversation_id de diferentes estructuras
        conv_id = None
        if "data" in event_data and isinstance(event_data["data"], dict):
            conv_data = event_data["data"].get("conversation", {})
            if isinstance(conv_data, dict):
                conv_id = conv_data.get("id")
        if not conv_id and "conversation" in event_data:
            conv_data = event_data["conversation"]
            if isinstance(conv_data, dict):
                conv_id = conv_data.get("id")
        
        logger.info(f"Conversation closed: {conv_id}")
    
    else:
        logger.warning(f"Unknown event type: {event_type}")
    