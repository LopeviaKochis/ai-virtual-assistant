import redis
import json
import logging
from typing import Dict, Any, Optional
from config.settings import settings

logger = logging.getLogger(__name__)

# Cliente Redis global
_redis_client: Optional[redis.Redis] = None

def get_redis_client() -> redis.Redis:
    """Obtiene o crea el cliente Redis."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True
        )
    return _redis_client

def enqueue_event(event_data: Dict[str, Any]) -> None:
    """
    Encola un evento para procesamiento asíncrono.
    
    Args:
        event_data: Diccionario con los datos del evento
    """
    client = get_redis_client()
    serialized = json.dumps(event_data)
    client.rpush(settings.REDIS_QUEUE_NAME, serialized)
    logger.debug(f"Event enqueued: {event_data.get('event')}")

def dequeue_event(timeout: int = 5) -> Optional[Dict[str, Any]]:
    """
    Desencola un evento (blocking).
    
    Args:
        timeout: Segundos a esperar por eventos
        
    Returns:
        Diccionario con datos del evento o None si timeout
    """
    client = get_redis_client()
    result = client.blpop(settings.REDIS_QUEUE_NAME, timeout=timeout)
    
    if result:
        _, serialized = result
        return json.loads(serialized)
    return None