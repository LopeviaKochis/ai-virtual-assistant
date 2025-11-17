import logging
from typing import Optional
from clients.queue_client import get_redis_client

logger = logging.getLogger(__name__)

IDEMPOTENCY_PREFIX = "processed:msg:"
IDEMPOTENCY_TTL = 86400  # 24 horas

def is_message_processed(message_id: str) -> bool:
    """
    Verifica si un mensaje ya fue procesado.
    
    Args:
        message_id: ID único del mensaje
        
    Returns:
        True si ya fue procesado
    """
    client = get_redis_client()
    key = f"{IDEMPOTENCY_PREFIX}{message_id}"
    return client.exists(key) > 0

def mark_message_processed(message_id: str) -> None:
    """
    Marca un mensaje como procesado.
    
    Args:
        message_id: ID único del mensaje
    """
    client = get_redis_client()
    key = f"{IDEMPOTENCY_PREFIX}{message_id}"
    client.setex(key, IDEMPOTENCY_TTL, "1")
    logger.debug(f"Message {message_id} marked as processed")