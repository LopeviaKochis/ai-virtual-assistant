import logging
import json
from typing import Dict, Any
import asyncio

from services.message_processor import process_message_for_webhook
from utils.idempotency import is_message_processed, mark_message_processed
from clients.respondio_client import respondio_client

logger = logging.getLogger(__name__)

async def handle_event(event_data: Dict[str, Any]) -> None:
    """
    Enruta eventos con rate limiting y feedback visual inmediato.
    
    Args:
        event_data: Datos completos del evento
    """

     # NUEVO: Log inicial del evento
    logger.info("="*60)
    logger.info(" NUEVO EVENTO RECIBIDO EN HANDLER")
    logger.info(f" Event data type: {type(event_data)}")
    logger.info(f" Event data keys: {list(event_data.keys()) if isinstance(event_data, dict) else 'Not a dict!'}")
    logger.info(f" Event data: {json.dumps(event_data, indent=2, default=str)}")
    logger.info("="*60)

    event_type = event_data.get("event_type")
    
    if not event_type:
        logger.warning("Event without type received")
        logger.warning(f"Available keys: {list(event_data.keys())}")
        return
    
    logger.info(f"Processing event: {event_type}")
    
    # EVENTO PRINCIPAL: message.received
    if event_type == "message.received":
        message_data = event_data.get("message", {})
        message_id = message_data.get("messageId")
        contact = event_data.get("contact", {})
        contact_id = str(contact.get("id", ""))
        channel_data = event_data.get("channel", {})
        channel_id = str(channel_data.get("id", ""))
        
        # P0-1: Marcar como leído INMEDIATAMENTE
        if message_id and channel_id:
            asyncio.create_task(
                respondio_client.mark_message_read(str(message_id), channel_id)
            )
        
        # 1. Verificar idempotencia
        if message_id and is_message_processed(str(message_id)):
            logger.info(f"Message {message_id} already processed, skipping")
            return
        
        # Verificar que sea incoming (no outgoing)
        traffic = message_data.get("traffic")
        logger.info(f"Traffic: {traffic}")

        if traffic != "incoming":
            logger.info(f"Ignoring {traffic} message")
            return
        
        # Procesar mensaje
        logger.info(f"Processing incoming message: {message_id}")
        await process_message_for_webhook(event_data)
        
        # Marcar como procesado
        if message_id:
            mark_message_processed(str(message_id))
            logger.info(f"Message {message_id} processed successfully")
    
    # EVENTO SECUNDARIO: conversation.opened
    elif event_type == "conversation.opened":
        conversation_data = event_data.get("conversation", {})
        logger.info(f"Conversation opened at {conversation_data.get('conversationOpenedAt')}")
        # Opcional: Enviar mensaje de bienvenida aquí
    
    else:
        logger.warning(f"Unknown event type: {event_type}")

def _extract_message_id(event_data: Dict[str, Any]) -> Any:
    """Extrae message ID del evento"""
    if "message" in event_data and isinstance(event_data["message"], dict):
        return event_data["message"].get("messageId")
    return None
